from math import radians

from skyfield.api import Time, EarthSatellite, wgs84


class Spacecraft:
	def __init__(
			self,
			satellite: EarthSatellite,
			field_of_regard: float = radians(30),
			aq_prob: float = 1.0,
			download_rate: float = 100.
	):
		self.satellite = satellite
		self.for_ = field_of_regard
		self.aq_prob = aq_prob
		self.download_rate = download_rate

	def __repr__(self):
		return self.satellite.satellite.__str__()


class Location:
	def __init__(
			self,
			name: str,
			location: tuple
	):
		self.name = name
		self.location = wgs84.latlon(location[0], location[1])


class Contact:
	"""Space-to-Ground contact base class"""
	def __init__(
			self,
			satellite: Spacecraft,
			target: Location,
			t_rise: Time,
			t_peak: Time,
			t_set: Time
	):
		self.satellite = satellite
		self.target = target
		self.t_rise = t_rise
		self.t_peak = t_peak
		self.t_set = t_set

	@property
	def duration(self):
		return 24 * 60 * 60 * (self.t_set - self.t_rise)

	def __lt__(self, other):				# Define what is meant when comparing one contact to another 
		if self.t_peak.J <= other.t_peak.J:
			return True
		return False
