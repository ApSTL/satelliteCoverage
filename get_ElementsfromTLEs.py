import os
import csv

from datetime import datetime
from skyfield.api import load
from math import degrees
from space import  fetch_tle_and_write_to_txt


# NOTE: A lot of the code is patched together from chris's scripts and adapted. Also adapted some code from Astrid.
# The script gathers TLE data from a constellation during the given timeframe... 
# isolates each satellite then determines all contacts with a series of ground lat/longs...
# the date of each contact is then compared with daily averaged cloud data to determine the probability that the image is cloud free.

# NOTE: This must match the name of the city in the coverage_lat_lng CSV
Targets = ["Solway firth", "Madrid", "Vilnius", "Bobo-Dioulasso"]
prob_thresholds = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

# Start/End dates of the search
start = datetime(2024, 1, 1, 0, 0, 0)
end = datetime(2024, 1, 7, 23, 59, 59)
start_string = start.strftime("%d-%m-%Y")
end_string = end.strftime("%d-%m-%Y")

platform="spire"
R_E = 6371000.8  # Mean Earth radius

# Skyfield timescale for TLE epoch conversion
ts = load.timescale()
start_ts = ts.utc(start.year, start.month, start.day, start.hour, start.minute, start.second)

# Get all TLE info for satellites within the timespan
time_start = str(start)[0:10]
time_end = str(end)[0:10]

file_tle = f"tle_data//{platform}_tle_{time_start}_{time_end}.txt"
if not os.path.isfile(file_tle):  # If TLE file doesn't already exist, create it.
	file_norad = f"norad_ids//{platform}_ids.txt"
	fetch_tle_and_write_to_txt(file_tle, file_norad, time_start, time_end)

satellites={}
for s in load.tle_file(file_tle):
	satnum = s.model.satnum
    # Simplified epoch conversion (21st century only)
	tle_epoch = ts.utc(2000 + s.model.epochyr, s.model.epochdays)

    # Check if this TLE is closer to the start time than the currently stored one
	if satnum not in satellites or abs(tle_epoch - start_ts) < abs(satellites[satnum][1] - start_ts):
		satellites[satnum] = (s, tle_epoch) 


a_data = []
e_data = []
i_data = []
raan_data = []
u0_data = []
elements = []

# Loop through each satellite in the TLE file
for satnum, (satellite, tle_epoch) in satellites.items():
	a = 6378.135*1000* satellite.model.a
	e = 0
	i = degrees(satellite.model.inclo)
	raan = degrees(satellite.model.nodeo)
	u0 = degrees(satellite.model.mo+satellite.model.argpo)
	elements.append([satnum, a, e, i, raan, u0])
 
output_csv = f'satellite_elements_{platform}.csv'
with open(output_csv, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(['Satellite Number','Semi-major axis(m)','eccentricity','inclination(degrees)', 'RAAN (degrees)','Argument of latitude(degrees)'])  # Header
    writer.writerows(elements)  # Write data

print(f"Orbital Elements data saved to {output_csv}")