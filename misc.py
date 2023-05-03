def probability_event_linear_scale(
		x,
		x_min,
		x_max
) -> float:
	"""
	Probability that an event has happened at some time between some min & max,
	given a linear probability distribution between those limits
	:return:
	"""
	return (x - x_min) / (x_max - x_min)
