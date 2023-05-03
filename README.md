# satelliteCoverage
Evaluate the delivery of processed data insights for a set of locations, from a set of satellites.

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
