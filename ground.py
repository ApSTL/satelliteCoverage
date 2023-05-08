import csv

from skyfield.api import wgs84

from classes import Location


# Define the Ground Stations to which images are downloaded
GROUND_STATIONS = [
	Location("Yukon", wgs84.latlon(69.588837, -139.048477)),  # Estimated position
	Location("North Dakota", wgs84.latlon(48.412949, -97.487445)),  # Estimated position
	Location("Iceland", wgs84.latlon(64.872589, -22.379039)),  # Estimated position
	Location("Awarura", wgs84.latlon(-46.528890, 168.381881)),
]


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
