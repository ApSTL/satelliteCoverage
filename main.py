"""
Main run file to get image acquisition-delivery probabilities over specific locations,
given cloud coverage data and satellite position data
"""

import os
import csv
from datetime import datetime, timedelta
from math import acos, sin, pi, radians, degrees
from typing import List, Dict

import skyfield.api
from skyfield.api import wgs84, load, Time, utc
from skyfield.toposlib import GeographicPosition

from space_track_api_script import space_track_api_request
from cloud import get_cloud_fraction_at_time, extract_cloud_data


class Spacecraft:
	def __init__(
			self,
			satellite: skyfield.api.EarthSatellite,
			field_of_regard: float = radians(30),
			aq_prob: float = 1.0,
			download_rate: float = 100.
	):
		self.satellite = satellite
		self.for_ = field_of_regard
		self.aq_prob = aq_prob
		self.download_rate = download_rate

	def __repr__(self):
		# FIXME this isn't correct...
		return self.satellite.satellite.__str__()


class Location:
	def __init__(
			self,
			name: str,
			location: GeographicPosition
	):
		self.name = name
		self.location = location


class Contact:
	"""Space-to-Ground contact base class"""
	def __init__(
			self,
			satellite: Spacecraft,
			target: Location,
			t_rise: Time,
			t_peak: Time,
			t_set: Time
	):
		self.satellite = satellite
		self.target = target
		self.t_rise = t_rise
		self.t_peak = t_peak
		self.t_set = t_set

	@property
	def duration(self):
		return 24 * 60 * 60 * (self.t_set - self.t_rise)

	def __lt__(self, other):
		if self.t_peak.J <= other.t_peak.J:
			return True
		return False


# Probability of downloading an image during the subsequent X ground station passes.
# E.g. If only one pass is considered, then there's a 100% probability then that pass
# is used. If two passes, then 75% chance the first is used, and 25% the second is used.
DOWNLOAD_PROBABILITY = {
	1: [1.0],
	2: [0.75, 0.25],
	3: [0.6, 0.3, 0.1],
	4: [0.5, 0.25, 0.1, 0.05]
}

# The number of downloads considered reasonable before data acquired earlier is
# guaranteed to have been downloaded.
MAX_DOWNLOADS_CONSIDERED: int = 2

T_MIN = 1 / 24  # Time (days) since download before which 0% chance of data arrival
T_MAX = 6 / 24  # Time (days) since download after which 100% chance of data arrival

PLATFORM_ATTRIBS = {
	"for": {  # Field of regard (half-angle)
		"FLOCK": radians(1.44763),  # 24km swath @ 476km alt
		# TODO Update to be realistic
		"SKYSAT": radians(30.)
	},
	"aq_prob": {  # probability that imaging opportunity results in capture
		# TODO Update to be realistic
		"FLOCK": 1.0,
		"SKYSAT": 0.1
	}
	}

# Define the Ground Stations to which images are downloaded
GROUND_STATIONS = [
	Location("Yukon", wgs84.latlon(69.588837, -139.048477)),  # Estimated position
	Location("North Dakota", wgs84.latlon(48.412949, -97.487445)),  # Estimated position
	Location("Iceland", wgs84.latlon(64.872589, -22.379039)),  # Estimated position
	Location("Awarura", wgs84.latlon(-46.528890, 168.381881)),
]


def for_elevation_from_half_angle(
		half_angle,
		altitude
) -> float:
	# TODO Write tests for this
	"""
	Return the elevation above the horizon at the edge of the Field of Regard
	:param half_angle: FoR half-angle (i.e. the angle, from Nadir, to edge of view) (rad)
	:param altitude: Satellite altitude (m)
	:return:
	"""
	R_E = 6371000.8  # Mean Earth radius

	# Check that we don't have the entire Earth in view, if so, return 90 deg
	lamda_0 = acos(R_E / (R_E + altitude))
	rho = (pi / 2) - lamda_0
	if half_angle >= rho:
		return 0.0

	return acos(sin(half_angle) / sin(rho))


def get_contact_events(
		sats: List,
		location: Location,
		t0: datetime,
		t1: datetime,
		is_target: bool = True
) -> List:
	"""
	Return all contact events between a set of satellites and ground locations
	:param sats: List of Spacecraft objects
	:param locations: List of Location objects representing Imaging targets
	:param stations: List of Location objects representing Ground Stations
	:param t0_ts: Time horizon start
	:param t1: Time horizon end
	:param is_target: Boolean indicating whether or not the ground node is an image target
	:return:
	"""
	R_E = 6371000.8  # Mean Earth radius
	contacts = []
	# For each satellite<>location pair, get all contact events during the horizon
	for s in sats:
		# Set the elevation angle above the horizon that defines "contact",
		# depending on whether the location is a Target or Ground Station
		if is_target:
			# FIXME using the perigee altitude here to get angle above the horizon
			#  that results in a "contact", however this would not work if we're in
			#  an elliptical orbit, since the elevation angle would change over time
			elev_angle = degrees(for_elevation_from_half_angle(
				s.for_, s.satellite.model.altp * R_E))
		else:
			elev_angle = 10

		# Get the rise, culmination and fall for all passes between this
		# satellite:target pair during the time horizon
		t0_ts = load.timescale().from_datetime(t0.astimezone(utc))
		t1_ts = load.timescale().from_datetime(t1.astimezone(utc))
		t, events = s.satellite.find_events(
			location.location, t0_ts, t1_ts, altitude_degrees=elev_angle)

		# Pre-set the
		t_rise = t0_ts
		t_peak = t0_ts
		for ti, event in zip(t, events):
			# If the event is 0 (i.e. "rise"), store the rise event, else if it's
			# 0 (i.e. "culmination"), continue
			if event == 0:  # If this is a Rise event, set the rise time
				t_rise = ti
				continue
			if event == 1:  # if this is a Peak event, skip
				t_peak = ti
				continue
			# So long as a rise time has been defined, instantiate the Download event
			contacts.append(Contact(s, location, t_rise, t_peak, ti))
	return contacts


def probability_event_linear_scale(
		x,
		x_min,
		x_max
) -> float:
	"""
	Probability that an event has happened at some time between some min & max,
	given a linear probability distribution between those limits
	:return:
	"""
	return (x - x_min) / (x_max - x_min)


def prob_arrival_via_download(
		t: datetime,
		download: Contact
) -> float:
	"""
	Probability that data, if it had been downloaded during this "download" event,
	would have been delivered to the customer by time "t".
	:return:
	"""
	t = load.timescale().from_datetime(t.astimezone(utc))
	if t.tt <= (download.t_set + T_MIN).tt:
		return 0.
	elif t.tt >= (download.t_set + T_MAX).tt:
		return 1.
	# Replace this function with a different probability function if required.
	return probability_event_linear_scale(
		t,
		download.t_set + T_MIN,
		download.t_set + T_MAX
	)


def prob_of_data_by_time(
		image: Contact,
		t_arrival: datetime,
		downloads: List[Contact],
		cloud: float,
) -> float:
	"""
	Return probability that cloud-free data from an image event has arrived
	:param image: Image object
	:param t_arrival:
	:param downloads: List of Download objects
	:param cloud: fraction of cloud cover at time of image
	:return:
	"""
	# The probability that the image even exist in the first place is the
	# combined probability that it was both taken AND it was cloud-free. E.g. if there
	# was an 80% chance of acquisition, and a 30% chance of it being cloud-free,
	# then the chance of image existing is 0.8 * 0.3 = 0.24.
	# This is the MAX probability that the data product arrives at the customer
	prob_image_exists = (1. - cloud) * image.satellite.aq_prob

	downloads_ = [
		d for d in downloads
		if d.t_set.tt > image.t_peak.tt and d.satellite == image.satellite
	]

	# Extracting only every 8th download opportunity, to simulate something closer to
	# the real download contact schedule seen by Planet's FLOCK
	# TODO Remove the hard-coding
	downloads_ = downloads_[::8]

	# Initiate a variable that tracks the probability that data that WAS delivered would
	# have arrived by this time. This does NOT consider the probability of it actually
	# existing in the first place. E.g. if we're passed the max processing time for two
	# download events, and we're only considering two download events feasible,
	# then this would be 100%
	total_prob_arr_via_download = 0
	for k in range(MAX_DOWNLOADS_CONSIDERED):
		prob_arrival_via_d = prob_arrival_via_download(t_arrival, downloads_[k])
		total_prob_arr_via_download += DOWNLOAD_PROBABILITY[MAX_DOWNLOADS_CONSIDERED][k] * prob_arrival_via_d

	# Combine the probability of the image existing and the probability of it having
	# arrived IF it were downloaded, to get the overall probability of
	return prob_image_exists * total_prob_arr_via_download


def fetch_satellite_tle_data(
		filename_tle,
		filename_norad,
		epoch_time_str,
		end_time_str
) -> None:
	with open(filename_norad, "r") as file_norads:
		norad_ids = file_norads.read()

	# Get all TLE data for each satellite in the list between the start and end dates
	tle_response = space_track_api_request(epoch_time_str, end_time_str, norad_ids)

	# Write the retrieved TLE data to a text file
	with open(filename_tle, "w", newline="") as text_file:
		text_file.write(tle_response.text)


def get_satellites_closest_to_epoch(
		file_with_tle_data,
		epoch
) -> Dict:
	satellites_best_epoch = {}
	for s in load.tle_file(file_with_tle_data):
		# If our TLE epoch is greater than the time from which we're considering
		# images to be "valuable", skip since we need something earlier
		if s.epoch.tt > epoch.tt:
			continue
		# If we've not yet stored a TLE for this satellite, do so
		if s.model.satnum not in satellites_best_epoch:
			satellites_best_epoch[s.model.satnum] = s
			continue
		# If this TLE is later than the one we currently have, overwrite it
		if s.epoch.tt > satellites_best_epoch[s.model.satnum].epoch.tt:
			satellites_best_epoch[s.model.satnum] = s
	return satellites_best_epoch


def get_spacecraft_from_epoch(
		platform,
		pre_epoch_time,
		epoch,
		end_time
) -> List[Spacecraft]:
	# Format the different times as required
	pre_epoch_time_str = str(pre_epoch_time)[0:10]
	end_time_str = str(end_time)[0:10]

	file_tle = f"tle_data//{platform}_tle_{pre_epoch_time_str}_{end_time_str}.txt"
	if not os.path.isfile(file_tle):  # Skip if we already have this data
		file_norad = f"norad_ids//{platform}_ids.txt"
		fetch_satellite_tle_data(file_tle, file_norad, pre_epoch_time_str, end_time_str)

	# For each satellite platform, extract the EarthSatellite object with an epoch
	# closest to (but no later than) the earliest time at which data is considered to be
	# of value
	satellites_best_epoch = get_satellites_closest_to_epoch(
		file_tle,
		load.timescale().from_datetime(epoch.astimezone(utc))
	)

	# Create Spacecraft objects for each item in the TLE dataset
	spacecraft_all = []
	for satellite_id, satellite in satellites_best_epoch.items():
		spacecraft_all.append(Spacecraft(
			satellite,
			[  # Field of regard (half angle, radians)
				PLATFORM_ATTRIBS["for"][x] for x in PLATFORM_ATTRIBS["for"]
				if x in satellite.name
			][0],
			[  # Probability a location within the FoR will be acquired
				PLATFORM_ATTRIBS["aq_prob"][x] for x in PLATFORM_ATTRIBS["aq_prob"]
				if x in satellite.name
			][0]
		))
	return spacecraft_all


def get_probability_of_no_image(
		city,
		images,
		downloads,
		cloud_threshold,
		day0,
		pre_epoch
) -> float:
	"""Get the probability that NO image will have been received of a particular location"""
	# Get cloud data for the city of interest during our time horizon
	cloud_data = extract_cloud_data(f"weather//{city}.csv", pre_epoch, day0)
	cumulative_probability_of_no_image = 1.
	for image in images:
		cloud_fraction = get_cloud_fraction_at_time(image.t_peak.tt, cloud_data)
		# If the image is not captured during sunlight, skip
		if 18 < image.t_peak.gast < 6:
			continue
		# If the image is deemed "too cloudy", skip
		if cloud_fraction > cloud_threshold:
			continue
		# Get the probability that the user will have data from this image by day0
		prob = prob_of_data_by_time(
			image,
			day0,
			downloads,
			cloud_fraction
		)
		# Update probability that we'd have received NO image by this time
		cumulative_probability_of_no_image *= 1 - prob
	return cumulative_probability_of_no_image


def find_city_location(
		city_name
) -> wgs84.latlon:
	"""
	Return a location object (lat lon) for a named city (city must be in the CSV).

	:param city_name: String of city for which the Lat Lon is required
	:return:
	"""
	filepath = "lat_lon_data/uscities_lat_lng.csv"
	with open(filepath, newline='') as csvfile:
		city_location = csv.reader(csvfile, quotechar='|')
		for row in city_location:
			if row[0] == city_name:
				return wgs84.latlon(float(row[2]), float(row[3]))
	raise ValueError(f"City {city_name} not found in the file")


def main(
		cities: List[str],
		day0: datetime = datetime(2022, 6, 10, 20, 0, 0),
		pre_day0_period: float = 1.0,
		platform: str = "flock",  # "skysat"
		cloud_threshold: float = 1.0  # maximum acceptable fraction of cloud cover
) -> Dict[str, float]:

	# Define the date and time from which we want to extract TLE data. This should be
	# early enough such that we can be sure not to miss the epoch (i.e. earliest time
	# of interest), considering that there can be gaps in TLE data of a couple of days.
	epoch = day0 - timedelta(pre_day0_period)  # pre-epoch time as a datatime object
	pre_epoch = day0 - timedelta(pre_day0_period + 3)  # epoch as a datetime object

	# Instantiate Spacecraft objects, one for each NORAD ID, with its epoch as close
	# to, but later than, the epoch time specified.
	satellites = get_spacecraft_from_epoch(platform, pre_epoch, epoch, day0)

	downloads = []
	for gs in GROUND_STATIONS:
		downloads.extend(
			get_contact_events(satellites, gs, epoch, day0, False)
		)
	downloads = sorted(downloads)

	probabilities = {}
	for city in cities:
		# Given a particular City, and a particular "Day 0", get the probability that a
		# decision maker will have received useful (processed) data, with which a trading
		# decision can be made. There should be a probability associated with images
		# acquired during preceding days, rather than simply Day 0 imagery.
		city_location = Location(city, find_city_location(city))
		# Get all the potential contact opportunities. These might not necessarily be
		# realised, because of things like cloud cover and/or time of day, but these are
		# events in which the satellite is above the minimum elevation for the target
		images = sorted(
			get_contact_events(satellites, city_location, epoch, day0)
		)

		# Given the set of images of this city, and the set of Download opportunities,
		# find the probability that NO image is received by Day 0
		no_image = get_probability_of_no_image(
			city,
			images,
			downloads,
			cloud_threshold,
			day0,
			pre_epoch
		)

		# Get the TOTAL probability of having data insights of this target, but this time
		probabilities[city] = 1 - no_image
	return probabilities


if __name__ == "__main__":
	# NOTE: This must match the name of the city in the lat-lon CSV
	cities = ["Denver", "New York", "Los Angeles"]
	day0 = datetime(2022, 11, 7, 5, 0, 0)
	pre_day0 = 1
	probabilities_all_cities = main(cities, day0, pre_day0)
	print(f"Probability of receiving data less than {pre_day0} days old:")
	for city, prob in probabilities_all_cities.items():
		print(f"-> {city}: {prob}")
