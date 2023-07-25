import os

from datetime import datetime


from Astrid import get_cloud_fraction_from_nc_file
from skyfield.api import load, utc
from math import radians, degrees
from classes import Location, Spacecraft, Contact
from space import  fetch_tle_and_write_to_txt, for_elevation_from_half_angle
from ground import find_city_location

start = datetime(2018, 1, 1, 0, 0, 0)
end = datetime(2019, 1, 1, 0, 0, 0)

ts = load.timescale()   
t = ts.tt(2000, 1, 1, 12, 0)

print('UTC date and time:', t.utc_strftime())
