"""
Main run file to get image acquisition-delivery probabilities over specific locations,
given cloud coverage data and satellite position data
"""

from skyfield.api import wgs84, load, Time


class Image:
	"""Image base class"""
	def __init__(
			self, target: str, time_capture: Time, satellite: str, cloud: float = 0.
	):
		self.target = target
		self.time = time_capture
		self.satellite = satellite
		self.cloud = cloud


class Download:
	"""Download event base class"""
	def __init__(self, ground_station: str, start: Time, end: Time, satellite: str):
		self.ground_station = ground_station
		self.start = start
		self.end = end
		self.satellite = satellite

	@property
	def duration(self):
		return 24 * 60 * 60 * (self.end - self.start)


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
	ground_stations = {
		"North Pole": wgs84.latlon(90.0, 0.0),
		"South Pole": wgs84.latlon(-90.0, 0.0)
	}

	# Time horizon parameters, between which image capture and download events are found
	t0 = load.timescale().utc(2023, 3, 24)
	t1 = load.timescale().utc(2023, 3, 26)

	# Data store for image events. Each key corresponds to a particular target location
	# (using their ID), and the value is an empty list that will get populated with
	# discrete image events and their associated information
	image_events = {target: [] for target in targets}
	download_events = {gs: [] for gs in ground_stations}

	for satellite in satellites:
		for target, location in targets.items():
			# Get the rise, culmination and fall for all passes between this
			# satellite:target pair during the time horizon
			t, events = satellite.find_events(location, t0, t1, altitude_degrees=30.0)
			for ti, event in zip(t, events):
				if event != 1:  # If this is NOT the "peak" of the pass
					continue
				image_events[target].append(
					Image(target, ti, satellite.name)
				)

		t_rise = None
		for gs, location in ground_stations.items():
			t, events = satellite.find_events(location, t0, t1, altitude_degrees=10.0)
			for ti, event in zip(t, events):
				# If the event is 0 (i.e. "rise"), store the rise event, else if it's
				# 0 (i.e. "culmination"), continue
				if event == 0:
					t_rise = ti
					continue
				if event == 1:
					continue
				if not isinstance(t_rise, Time):
					continue
				# So long as a rise time has been defined, instantiate the Download event
				download_events[gs].append(
					Download(gs, t_rise, ti, satellite.name)
				)

	print('')
