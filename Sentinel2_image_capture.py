import os

from datetime import datetime
from suntime import Sun
from Astrid import get_cloud_fraction_from_nc_file
from skyfield.api import load, utc
from math import radians, degrees
from classes import Location, Spacecraft, Contact
from space import  fetch_tle_and_write_to_txt, for_elevation_from_half_angle
from ground import find_city_location
import time 

start_Walltime=time.time()
start_CPUtime = time.process_time()

# Most of the code taken from chris's scripts and adapted. Also adapted some code from Astrid.

# NOTE: This must match the name of the city in the coverage_lat_lng CSV
# Targets = ["Solway firth", "Madrid", "Vilnius", "Bobo-Dioulasso"]
Targets = ["Bobo-Dioulasso"]
cloud_thresholds = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

# Start/End dates of the search
start = datetime(2021, 1, 1, 0, 0, 0)
end = datetime(2022, 1, 1, 0, 0, 0)
start_string = start.strftime("%d-%m-%Y")
end_string = end.strftime("%d-%m-%Y")

platform="sentinel2"
R_E = 6371000.8  # Mean Earth radius


# Contstellation Attributes Dictionary.
PLATFORM_ATTRIBS = {
	"for": {  # Field of regard (half-angle)
		"FLOCK": radians(1.44763),  # 24km swath @ 476km alt
		# TODO Update to be realistic, currently using Sentinel 2 FOV (from Roy et al)
		"SKYSAT": radians(30.),
		"SENTINEL 2": radians(10.3)
	},
	"aq_prob": {  # probability that imaging opportunity results in capture
		# TODO Update to be realistic
		"FLOCK": 1.0,
		"SKYSAT": 0.1,
		"SENTINEL 2":1.0
	}
}

# Get all TLE info for satellites within the timespan
time_start = str(start)[0:10]
time_end = str(end)[0:10]

file_tle = f"tle_data//{platform}_tle_{time_start}_{time_end}.txt"
if not os.path.isfile(file_tle):  # If TLE file doesn't already exist, create it.
	file_norad = f"norad_ids//{platform}_ids.txt"
	fetch_tle_and_write_to_txt(file_tle, file_norad, time_start, time_end)


sats=load.tle_file(file_tle)

# satellites={}
# for s in load.tle_file(file_tle):
#       satellites[s.model.satnum]=s

# Create Spacecraft objects for each item in the TLE dataset
spacecraft_all = []
for satellite in sats:
    satname=satellite.name
    
    # Some TLE's dont have a name assigned, not sure why so just ignore them.
    if satname=='TBA - TO BE ASSIGNED':
        continue
    
    spacecraft_all.append(Spacecraft(		satellite,
		[  # Field of regard (half angle, radians)
			# we are associating all keys in PLATFORM_ATTRIBS["for"] with 'x' and then itterating over them
			PLATFORM_ATTRIBS["for"][x] for x in PLATFORM_ATTRIBS["for"]
			if x in satname
		][0],
		[  # Probability a location within the FoR will be acquired
			PLATFORM_ATTRIBS["aq_prob"][x] for x in PLATFORM_ATTRIBS["aq_prob"]
			if x in satname
		][0]
  ))

# Initialise a list of contacts and dictionary for storing results
Totalcontacts = []
daycontacts = []
contact_per_tar={}

cf_allmean={}
cf_daymean={}
fullContactCount={}


# for each target, run through each spacecraft and find each contact event.
# run through each cloud fraction threshold and count the contacts that meet them.
for target in Targets:
    target_location=Location(target, find_city_location(target, "lat_lon_data/coverage_lat_lng.csv"))
    Targetcontact_num={}
    for i in cloud_thresholds:
        Targetcontact_num[i]=0
    
    cf_alltotal=0
    cf_daytotal=0
    allcontactCount=0
    
    # initialise sun for the target location
    lat=target_location.location.latitude.degrees
    lon=target_location.location.longitude.degrees
    
    sun= Sun(lat, lon)
    
    nextEpoch=0
    satname=spacecraft_all[0].satellite.name
    next_satname=satname
    
    # For each satellite<>location pair, get all contact events during the horizon
    for s in spacecraft_all:
        nextEpoch+=1
        satname=s.satellite.name
        
        # When we reach the end of the list, dont update next name
        if nextEpoch<=len(spacecraft_all)-1:
            next_satname=spacecraft_all[nextEpoch].satellite.name
            
        t0_ts = load.timescale().ut1_jd(s.satellite.epoch.ut1)
        
        # If the next satellite is different or there are no more TLEs to check, 
        # run to the final date. Otherwise just use next epoch
        if next_satname!=satname or nextEpoch>len(spacecraft_all)-1:
            t1_ts = load.timescale().from_datetime(end.astimezone(utc))
        else:
            t1_ts = load.timescale().ut1_jd(spacecraft_all[nextEpoch].satellite.epoch.ut1)
        
        # if the epochs are the same (sometimes they are for some reason) just move to the next loop
        if t0_ts==t1_ts:
            continue
        
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
            day_night=bool()
            
            # if event is 0, it is a rise event, 1 is a peak. If it's neither, instantiate
            if event == 0:
                t_rise = ti
                continue
            if event == 1:
                t_peak = ti
                continue
            
            newContact=Contact(s, target_location, t_rise, t_peak, ti)
            Totalcontacts.append(newContact)
            allcontactCount+=1

            # now find day time cloud fraction during contact, if the data isnt there, use 24hr cloud fraction instead
            cf=get_cloud_fraction_from_nc_file(newContact, 'day')
            is_float = isinstance(cf, float)
            
            if is_float == False:
                cf=get_cloud_fraction_from_nc_file(newContact)
                
            
            cf_alltotal=cf_alltotal+cf

            # If peak contact occurs before sunrise or after sunset, ignore it.
            # clunky but only way i can get this to work for now
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
            
            if daytime==False:
                continue
            
            # If rise and peak are defined AND they happened in the daytime, Instantiate event
            usefulContact=newContact
            
            # now store cloud fraction during contact, if too high, skip it. Otherwise record contact
            cf_daytotal=cf_daytotal+cf

            for ct in cloud_thresholds:
                
                if cf > ct:
                    continue
                
                Targetcontact_num[ct]+=1
        
            daycontacts.append(usefulContact)
      
       
        
        
    cf_daymean[target]=cf_daytotal/Targetcontact_num[100]
    cf_allmean[target]=cf_alltotal/allcontactCount
    fullContactCount[target]=allcontactCount
    contact_per_tar[target]=Targetcontact_num

print("--- Executed in %s seconds (Wall time) ---" % (time.time() - start_Walltime))
print("--- Executed in %s seconds (CPU time) ---" % (time.process_time() - start_CPUtime))

# Print total contacts
print(f"Number of possible images with cloud cover less than threshold between {start_string} and {end_string}:")
for target in contact_per_tar:
    print(f"==> {target}")
    for ct, num in contact_per_tar[target].items():
     print(f"<={ct}% = {num}")
    print(f"Mean cloud fraction(Day Contacts) = {cf_daymean[target]}")
    print(f"Mean cloud fraction(ALL Contacts) = {cf_allmean[target]}")
    print(f"Total Contacts = {fullContactCount[target]}")
    print(f"")


# for contact in Totalcontacts:
#      print(f"Contact time = {contact.t_peak.utc}")