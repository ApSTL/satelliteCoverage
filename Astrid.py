from classes import Contact
from netCDF4 import Dataset
import numpy as np

# Astrids code, just making it into a function
def get_cloud_fraction_from_nc_file(
    c: Contact,
    fraction: str='',    
    
) ->float:

    contact_year= c.t_peak.utc_strftime('%Y')
    contact_date= c.t_peak.utc_strftime('%Y%m%d')

    
    if fraction=='':
        fraction_type='cfc'
    else:
        fraction_type=f"cfc_{fraction}"  
        
    
    nc_f = f"Global_Cloud_Data_{contact_year}/CFCdm{contact_date}000040019AVPOS01GL.nc"  # Your filename

    # 2018 file names are different, not sure why
    if contact_year=='2018':
        nc_f = f"Global_Cloud_Data_{contact_year}/CFCdm{contact_date}000000219AVPOSE1GL.nc"  # Your filename

    nc_fid = Dataset(nc_f, 'r')  # Dataset is the class behavior to open the file and create an instance of the ncCDF4 class

    lats = nc_fid.variables['lat'][:]  # extract/copy the data
    lons = nc_fid.variables['lon'][:]

    # string 'cfc_day' indicates im only pulling the mean cloud cover from the daytime hours
    cfc = nc_fid.variables[fraction_type][:]

    lat = c.target.location.latitude.degrees
    lon = c.target.location.longitude.degrees

    minlat = lat - 0.2
    maxlat = lat + 0.2

    minlon = lon - 0.2
    maxlon = lon + 0.2

    indlat = np.where((lats < maxlat) & (lats > minlat))
    indlon = np.where((lons < maxlon) & (lons > minlon))

    cfc_day = np.mean(cfc[0,indlat[:],indlon[:]])
    
    return cfc_day