"""
Main run file to get image acquisition-delivery probabilities over specific locations,
given cloud coverage data and satellite position data
"""

from math import acos, sin, pi, radians, degrees
from typing import List, Dict

import skyfield.api
from skyfield.api import wgs84, load, Time
from skyfield.toposlib import GeographicPosition


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


class Location:
	def __init__(
			self,
			name: str,
			location: GeographicPosition
	):
		self.name = name
		self.location = location


class Image:
	"""Image base class"""
	def __init__(
			self,
			satellite: Spacecraft,
			target: Location,
			time_capture: Time,
			cloud: float = 0.
	):
		self.target = target
		self.time = time_capture
		self.satellite = satellite
		self.cloud = cloud
		self.download_opportunities = []

	def __lt__(self, other):
		if self.time.J <= other.time.J:
			return True
		return False


class Download:
	"""Download event base class"""
	def __init__(
			self,
			satellite: Spacecraft,
			ground_station: Location,
			start: Time,
			end: Time
	):
		self.ground_station = ground_station
		self.start = start
		self.end = end
		self.satellite = satellite

	@property
	def duration(self):
		return 24 * 60 * 60 * (self.end - self.start)

	@property
	def capacity(self):
		return self.duration * self.satellite.download_rate

	def __lt__(self, other):
		if self.start.J < other.start.J:
			return True
		if self.start.J == other.start.J and self.end.J < other.end.J:
			return True
		return False


def for_elevation_from_half_angle(half_angle, altitude):
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


def get_all_events(sats: List, targs: List, stations: List, t0: Time, t1: Time):
	"""
	Return all contact events between a set of satellites and ground locations
	:param sats: List of Spacecraft objects
	:param targs: List of Location objects representing Imaging targets
	:param stations: List of Location objects representing Ground Stations
	:param t0: Time horizon start
	:param t1: Time horizon end
	:return:
	"""
	R_E = 6371000.8  # Mean Earth radius

	image_events = []
	download_events = []

	# For each satellite<>location pair, get all contact events during the horizon
	for s in sats:
		for location in targs + stations:

			# Set the elevation angle above the horizon that defines "contact",
			# depending on whether the location is a Target or Ground Station
			if location in targs:
				# FIXME using the perigee altitude here to get angle above the horizon
				#  that results in a "contact", however this would not work if we're in
				#  an elliptical orbit, since the elevation angle would change over time
				elev_angle = degrees(for_elevation_from_half_angle(
					s.for_, s.satellite.model.altp * R_E))
			else:
				elev_angle = 10

			# Get the rise, culmination and fall for all passes between this
			# satellite:target pair during the time horizon
			t, events = s.satellite.find_events(
				location.location, t0, t1, altitude_degrees=elev_angle)

			# Pre-set the
			t_rise = t0
			t_peak = None
			for ti, event in zip(t, events):
				if location.name in [t.name for t in targs]:
					if event == 0:  # If this is a Rise event, skip
						continue
					elif event == 1:  # If this is a Peak event, set the peak time
						t_peak = ti
					else:  # if this is a Fall event
						# If we haven't yet seen a peak, we must have started in a
						# contact, but after the peak. In this case, set the peak time
						# to be the start of our horizon, to get as close as possible
						if t_peak is None:
							t_peak = t0
						else:
							continue
					# otherwise, we must be at a Peak event, so add to the events list
					image_events.append(Image(s, location, t_peak))

				elif location.name in [gs.name for gs in stations]:
					# If the event is 0 (i.e. "rise"), store the rise event, else if it's
					# 0 (i.e. "culmination"), continue
					if event == 0:  # If this is a Rise event, set the rise time
						t_rise = ti
						continue
					if event == 1:  # if this is a Peak event, skip
						continue
					# So long as a rise time has been defined, instantiate the Download event
					download_events.append(Download(s, location, t_rise, ti))

				else:
					raise ValueError("Location not in either targets or ground stations")

	return image_events, download_events


def get_n_following_downloads(image: Image, downloads: List, n: int = 1):
	"""
	Given a particular image event, find the n downloads that are available.
	:param image:
	:param downloads:
	:param n:
	:return:
	"""
	downloads_ = []  # List of download events available after image acquisition
	for download in downloads:
		if len(downloads_) == n:
			break
		if download.end.tt > image.time.tt and download.satellite == image.satellite:
			downloads_.append(download)
	return downloads_


if __name__ == "__main__":
	# Fetch the latest TLEs for all of Planet's satellites
	planet_url = "http://celestrak.com/NORAD/elements/planet.txt"

	# Instantiate an "skyfield.EarthSatellite" object for each of the TLE entries. This
	# is a satellite object that has built-in functionality for such things as rise and
	# set times over a particular location on the ground. It's "epoch" is based on the
	# TLE used to generate it
	satellites = load.tle_file(planet_url)

	# Define the platform attributes that get assigned based on the TLE data. Note that
	# the "keys" within each of the attributes correspond to the "name" attribute on
	# the Satrec object in the Skyfield EarthSatellite.satellite object. As in if
	# "FLOCK" is in the name attribute, it will be used.
	platform_attribs = {
		"for": {  # Field of regard (half-angle)
			# TODO Update to be realistic
			"FLOCK": radians(30.),
			"SKYSAT": radians(40.)
		},
		"aq_prob": {  # probability that imaging opportunity results in capture
			# TODO Update to be realistic
			"FLOCK": 1.,
			"SKYSAT": 0.2
		}
	}

	# Define the target location over which images are captured
	targets = [
		Location("sbs", wgs84.latlon(55.863005, -4.243111)),
		Location("nyc", wgs84.latlon(40.749040, -73.985933))
	]

	# Define the Ground Stations to which images are downloaded
	ground_stations = [
		Location("North Pole", wgs84.latlon(90.0, 0.0)),
		Location("South Pole", wgs84.latlon(-90.0, 0.0))
	]

	# Time horizon parameters, between which image capture and download events are found
	t0 = load.timescale().utc(2023, 3, 24)
	t1 = load.timescale().utc(2023, 3, 26)

	satellites_ = []
	for satellite in satellites:
		satellites_.append(Spacecraft(
			satellite,
			[  # Field of regard (half angle, radians)
				platform_attribs["for"][x] for x in platform_attribs["for"]
				if x in satellite.name
			][0],
			[  # Probability a location within the FoR will be acquired
				platform_attribs["aq_prob"][x] for x in platform_attribs["aq_prob"]
				if x in satellite.name
			][0]
		))

	images, downloads = get_all_events(satellites_, targets, ground_stations, t0, t1)
	images = sorted(images)
	downloads = sorted(downloads)

	# For each image event, get the combined-CDF for delivery of the data product to the
	# analyst before time t

	num_dl = 2
	for image in images:
		image.download_opportunities = get_n_following_downloads(image, downloads, num_dl)

	print('')
