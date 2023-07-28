from datetime import datetime, timedelta
from classes import Location
from ground import find_city_location
from netCDF4 import Dataset
import numpy as np

# botched together to average out a years worth of daily averaged cloud data. 


Targets = ["Solway firth", "Madrid", "Vilnius", "Bobo-Dioulasso"]

cf=0
cf_total={}

for t in Targets:
    cf_total[t]=0

cfmean={}
day_count=0
oneday=timedelta(days=1)


date = datetime(2021, 1, 1, 0, 0, 0)
datestring=date.strftime("%Y%m%d")
startyear=date.strftime("%Y")
year=startyear

while year == startyear:

    for target in Targets:
        
        #for each target grab the lat/longs, get the cloud fraction on that day then add it to the total

        target_location=Location(target, find_city_location(target, "lat_lon_data/coverage_lat_lng.csv"))
        lat=target_location.location.latitude.degrees
        lon=target_location.location.longitude.degrees

        nc_f = f"Global_Cloud_Data_{year}/CFCdm{datestring}000040019AVPOS01GL.nc"  # Your filename

        # 2018 file names are different, not sure why
        if year=='2018':
            nc_f = f"Global_Cloud_Data_{year}/CFCdm{datestring}000000219AVPOSE1GL.nc"  # Your filename

        nc_fid = Dataset(nc_f, 'r')  # Dataset is the class behavior to open the file and create an instance of the ncCDF4 class

        lats = nc_fid.variables['lat'][:]  # extract/copy the data
        lons = nc_fid.variables['lon'][:]

        cfc = nc_fid.variables['cfc'][:]

        minlat = lat - 0.2
        maxlat = lat + 0.2

        minlon = lon - 0.2
        maxlon = lon + 0.2

        indlat = np.where((lats < maxlat) & (lats > minlat))
        indlon = np.where((lons < maxlon) & (lons > minlon))

        cf = np.mean(cfc[0,indlat[:],indlon[:]])

        cf_total[target]=cf_total[target]+cf
    
    # incriment the day and go again
    day_count+=1
    date += oneday
    year=date.strftime("%Y")
    datestring=date.strftime("%Y%m%d")

# When everything is counted, print the results.
# Print total contacts
print(f"Annual Mean Cloud Fraction of {startyear}:")
for target in Targets:
    print(f"==> {target} = {cf_total[target]/day_count}")

    



