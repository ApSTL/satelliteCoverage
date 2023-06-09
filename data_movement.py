from datetime import datetime
from math import degrees
from typing import List, Dict, Union

from skyfield.api import load, utc

from classes import Location, Contact
from cloud import get_cloud_fraction_at_time, extract_cloud_data
from space import for_elevation_from_half_angle
from misc import probability_event_linear_scale

# The number of downloads considered reasonable before data acquired earlier is
# guaranteed to have been downloaded.
MAX_DOWNLOADS_CONSIDERED: int = 2

# Probability of downloading an image during the subsequent X ground station passes.
# E.g. If only one pass is considered, then there's a 100% probability then that pass
# is used. If two passes, then 75% chance the first is used, and 25% the second is used.
DOWNLOAD_PROBABILITY = {
	1: [1.0],
	2: [0.75, 0.25],
	3: [0.6, 0.3, 0.1],
	4: [0.5, 0.25, 0.1, 0.05]
}

# It is unlikely that satellites make use of EVERY download opportunity. This value
# represents the download access frequency, i.e. download will be available every Nth
# pass. So, a lower number here, represents a higher frequency of actually utilising
# downloads. 1 would be using every download, while 10 would be making use of every 10th.
DOWNLOAD_FREQ = 8

T_MIN = 1 / 24  # Time (days) since download before which 0% chance of data arrival
T_MAX = 6 / 24  # Time (days) since download after which 100% chance of data arrival


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


def prob_arrival_via_download(
		t: datetime,
		download: Contact,
		processing_time_min: float = T_MIN,
		processing_time_max: float = T_MAX
) -> float:
	"""
	Probability that data, if it had been downloaded during this "download" event,
	would have been delivered to the customer by time "t", given some minimum and
	maximum amount of necessary processing time (post download).
	:return:
	"""
	t = load.timescale().from_datetime(t.astimezone(utc))

	if t.tt <= (download.t_set + processing_time_min).tt:
		return 0.

	elif t.tt >= (download.t_set + processing_time_max).tt:
		return 1.

	# Replace this function with a different probability function if required.
	return probability_event_linear_scale(
		t,
		download.t_set + processing_time_max,
		download.t_set + processing_time_min
	)


def prob_of_data_by_time(
		image: Contact,
		downloads: List[Contact],
		t_arrival: datetime,
		data_processing_time: Union[List[float], None] = None
) -> float:
	"""
	Return probability that cloud-free data, from an image event, has arrived.

	:param image: Image object
	:param downloads: List of Download objects
	:param t_arrival: Datetime object by when the processed image must have arrived
	:param data_processing_time: List of length 2, containing the minimum and maximum
		processing times
	:return: Probability of arrival
	"""
	if not data_processing_time:
		data_processing_time = [T_MIN, T_MAX]

	downloads_ = [
		d for d in downloads
		if d.t_set.tt > image.t_peak.tt and d.satellite == image.satellite
	]

	# Extracting only every 8th download opportunity, to simulate something closer to
	# the real download contact schedule seen by Planet's FLOCK
	# TODO Make this platform specific, currently hard coded for all
	downloads_trimmed = downloads_[::DOWNLOAD_FREQ]

	# Initiate a variable that tracks the probability that data that WAS delivered would
	# have arrived by this time. This does NOT consider the probability of it actually
	# existing in the first place. E.g. if we're passed the max processing time for two
	# download events, and we're only considering two download events feasible,
	# then this would be 100%
	total_prob_arr_via_download = 0
	for k in range(min(MAX_DOWNLOADS_CONSIDERED, len(downloads_trimmed))):

		prob_arrival_via_d = prob_arrival_via_download(
			t_arrival,
			downloads_trimmed[k],
			data_processing_time[0],
			data_processing_time[1]
		)

		total_prob_arr_via_download += \
			DOWNLOAD_PROBABILITY[MAX_DOWNLOADS_CONSIDERED][k] * prob_arrival_via_d

	# Combine the probability of the image existing and the probability of it having
	# arrived IF it were downloaded, to get the overall probability of
	return total_prob_arr_via_download


def probability_no_image_from_set(
		images: List[Contact],
		downloads: List[Contact],
		day0: datetime,
		cloud_data: Dict[float, float],
		cloud_threshold: float = 1.0
) -> float:
	"""Get the probability that NO image will have been received of a particular location"""
	cumulative_probability_of_no_image = 1.
	for image in images:
		# If the image is not captured during sunlight, skip
		if 18 < image.t_peak.gast < 6:
			continue

		# If the image is deemed "too cloudy", skip
		cloud = get_cloud_fraction_at_time(image.t_peak.tt, cloud_data)
		if cloud > cloud_threshold:
			continue

		p_image_is_cloud_free = (1. - cloud) * image.satellite.aq_prob

		p_image_delivered = prob_of_data_by_time(image, downloads, day0)

		p_image_delivered_and_cloud_free = p_image_delivered * p_image_is_cloud_free

		# Update probability that we'd have received NO image by this time
		cumulative_probability_of_no_image *= 1 - p_image_delivered_and_cloud_free
	return cumulative_probability_of_no_image
