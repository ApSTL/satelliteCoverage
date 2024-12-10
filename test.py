from skyfield.api import load
import numpy as np
from datetime import datetime

# Load the TLE file
# Start/End dates of the search
start = datetime(2024, 1, 1, 0, 0, 0)
end = datetime(2024, 1, 7, 23, 59, 59)
start_string = start.strftime("%d-%m-%Y")
end_string = end.strftime("%d-%m-%Y")
time_start = str(start)[0:10]
time_end = str(end)[0:10]

platform="iridium-next"
filename = f"tle_data//{platform}_tle_{time_start}_{time_end}.txt"
satellites = load.tle_file(filename)

# Iterate through satellites and compute argument of latitude
for sat in satellites[:10]:  # Process the first 10 satellites as an example
    name = sat.name
    argpo = sat.model.argpo  # Argument of perigee in radians
    mo = sat.model.mo        # Mean anomaly in radians
    
    # Compute raw and normalized argument of latitude
    u_raw = argpo + mo
    u_normalized = u_raw % (2 * np.pi)
    
    print(f"Satellite: {name}")
    print(f"  Argument of Perigee (argpo): {np.degrees(argpo):.2f} degrees")
    print(f"  Mean Anomaly (mo): {np.degrees(mo):.2f} degrees")
    print(f"  Raw Argument of Latitude (u_raw): {np.degrees(u_raw):.2f} degrees")
    print(f"  Normalized Argument of Latitude (u_normalized): {np.degrees(u_normalized):.2f} degrees")
    print("-" * 50)