#!/usr/bin/env python3
"""
Abstract Satellite class
"""

__author__ = "Christopher Lowe"

import math
from dataclasses import dataclass, field
from typing import List

import numpy as np
from scipy.integrate import odeint, solve_ivp
from sgp4.api import Satrec
from skyfield.api import EarthSatellite, load, wgs84

import misc as _misc


R_E = 6371000.8
MU_E = 3.986005e+14
J2 = 0.00108263  # J2 Earth oblateness


@dataclass
class Spacecraft:
    """ Spacecraft baseclass """

    tle: List[str] = field(default_factory=lambda: [
        "1 39418U 13066C   23081.74267126  .00004725  00000+0  36677-3 0  9999",
        "2 39418  97.5386 150.1649 0032504  41.8733 318.4969 15.01401933510385"
    ]),  # SKYSAT-A satellite

    def __post_init__(self):
        self.satrec = Satrec.twoline2rv(self.tle[0], self.tle[1])

    def get_position(self, jd: int | float, fr: int | float = 0):
        """
        Get position and velocity at a specific date.
        """
        if jd + fr < self.satrec.jdsatepoch + self.satrec.jdsatepochF:
            raise ValueError("Cannot return position prior to TLE epoch")

        e, r, v = self.satrec.sgp4(jd, fr)
        if e:
            raise Exception(f"Error in SGP4 propagation: {e}")
        return r, v

    def get_position_array(self, jd: np.ndarray, fr: np.ndarray = None):
        if min(jd) + min(fr) < self.satrec.jdsatepoch + self.satrec.jdsatepochF:
            raise ValueError("Cannot return position prior to TLE epoch")

        e, r, v = self.satrec.sgp4_array(jd, fr)
        if any(e):
            raise Exception(f"Error in SGP4 propagation: {e}")
        return r, v


if __name__ == "__main__":
    """ This is executed when run from the command line """

    # Example from the Skyfield docs
    line1 = '1 25544U 98067A   14020.93268519  .00009878  00000-0  18200-3 0  5082'
    line2 = '2 25544  51.6498 109.4756 0003572  55.9686 274.8005 15.49815350868473'
    ts = load.timescale()
    satellite = EarthSatellite(line1, line2, 'ISS (ZARYA)', ts)
    t = ts.utc(2014, 1, 23, 11, 18, 7)
    geocentric = satellite.at(t)

    # Example using Planet's SKYSAT-A satellite and custom class
    tle = """SKYSAT-A
    1 39418U 13066C   23081.74267126  .00004725  00000+0  36677-3 0  9999
    2 39418  97.5386 150.1649 0032504  41.8733 318.4969 15.01401933510385"""
    lines = [t.strip() for t in tle.splitlines()]
    ts = load.timescale()
    s = Spacecraft([lines[1], lines[2]])
    satellite2 = EarthSatellite.from_satrec(s.satrec, ts)
    t = ts.utc(2023, 3, 23, 18, 1)
    geocentric2 = satellite2.at(t)
    print(geocentric2.position.km)
    lat, lon = wgs84.latlon_of(geocentric2)
    print('Latitude:', lat)
    print('Longitude:', lon)

    # Alternative that gives the sub-satellite point (same results as above)
    # lat_lon = wgs84.subpoint_of(geocentric2)
    # print('Latitude_:', lat_lon.latitude)
    # print('Longitude_:', lat_lon.longitude)