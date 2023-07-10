from datetime import datetime, timedelta
from typing import List, Dict, Union

from classes import Location
from space import get_spacecraft_from_epoch
from data_movement import get_contact_events, probability_no_image_from_set
from ground import find_city_location
from cloud import extract_cloud_data

# NOTE: This must match the name of the city in the coverage_lat_lng CSV

#Targets = ["Solway firth", "Madrid", "Bobo-Dioulasso", "Vilnius"]
Targets = ["Denver", "New York", "Los Angeles", "London"]

# Start/End dates of the search
start = datetime(2022, 1, 1, 0, 0, 0)
end = datetime(2023, 1, 1, 0, 0, 0)
start_string = start.strftime("%d-%m-%Y")
end_string = end.strftime("%d-%m-%Y")

satellites = get_spacecraft_from_epoch("sentinel2", start, t_v0, end)


for target in Targets:
    target_location=Location(target, find_city_location(target, "lat_lon_data/uscities_lat_lng.csv"))




# Pretty print the outputs
print(f"Number of possible cloud-free images between {start_string} and {end_string}:")


#for city, prob in probabilities_all_cities.items():
	#print(f"-> {city}: {prob}")