from skyfield.api import load, utc
from datetime import datetime


start = datetime(2018, 1, 1, 0, 0, 0)
end = datetime(2019, 1, 1, 0, 0, 0)

t_rise = load.timescale().from_datetime(start.astimezone(utc))

        
t = t_rise.tt(2000, 1, 1, 12, 0)

print('UTC date and time:', t.utc_strftime())
