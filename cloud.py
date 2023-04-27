from typing import Dict
from bisect import bisect

from datetime import datetime
import csv

from skyfield.api import load


def get_cloud_fraction_at_time(
		t: float,
		clouds: Dict
) -> float:
	idx = bisect(list(clouds), t)
	t0 = list(clouds)[idx]

	if idx == len(clouds) - 1:
		return clouds[t0]

	t1 = list(clouds)[idx+1]

	# TODO extrapolate between t0 & t1 to get actual cloud cover
	return clouds[t0]


def extract_cloud_data(
		filepath: str,
		start: datetime,
		end: datetime
) -> Dict:
	"""
	Import cloud cover fraction data from CSV file (obtained from openweathermap) between
	two dates, for a particular location.

	:param filepath: [str] name of location of interest (must match the name of the csv)
	:param start: [datetime.datetime] Time at which cloud data starts
	:param end: [datetime.datetime] Time at which cloud data ends
	:return: [Dict] {Julian Date: cloud fraction}
	"""
	cloud_info = {}
	with open(filepath, newline='') as csvfile:
		city_weather = csv.reader(csvfile, quotechar='|')
		for row in city_weather:
			if city_weather.line_num == 1:
				cloud_idx = row.index("clouds_all")
				continue
			time_ = datetime.fromisoformat(row[1][0:19])
			if time_ < start or time_ > end:
				continue
			time_ts = load.timescale().utc(time_.year, time_.month, time_.day, time_.hour)
			cloud_info[time_ts.tt] = int(row[cloud_idx])/100
	return cloud_info
