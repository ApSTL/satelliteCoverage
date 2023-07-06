import os
from math import acos, sin, pi, radians, sqrt, cos, asin
from typing import List, Dict, Union
from numpy import sign
from datetime import datetime

from skyfield.api import load, utc, Timescale, EarthSatellite

from classes import Spacecraft
from space_track_api_script import space_track_api_request

# Josh - Added arbitrary Sentinel-2 numbers.
PLATFORM_ATTRIBS = {
	"for": {  # Field of regard (half-angle)
		"FLOCK": radians(1.44763),  # 24km swath @ 476km alt
		# TODO Update to be realistic
		"SKYSAT": radians(30.),
		"SENTINEL2": radians(1.5)
	},
	"aq_prob": {  # probability that imaging opportunity results in capture
		# TODO Update to be realistic
		"FLOCK": 1.0,
		"SKYSAT": 0.1,
		"SENTINEL2":1.0
	}
}


# TODO Not currently used, but was added in as a way to perhaps better dictate which
#  ground station passes to consider as "usable" for each platform.
def ppd(sma, inc, el, lat):
	"""
	Return the long-term average number of passes per day.

	PPD for a satellite would have in relation to a point on
	the ground at a certain latitude

	:param sma: Semi-major axis (m)
	:param inc: Orbit inclination (radians)
	:param el: Min elevation of communication (radians)
	:param lat: Latitude of ground node (radians)
	"""

	r_earth = 6378145
	mu = 398601000000000
	ecc_earth = 0.08182  # Earth oblateness eccentricity
	day_sid = 86400  # Sidereal Day (s)

	if inc > pi/2:
		inc = pi - inc

	# FRACTION OF REVOLUTIONS CONTAINING A PASS
	# Earth Central Distance (m)
	rL = r_earth * sqrt((cos(lat) ** 2 + (1 - ecc_earth ** 2) * sin(lat) ** 2) / (1 - ecc_earth ** 2 * sin(lat) ** 2))

	# Earth central angle (rads)
	lam = pi/2 - el - asin(rL * cos(el) / sma)

	if inc == 0:
		f1 = sign(lat - lam)
	elif lat == pi/2:
		f1 = sign(pi/2 - lam - min(inc, (pi/2 - inc)))
	else:
		f1 = (sin(lat) * cos(inc) - sin(lam)) / (cos(lat) * sin(inc))

	phi1 = acos(min(1, max(-1, f1)))

	if inc == 0 or lat == pi/2:
		f2 = 1
	else:
		f2 = (sin(lat) * cos(inc) + sin(lam)) / (cos(lat) * sin(inc))

	phi2 = acos(min([1, f2]))

	f = (phi1 - phi2)/pi

	tau = 2 * pi * sqrt(sma**3 / mu)
	ppd = f * (day_sid / tau - cos(inc))
	return ppd


def for_elevation_from_half_angle(
		half_angle: Union[int, float],
		altitude: Union[int, float],
) -> float:
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


def fetch_tle_and_write_to_txt(
		filename_tle: str,
		filename_norad: str,
		epoch_time: str,
		end_time: str
) -> None:
	with open(filename_norad, "r") as file_norads:
		norad_ids = file_norads.read()

	# Get all TLE data for each satellite in the list between the start and end dates
	tle_response = space_track_api_request(epoch_time, end_time, norad_ids)

	# Write the retrieved TLE data to a text file
	with open(filename_tle, "w", newline="") as text_file:
		text_file.write(tle_response.text)


def get_satellites_closest_to_epoch(
		file_with_tle_data: str,
		epoch: Timescale
) -> Dict[str, EarthSatellite]:
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
		platform: str,
		pre_epoch_time: datetime,
		epoch: datetime,
		end_time: datetime
) -> List[Spacecraft]:
	# Format the different times as required
	pre_epoch_time_str = str(pre_epoch_time)[0:10]
	end_time_str = str(end_time)[0:10]

	file_tle = f"tle_data//{platform}_tle_{pre_epoch_time_str}_{end_time_str}.txt"
	if not os.path.isfile(file_tle):  # Skip if we already have this data
		file_norad = f"norad_ids//{platform}_ids.txt"
		fetch_tle_and_write_to_txt(file_tle, file_norad, pre_epoch_time_str, end_time_str)

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
				# we are associating all keys in PLATFORM_ATTRIBS["for"] with 'x' and then itterating over them
				PLATFORM_ATTRIBS["for"][x] for x in PLATFORM_ATTRIBS["for"]
				if x in satellite.name
			][0],
			[  # Probability a location within the FoR will be acquired
				PLATFORM_ATTRIBS["aq_prob"][x] for x in PLATFORM_ATTRIBS["aq_prob"]
				if x in satellite.name
			][0]
		))
	return spacecraft_all
