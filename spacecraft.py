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

import misc as _misc


R_E = 6371000.8
MU_E = 3.986005e+14
J2 = 0.00108263  # J2 Earth oblateness


@dataclass
class Platform:
    """Base class for a spacecraft platform (bus)"""
    pass


@dataclass
class Orbit:
    """Base class for a spacecraft orbit"""
    # sma0: float = R_E + 500000.  # 500km altitude
    # ecc0: float = 0.0
    # inc0: float = math.pi / 2  # 90 deg
    # aop0: float = 0.0
    # raan0: float = 0.0
    # ta0: float = 0.0
    tle_s: str = "1 39429C 13066P 22343.34114583 -.00005658  00000-0 -95669-3 0  3433"
    tle_t: str = "2 39429  97.8100 247.5760 0141660 186.6832 272.9669 14.62999519"
    jd0: int | float = 2460026.  # 12:00, 22 Mar 2023

    eci: np.ndarray = field(init=False, default=None)
    mee: np.ndarray = field(init=False, default=None)
    lla: np.ndarray = field(init=False, default=None)
    times: np.ndarray = None

    def __post_init__(self):
        self.satellite = Satrec.twoline2rv(self.tle_s, self.tle_t)
        self.coe0 = [self.sma0, self.ecc0, self.inc0, self.aop0, self.raan0, self.ta0]
        self.mee0 = _misc.coe_to_mee(self.coe0)

    def propagate(self, duration: int | float = 3600, step: int | float = 1):
        """
        Propagate the orbit for some duration
        :param duration: duration of the propagation (s)
        :param step: propagation step size for the returned values (s)
        :return:
        """
        if step <= 0:
            raise ValueError("Propagation step size must be a positive value")
        self.times = np.arange(0, duration, step)  # time array used for simulation

        # Carry out numerical integration, returning a numpy array of the
        # modified equinoctial elements
        # self.mee = odeint(eq, self.mee0, self.times)
        sol = solve_ivp(
            _misc.eq_of_mo_mee,
            [0, duration],
            self.mee0,
            t_eval=self.times
        )
        self.mee = np.transpose(sol.y)
        self.times = np.transpose(np.atleast_2d(sol.t))

        # get keplerian and cartesian results from modified equinoctial elements
        self.eci = np.array([tuple(_misc.mee_to_cart(x)) for x in self.mee])

        lla = []
        for idx, r_position in enumerate(self.eci[:, 0:3]):
            lla.append(_misc.eci_to_geod(
                self.jd0 + self.times[idx][0] / 86400, r_position))
        self.lla = np.array(lla)

    @property
    def period(self):
        return 2 * math.pi * math.sqrt(self.sma0 ** 3 / MU_E)

    @property
    def velocity0(self):
        return math.sqrt(MU_E * ((2 / self.sma0) - (1 / self.sma0)))


@dataclass
class Spacecraft:
    """ Spacecraft baseclass """

    tle: List[str] = field(default_factory=lambda: [
        "1 39429C 13066P 22343.34114583 -.00005658  00000-0 -95669-3 0 3433",
        "2 39429  97.8100 247.5760 0141660 186.6832 272.9669 14.62999519"
    ])  # DOVE-3 satellite

    def __post_init__(self):
        self.satellite = Satrec.twoline2rv(self.tle[0], self.tle[1])

    def get_position(self, jd: int | float, fr: int | float = 0):
        """
        Get position and velocity at a specific date.
        """
        if jd + fr < self.satellite.jdsatepoch + self.satellite.jdsatepochF:
            raise ValueError("Cannot return position prior to TLE epoch")

        e, r, v = self.satellite.sgp4(jd, fr)
        if e:
            raise Exception(f"Error in SGP4 propagation: {e}")
        return r, v

    def get_position_array(self, jd: np.ndarray, fr: np.ndarray = None):
        if min(jd) + min(fr) < self.satellite.jdsatepoch + self.satellite.jdsatepochF:
            raise ValueError("Cannot return position prior to TLE epoch")

        e, r, v = self.satellite.sgp4_array(jd, fr)
        if any(e):
            raise Exception(f"Error in SGP4 propagation: {e}")
        return r, v


if __name__ == "__main__":
    """ This is executed when run from the command line """
    # main()