from math import pi, sqrt, cos, sin, acos, asin
from numpy import sign


def ppd(sma, inc, el, lat):
    """
    Return the long-term average number of passes per day.

    PPD for a satellite would have in relation to a point on
    the ground at a certain latitude

    :param sma: Semi-major axis (m)
    :param inc: Orbit inclination (radians)
    :param el: Min elevation of communication (radians)
    :param lat: Latitude of ground node (radians)
    """

    r_earth = 6378145
    mu = 398601000000000
    ecc_earth = 0.08182  # Earth oblateness eccentricity
    day_sid = 86400  # Sidereal Day (s)

    if inc > pi/2:
        inc = pi - inc

    # FRACTION OF REVOLUTIONS CONTAINING A PASS
    # Earth Central Distance (m)
    rL = r_earth * sqrt((cos(lat) ** 2 + (1 - ecc_earth ** 2) * sin(lat) ** 2) / (1 - ecc_earth ** 2 * sin(lat) ** 2))

    # Earth central angle (rads)
    lam = pi/2 - el - asin(rL * cos(el) / sma)

    if inc == 0:
        f1 = sign(lat - lam)
    elif lat == pi/2:
        f1 = sign(pi/2 - lam - min(inc, (pi/2 - inc)))
    else:
        f1 = (sin(lat) * cos(inc) - sin(lam)) / (cos(lat) * sin(inc))

    phi1 = acos(min(1, max(-1, f1)))

    if inc == 0 or lat == pi/2:
        f2 = 1
    else:
        f2 = (sin(lat) * cos(inc) + sin(lam)) / (cos(lat) * sin(inc))

    phi2 = acos(min([1, f2]))

    f = (phi1 - phi2)/pi

    tau = 2 * pi * sqrt(sma**3 / mu)
    ppd = f * (day_sid / tau - cos(inc))
    return ppd
