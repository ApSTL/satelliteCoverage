"""
Main run file to get image acquisition-delivery probabilities over specific locations,
given cloud coverage data and satellite position data
"""

from datetime import datetime, timedelta
from typing import List, Dict, Union

from classes import Location
from space import get_spacecraft_from_epoch
from data_movement import get_contact_events, probability_no_image_from_set
from ground import find_city_location
from cloud import extract_cloud_data


def main(
		targets: List[str],
		ground_stations: List[Location],
		t_final: datetime = datetime(2022, 6, 10, 20, 0, 0),
		max_age: Union[int, float] = 1.0,
		platform: str = "flock",  # TODO add in "skysat" capabilities
		cloud_threshold: float = 1.0  # maximum acceptable fraction of cloud cover
) -> Dict[str, float]:
	"""
	Return the probabilities, for a set of cities, that data insights will be
	available by a specific date/time, assuming image data less than a certain age
	:param targets: [List] A list of strings, each mapping to a city with "weather" data
	:param ground_stations: [List]
	:param t_final: [datetime] Time by which data insights must be available
	:param max_age: [float] Maximum number of days old that data is still of value
	:param platform: [str] Mapping to the satellite platforms of interest
	:param cloud_threshold: [float] Maximum fraction of cloud cover before an image is
		considered to be of zero value and, therefore, not included in analysis
	"""
	# Define the date and time from which we want to extract TLE data. This should be
	# early enough such that we can be sure not to miss the epoch (i.e. earliest time
	# of interest), considering that there can be gaps in TLE data of a couple of days.
	t_v0 = t_final - timedelta(max_age)  # pre-epoch time as a datatime object
	t_epoch = t_final - timedelta(max_age + 3)  # epoch as a datetime object

	# Instantiate Spacecraft objects, one for each NORAD ID, with its epoch as close
	# to, but later than, the epoch time specified.
	satellites = get_spacecraft_from_epoch(platform, t_epoch, t_v0, t_final)

	downloads = []
	for gs in ground_stations:
		downloads.extend(
			get_contact_events(satellites, gs, t_v0, t_final, False)
		)
	downloads = sorted(downloads)

	probabilities = {}
	for target in targets:
		# Given a particular City, and a particular "Day 0", get the probability that a
		# decision maker will have received useful (processed) data, with which a trading
		# decision can be made. There should be a probability associated with images
		# acquired during preceding days, rather than simply Day 0 imagery.
		city_location = Location(target, find_city_location(target))
		# Get all the potential contact opportunities. These might not necessarily be
		# realised, because of things like cloud cover and/or time of day, but these are
		# events in which the satellite is above the minimum elevation for the target
		images = sorted(
			get_contact_events(satellites, city_location, t_v0, t_final)
		)

		# Get cloud data for the city of interest during our time horizon
		# TODO this should be handled using logic, rather than simply a try-except clause
		try:
			cloud_data = extract_cloud_data(f"weather//{target}.csv", t_v0, t_final)
		except:
			probabilities[target] = "No weather available"
			continue

		# Given the set of images of this city, and the set of Download opportunities,
		# find the probability that NO image is received by Day 0
		no_image = probability_no_image_from_set(
			images,
			downloads,
			t_final,
			cloud_data,
			cloud_threshold,
		)

		# Get the TOTAL probability of having data insights of this target, but this time
		probabilities[target] = 1 - no_image
	return probabilities


if __name__ == "__main__":
	# NOTE: This must match the name of the city in the lat-lon CSV
	cities_input = ["Denver", "New York", "Los Angeles", "London"]

	# Define the Ground Stations to which images are downloaded
	gateways = [
		Location("Yukon", (69.588837, -139.048477)),  # Estimated position
		Location("North Dakota", (48.412949, -97.487445)),  # Estimated position
		Location("Iceland", (64.872589, -22.379039)),  # Estimated position
		Location("Awarura", (-46.528890, 168.381881)),
	]

	# Time by which data is required to be available
	day0 = datetime(2022, 11, 7, 5, 0, 0)

	# time (days) before day0 during which data has "value"
	pre_day0 = 1

	# Run the main simulation
	probabilities_all_cities = main(cities_input, gateways, day0, pre_day0, "flock")

	# Pretty print the outputs
	print(f"Probability of receiving data less than {pre_day0} days old:")
	for city, prob in probabilities_all_cities.items():
		print(f"-> {city}: {prob}")
