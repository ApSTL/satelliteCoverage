# satelliteCoverage
Evaluate the delivery of processed data insights for a set of locations, from a set of satellites.

To run this analysis, call the `main()` function within the `main.py` script, passing the following as input arguments:
 1. **cities** _[List]_ A list of strings, where each string corresponds to the name of a city. This name should match (exactly) the name provided in the `/lat_lon_data/uscities_lat_lon.csv` file. There must also be weather data for this city, within the `/weather/` directory.
 2. **t_final** _[datetime]_ Time by which data insights must be available. E.g. the time at which a decision maker in a hedge fund needs the processed data in order to execute a particular trade.
 3. **max_age** _[float]_ Maximum number of days old that data is still of value. Images opportunities that occur between _t_final - max_age_ and _t_final_ are considered in the analysis.
 4. **platform** _[str]_ Name of the satellite platform type to be considered in the analysis (currently only "flock" is handled, but "skysat" would be another option)
 5. **cloud_threshold** _[float]_ Maximum fraction of cloud cover before an image is considered to be of zero value and, therefore, not included in analysis. Value must be between 0 & 1.

The response from this function is a Python `dictionary`, where the keys are the city names (as provided in the `cities` input list) and corresponding values as floats, which represent the **probability that useful data of that city is available prior to `t_final`**.

![General flow of the model operations](/assets/model_flow.PNG)

## General Overview
By **running the main.py file**, the following procedure is executed:
 1. Two-line element sets are fetched, via the [Space-Track API](https://www.space-track.org/documentation#/api), for all satellites defined in the `norad_ids/<platform>_ids.txt` file, where `<platform>` is specified as an input to the main.main() function
 2. Get the TLE, for each unique platform, that is closest to our "value time", i.e. the time from which data has at least some value
 3. Identify contact opportunities with ground stations ("downloads")
 4. For each location (city) of interest...
 5. Identify contact opportunities ("images")
 6. Find the probability of NOT receiving insights from each image by the time required
 7. Find the total probability of NOT receiving ANY images over this location
 8. Find the probability of getting at least one good dataset of each location

## Weather
Each entry in the `/weather/` directory is an hour-by-hour representation of the weather for a particular city. **NOTES**:
 1. There must be a "clouds_all" heading, under which there should be a value between 0 and 100, where 0 is cloud-free and 100 is fully overcast.
 2. The name of the file must match the name of the City as defined in the list of cities provide as an input to the main.main() function.
