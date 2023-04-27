from typing import Dict
from bisect import bisect


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

