import os
import csv

from datetime import datetime
from suntime import Sun
from Astrid import get_cloud_fraction_from_nc_file
from skyfield.api import load, utc
from math import radians, degrees
from classes import Location, Spacecraft, Contact
from space import  fetch_tle_and_write_to_txt, for_elevation_from_half_angle
from ground import find_city_location

# NOTE: A lot of the code is patched together from chris's scripts and adapted. Also adapted some code from Astrid.
# The script gathers TLE data from a constellation during the given timeframe... 
# isolates each satellite then determines all contacts with a series of ground lat/longs...
# the date of each contact is then compared with daily averaged cloud data to determine the probability that the image is cloud free.

# NOTE: This must match the name of the city in the coverage_lat_lng CSV
Targets = ["Solway firth", "Madrid", "Vilnius", "Bobo-Dioulasso"]
prob_thresholds = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

# Start/End dates of the search
start = datetime(2024, 1, 1, 0, 0, 0)
end = datetime(2024, 6, 1, 0, 0, 0)
start_string = start.strftime("%d-%m-%Y")
end_string = end.strftime("%d-%m-%Y")

platform="spire"
R_E = 6371000.8  # Mean Earth radius

# Contstellation Attributes Dictionary.
PLATFORM_ATTRIBS = {
	"for": {  # Field of regard (half-angle)
		"FLOCK": radians(1.44763),  # 24km swath @ 476km alt
		# TODO Update to be realistic, currently using Sentinel 2 FOV (from Roy et al)
		"SKYSAT": radians(30.),
		"SENTINEL 2": radians(10.3),
        "LEMUR": radians(10.3)
	},
	"aq_prob": {  # probability that imaging opportunity results in capture
		# TODO Update to be realistic
		"FLOCK": 1.0,
		"SKYSAT": 0.1,
		"SENTINEL 2":1.0,
        "LEMUR":1.0
	}
}

# Get all TLE info for satellites within the timespan
time_start = str(start)[0:10]
time_end = str(end)[0:10]

file_tle = f"tle_data//{platform}_tle_{time_start}_{time_end}.txt"
if not os.path.isfile(file_tle):  # If TLE file doesn't already exist, create it.
	file_norad = f"norad_ids//{platform}_ids.txt"
	fetch_tle_and_write_to_txt(file_tle, file_norad, time_start, time_end)

satellites={}
for s in load.tle_file(file_tle):
      satellites[s.model.satnum]=s

a_data = []
e_data = []
i_data = []
raan_data = []
u0_data = []
elements = []
# Loop through each satellite in the TLE file
for satnum, satellite in satellites.items():
	a = 6378.135*1000* satellite.model.a
	e = 0
	i = degrees(satellite.model.inclo)
	raan = degrees(satellite.model.nodeo)
	u0 = degrees(satellite.model.mo)
	elements.append([satnum, a, e, i, raan, u0])
    
output_csv = 'satellite_elements.csv'
with open(output_csv, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(['Satellite Number','Semi-major axis(m)','eccentricity','inclination(degrees)', 'RAAN (degrees)','Argument of latitude(degrees)'])  # Header
    writer.writerows(elements)  # Write data

print(f"Orbital Elements data saved to {output_csv}")