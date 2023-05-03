"""
Main run file to get image acquisition-delivery probabilities over specific locations,
given cloud coverage data and satellite position data
"""

from datetime import datetime, timedelta
from typing import List, Dict

from skyfield.api import wgs84

from classes import Location
from space import get_spacecraft_from_epoch
from data_movement import get_contact_events, get_probability_of_no_image
from ground import find_city_location


# Define the Ground Stations to which images are downloaded
GROUND_STATIONS = [
	Location("Yukon", wgs84.latlon(69.588837, -139.048477)),  # Estimated position
	Location("North Dakota", wgs84.latlon(48.412949, -97.487445)),  # Estimated position
	Location("Iceland", wgs84.latlon(64.872589, -22.379039)),  # Estimated position
	Location("Awarura", wgs84.latlon(-46.528890, 168.381881)),
]


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
