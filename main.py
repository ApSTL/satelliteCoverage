"""
Main run file to get image acquisition-delivery probabilities over specific locations,
given cloud coverage data and satellite position data
"""

from skyfield.api import wgs84, load, Time


class Image:
	"""Image base class"""
	def __init__(
			self, time_capture: Time, satellite: str, cloud: float = 0.):
		self.time = time_capture
		self.satellite = satellite
		self.cloud = cloud


if __name__ == "__main__":
	# Fetch the latest TLEs for all of Planet's satellites
	planet_url = "http://celestrak.com/NORAD/elements/planet.txt"

	# Instantiate an "skyfield.EarthSatellite" object for each of the TLE entries. This
	# is a satellite object that has built-in functionality for such things as rise and
	# set times over a particular location on the ground. It's "epoch" is based on the
	# TLE used to generate it
	satellites = load.tle_file(planet_url)

	# Define the target location over which images are captured
	targets = {
		"sbs": wgs84.latlon(55.863005, -4.243111),
		"nyc": wgs84.latlon(40.749040, -73.985933),
	}

	# List of Ground Station objects to which images are downloaded
	ground_stations = [
		{
			"name": "North Pole",
			"location": wgs84.latlon(90.0, 0.0)
		}, {
			"name": "North Pole",
			"location": wgs84.latlon(-90.0, 0.0)
		}
	]

	# Time horizon parameters, between which image capture and download events are found
	t0 = load.timescale().utc(2023, 3, 24)
	t1 = load.timescale().utc(2023, 3, 26)

	# Data store for image events. Each key corresponds to a particular target location
	# (using their ID), and the value is an empty list that will get populated with
	# discrete image events and their associated information
	image_events = {target: [] for target in targets}

	for target, location in targets.items():
		for satellite in satellites:
			# Get the rise, culmination and fall for all passes between this
			# satellite:target pair during the time horizon
			t, events = satellite.find_events(location, t0, t1, altitude_degrees=30.0)
			for ti, event in zip(t, events):
				if event == 1:  # If this is the "peak" of the pass
					image_events[target].append(Image(ti, satellite.name))

	print('')
