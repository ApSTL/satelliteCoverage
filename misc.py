from typing import Union


def probability_event_linear_scale(
		x: Union[float, int],
		x_max: Union[float, int],
		x_min: Union[float, int] = 0
) -> float:
	"""
	Probability that an event has happened at some time between some min & max,
	given a linear probability distribution between those limits
	:return:
	"""
	return (x - x_min) / (x_max - x_min)
