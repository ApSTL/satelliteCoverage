
from math import sin, cos, tan, sqrt, pi


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
