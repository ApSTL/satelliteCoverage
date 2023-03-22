
from math import sin, cos, tan, sqrt, pi, asin, atan2
import numpy as np


R_E = 6371000.8
MU_E = 3.986005e+14
J2 = 0.00108263  # J2 Earth oblateness


def sma_from_period(period) -> float:
    return (MU_E * (period / (2 * pi)) ** 2) ** (1/3)


def coe_to_mee(coe):
    """ converts from keplerian to modified equinoctial elements

    :param a: semi-major axis
    :param e: eccentricity
    :param i: inclination
    :param raan: right ascension of ascending node
    :param om: argument of perigee
    :param v: true anomaly
    :return [p, f, ...]: Modified equinoctial elements
    """

    a = coe[0]
    e = coe[1]
    i = coe[2]
    raan = coe[3]
    om = coe[4]
    v = coe[5]

    p = a * (1 - e ** 2)
    f = e * cos(om + raan)
    g = e * sin(om + raan)
    h = tan(i / 2) * cos(raan)
    k = tan(i / 2) * sin(raan)
    l = raan + om + v
    return [p, f, g, h, k, l]


def mee_to_cart(mee, mu=MU_E):
    """ converts from mod. equinoctial ele. to cartesian

    :param mee
    :param mu: Grav constant
    :return [rx, ry, rz, vx, vy, vz]: position vector and velocity vectors in cartesian coordinates
    """

    p = mee[0]
    f = mee[1]
    g = mee[2]
    h = mee[3]
    k = mee[4]
    l = mee[5]

    h2 = h ** 2
    k2 = k ** 2
    al2 = h2 - k2
    s2 = 1 + h2 + k2
    cl = cos(l)
    sl = sin(l)
    w = 1 + f * cl + g * sl
    r = p / w
    a = r / s2
    b = (1 / s2) * sqrt(mu / p)

    rx = a * (cl + al2 * cl + 2 * h * k * sl)
    ry = a * (sl - al2 * sl + 2 * h * k * cl)
    rz = 2 * a * (h * sl - k * cl)

    vx = -b * (sl + al2 * sl - 2 * h * k * cl + g - 2 * f * h * k + al2 * g)
    vy = -b * (-cl + al2 * cl + 2 * h * k * sl - f + 2 * g * h * k + al2 * f)
    vz = 2 * b * (h * cl + k * sl + f * h + g * k)

    return [rx, ry, rz, vx, vy, vz]


def eci_to_geod(jdate, r_pos):
    """
    Convert from ECI position to Lat, Lon, Alt position
    :param jdate: Julian Date
    :param r_pos: ECI position vector (m)
    :return lat: Latitude (degrees)
    :return lon: Longitude (degrees)
    :return alt: Altitude (m)
    """
    # Greenwich apparent sidereal time
    gst = gast(jdate)

    r_mag = np.linalg.norm(r_pos)
    geoc_decl = asin(r_pos[2] / r_mag)
    [alt, lat] = geodet(r_mag / 1000., geoc_decl)

    x_ecf = (r_pos[0] * cos(gst)) + (r_pos[1] * sin(gst))
    y_ecf = (r_pos[1] * cos(gst)) - (r_pos[0] * sin(gst))

    lamda = atan2(y_ecf, x_ecf)

    if pi < lamda:
        lon = lamda - 2 * pi

    else:
        lon = lamda

    return lat, lon, alt * 1000


def geodet(rmag, dec):
    """
    geodetic latitude and altitude
    :param rmag: geocentric radius (kilometers)
    :param dec: geocentric declination (radians) (+north, -south; -pi/2 <= dec <= +pi/2)
    :return lat: geodetic latitude (radians) (+north, -south; -pi/2 <= lat <= +pi/2)
    :return alt: geodetic altitude (kilometers)
    """
    req = 6.3781363e+3
    flat = 1 / 298.257

    n = req / rmag
    o = flat * flat

    a = 2 * dec
    p = sin(a)
    q = cos(a)

    a = 4 * dec
    r = sin(a)
    s = cos(a)

    lat = dec + flat * n * p + o * n * r * (n - .25)
    alt = rmag + req * (flat * .5 * (1 - q) + o * (.25 * n - .0625) * (1 - s) - 1)

    return alt, lat


def gast(jdate):
    """ Greenwich apparent sidereal time

    :param jdate: julian date
    :return gst: greenwich siderial time
    """
    dtr = pi/180  # degrees to radians
    atr = dtr/3600  # arc second to radians

    # time arguments
    t = (jdate - 2451545) / 36525 # number of julian centuries since 12:00 01 Jan 2000
    t2 = t * t
    t3 = t * t2

    # fundamental trig arguments (modulo 2pi functions)
    l = (dtr * (280.4665 + 36000.7698 * t)) % (2*pi)
    lp = (dtr * (218.3165 + 481267.8813 * t)) % (2*pi)
    lraan = (dtr * (125.04452 - 1934.136261 * t)) % (2*pi)

    # nutations in longitude and obliquity
    dpsi = atr * (-17.2 * sin(lraan) - 1.32 * sin(2 * l) - 0.23 * sin(2 * lp) + 0.21 * sin(2 * lraan))
    deps = atr * (9.2 * cos(lraan) + 0.57 * cos(2 * l) + 0.1 * cos(2 * lp) - 0.09 * cos(2 * lraan))

    # mean and apparent obliquity of the ecliptic
    eps0 = (dtr * (23 + 26 / 60 + 21.448 / 3600) + atr * (-46.815 * t - 0.00059 * t2 + 0.001813 * t3)) % (2*pi)
    obliq = eps0 + deps

    # greenwich mean and apparent sidereal time
    gstm = (dtr * (280.46061837 + 360.98564736629 * (jdate - 2451545) + 0.000387933 * t2 - t3 / 38710000)) % (2*pi)
    gst = (gstm + dpsi * cos(obliq)) % (2*pi)

    return gst


def eq_of_mo_mee(t, u):
    """
    Orbit equations of motion for Modified equinoctial elements
    """
    # initialise variables to input
    p = u[0]
    f = u[1]
    g = u[2]
    h = u[3]
    k = u[4]
    L = u[5]

    # calculate support parameters
    sinL = sin(L)
    cosL = cos(L)
    w = 1 + f * cosL + g * sinL
    x = sqrt(p / MU_E)
    r = p / w
    s2 = 1 + h ** 2 + k ** 2

    Dr, Dt, Dn = pert_j2_mee(h, k, L, r)

    # calculate rates of change in variables
    dp = ((2 * p * x) / w) * Dt
    df = x * (sinL * Dr + (((w + 1) * cosL + f) / w) * Dt - (
            ((h * sinL - k * cosL) * g) / w) * Dn)
    dg = x * (-cosL * Dr + (((w + 1) * sinL + g) / w) * Dt + (
            ((h * sinL - k * cosL) * f) / w) * Dn)
    dh = (x * s2 * cosL / (2 * w)) * Dn
    dk = (x * s2 * sinL / (2 * w)) * Dn
    dL = (sqrt(MU_E * p) * (w / p) ** 2) + (1 / w) * x * (h * sinL - k * cosL) * Dn

    # return rates of change variables
    return [dp, df, dg, dh, dk, dL]


def pert_j2_mee(h, k, l, r):
    """ calculate perturbation forces due to J2 in MEq frame
    :param h:
    :param k:
    :param l:
    :param r:
    :return:
    """

    x = MU_E * J2 * R_E ** 2 / r ** 4
    y = (1 + h ** 2 + k ** 2) ** 2
    sl = sin(l)
    cl = cos(l)

    dr = -(3 / 2) * x * (1 - (12 * (h * sl - k * cl) ** 2) / y)
    dt = -12 * x * (((h * sl - k * cl) * (h * cl + k * sl)) / y)
    dn = -6 * x * (((1 - h ** 2 - k ** 2) * (h * sl - k * cl)) / y)

    return dr, dt, dn
