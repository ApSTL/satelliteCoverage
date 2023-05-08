import csv

from classes import Location


# Define the Ground Stations to which images are downloaded
GROUND_STATIONS = [
	Location("Yukon", (69.588837, -139.048477)),  # Estimated position
	Location("North Dakota", (48.412949, -97.487445)),  # Estimated position
	Location("Iceland", (64.872589, -22.379039)),  # Estimated position
	Location("Awarura", (-46.528890, 168.381881)),
]


def find_city_location(
		city_name: str,
		filepath: str = "lat_lon_data/uscities_lat_lng.csv"
) -> tuple:
	"""
	Return a location object (lat lon) for a named city (city must be in the CSV).

	:param city_name: String of city for which the Lat Lon is required
	:param filepath: String of the path where the locations file is located
	:return:
	"""

	with open(filepath, newline='') as csvfile:
		locations = csv.reader(csvfile, quotechar='|')
		for k, row in enumerate(locations):
			if k == 0:
				col_name = row.index("city_ascii")
				col_lat = row.index("lat")
				col_lon = row.index("lng")
				continue
			if row[col_name] == city_name:
				return float(row[col_lat]), float(row[col_lon])

	raise ValueError(f"City {city_name} not found in the file")
