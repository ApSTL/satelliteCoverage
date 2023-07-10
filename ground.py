import csv

# Josh - changed filepath to file with every city in the world rather than just USA
def find_city_location(
		city_name: str,
		#filepath: str = "lat_lon_data/uscities_lat_lng.csv"
		filepath: str = "lat_lon_data/worldcities.csv"
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
			if k == 0:												# If this is the first row, find the indices that indicate the city name, lat and long
				col_name = row.index("city_ascii")
				col_lat = row.index("lat")
				col_lon = row.index("lng")
				continue
			if row[col_name] == city_name:							# If we found the correct city, return the lat and long values
				return float(row[col_lat]), float(row[col_lon])

	raise ValueError(f"City {city_name} not found in the file")
