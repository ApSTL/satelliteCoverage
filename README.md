# satelliteCoverage
Evaluate the delivery of processed data insights for a set of locations, from a set of satellites.

To run this analysis, call the `main()` function within the `main.py` script, passing the following as input arguments:
 1. **cities** _[List]_ A list of strings, where each string corresponds to the name of a city. This name should match (exactly) the name provided in the `/lat_lon_data/uscities_lat_lon.csv` file. There must also be weather data for this city, within the `/weather/` directory.
 2. **gateways** _[List]_ A list of Skyfield.WGS84.Location objects, representing the ground station locations to which data can be downloaded
 3. **t_final** _[datetime]_ Time by which data insights must be available. E.g. the time at which a decision maker in a hedge fund needs the processed data in order to execute a particular trade.
 4. **max_age** _[float]_ Maximum number of days old that data is still of value. Images opportunities that occur between _t_final - max_age_ and _t_final_ are considered in the analysis.
 5. **platform** _[str]_ Name of the satellite platform type to be considered in the analysis (currently only "flock" is handled, but "skysat" would be another option)
 6. **cloud_threshold** _[float]_ Maximum fraction of cloud cover before an image is considered to be of zero value and, therefore, not included in analysis. Value must be between 0 & 1.

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

## Fetching TLE data
Two line element data is obtained via HTTP request to the Space-Track.org API. The majority of the code in the `space_track_api_script.py` file is taken from https://www.space-track.org/documentation#howto-api_python. The function `space_track_api_request()` within this file will return a list of TLEs for every platform defined by the list of NORAD IDs given in the inputs, between the two times specified (other input args).

Authentication details are stored in the SLTrack.ini file, but if making this functionality public, it is recommended that these attributes are not included in the repository and, instead, accessed from a .env file (or similar)

**NOTE** There are API access limits when interacting with SpaceTrack.org, so be mindful of not making too many requests in a short space of time. Generally speaking. Access limit guidance can be found at https://www.space-track.org/documentation#api

## Constants and other variables
There are a number of constants and global variables used within the model. They are defined as global variables to reduce the passing of arguments into and out of functions, but equally could be defined at the main() level as input arguments.

### Probability of download to subsequent ground station passes [`DOWNLOAD_PROBABILITY`]
This is a Dictionary containing the probability of using _N_ subsequent ground station passes, for download purpose. The keys are the value _N_ and the corresponding values are lists of length |_N_| containing floats that must not sum to greater than 1. For example:
`DOWNLOAD_PROBABILITY` = {
    2: [0.7, 0.2],
    3: [0.5, 0.3, 0.1],
    ...
}
suggests that, if two download opportunities are considered, the probability of using the first one is 70%, while the probability of using the 2nd, is 20%. Alternatively, if 3 are considered, the likelihoods are 50%, 30% and 10%, respectively.

### Number of Downloads considered [`MAX_DOWNLOADS_CONSIDERED`]
This attribute defines the _key_ to be used within the `DOWNLOAD_PROBABILITY` variable.

### Download Frequency [`DOWNLOAD_FREQ`]
During analysis, it was identified that allowing use of _all_ ground station opportunities from the Planet constellation resulted in a ~8x higher download potential than what is suggested via information online. This attribute therefore allows you to "skip" a certain number of download opportunities. For example, if 5 is defined here, only every 5th ground station pass will be considered available. Note that the 1st pass is always considered, after which every _X_ passes are considered.



### Min and max processing time [`T_MIN, TMAX`]
`T_MIN`: The minimum amount of time, from the moment an image is downloaded, until processing begins
`T_MAX`: The amount of time, from the moment an image is downloaded, before it is guaranteed to be downloaded

### Platform-specific attributes [`PLATFORM_ATTRIBUTES`]
A dictionary that contains values for the:
- Field of Regard (`"for"`), represented as the imager half angle (in radians) cone
- Acquisition probability (`"aq_prob"`), representing the probability of an image being captured if the target falls within the satellite's Field of Regard. For Example, a satellite may have the capacity to slew their imager a great deal (large FoR), but only have a relatively small imager footprint. In this case, there might be a small probability the target would be acquired, even when within the FoR.
