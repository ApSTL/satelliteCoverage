import os

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
start = datetime(2023, 1, 1, 0, 0, 0)
end = datetime(2024, 1, 1, 0, 0, 0)
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

# Create Spacecraft objects for each item in the TLE dataset
spacecraft_all = []
for satellite_id, satellite in satellites.items():
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

# Initialise a list of contacts and disctionary for storing results
contacts = []
contact_per_tar={}

# for each target, run through each spacecraft and find each contact event.
# run through each cloud fraction threshold and count the contacts that meet them.
for target in Targets:
    target_location=Location(target, find_city_location(target, "lat_lon_data/coverage_lat_lng.csv"))
    
    # initialise sun for the target location
    lat=target_location.location.latitude.degrees
    lon=target_location.location.longitude.degrees
    
    sun= Sun(lat, lon)

    Targetcontact_num={}
    for i in prob_thresholds:
        Targetcontact_num[i]=0
    
    # For each satellite<>location pair, get all contact events during the horizon
    for s in spacecraft_all:
    
        t0_ts = load.timescale().from_datetime(start.astimezone(utc))
        t1_ts = load.timescale().from_datetime(end.astimezone(utc))
        
        # Set the elevation angle above the horizon that defines "contact",
	    # depending on whether the location is a Target or Ground Station
        elev_angle = degrees(for_elevation_from_half_angle(
			s.for_,s.satellite.model.altp * R_E))
        
        t, events = s.satellite.find_events(
			target_location.location, t0_ts,t1_ts, altitude_degrees=elev_angle)
        # Pre-set times
        t_rise = start
        t_peak= start
        
        for ti, event in zip(t, events):
            # if event is 0, it is a rise event, 1 is a peak. If it's neither, instantiate

            if event == 0:
                t_rise = ti
                continue
            if event == 1:
                t_peak = ti
                continue
            
            # If peak contact occurs before sunrise or after sunset, ignore it.
            # TODO clunky but only way i can get this to work for now (numpy64 error)
            ContactTime=t_peak.utc
            year=int(ContactTime.year)
            month=int(ContactTime.month)
            day=int(ContactTime.day)
            hour= int(ContactTime.hour)
            minute= int(ContactTime.minute)
            second=int(ContactTime.second)
            
            ImageTime=datetime(year,month,day,hour,minute,second).astimezone(utc)
           
            sunrise=sun.get_sunrise_time(ImageTime)
            sunset=sun.get_sunset_time(ImageTime)
            
            daytime=ImageTime>sunrise and ImageTime<sunset
            
            # NOTE Remove if you only care about contacts, not daytime images.
            # if daytime==False:
            #     continue

            # If rise and peak are defined AND they happened in the daytime, Instantiate event
            newContact=Contact(s, target_location, t_rise, t_peak, ti)

            # NOTE Again if you only care about number of contacts, remove this part
            # now find cloud fraction during contact, if too high, skip it. Otherwise record contact
            # cf=get_cloud_fraction_from_nc_file(newContact)
            # prob_cloud_free=100-cf
            
            for pt in prob_thresholds:
                
            #     if prob_cloud_free > pt:
            #         continue
                
                Targetcontact_num[pt]+=1
        
            contacts.append(newContact)
        
    contact_per_tar[target]=Targetcontact_num

# Print total contacts
# print(f"Number of images with probability of being cloud free between {start_string} and {end_string}:")
for target in contact_per_tar:
    print(f"==> {target}")
    prev_pt=0
    prev_num=0
    
    for pt, num in contact_per_tar[target].items():
     print(f"{prev_pt}-{pt}% = {num-prev_num}")
     prev_pt=pt
     prev_num=num
     
    print(f"Total = {num}")
    print(f"")
    
# for contact in contacts:
#     print('UTC date and time:', contact.t_peak.utc)
