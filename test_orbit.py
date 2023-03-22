import unittest
import spacecraft as _spacecraft
import misc as _misc


class MyTestCase(unittest.TestCase):
    def test_100_minute_polar_orbit(self):
        expected_period = 100 * 60
        sma_100_min = _misc.sma_from_period(100 * 60)
        orbit = _spacecraft.Orbit(sma0=sma_100_min)

        # Assert that the orbit period is roughly 100 minutes
        self.assertAlmostEqual(orbit.period, expected_period, 3)

        # Propagate the orbit for 100 minutes
        orbit.propagate(expected_period, 1)

        # Assert that the final position is <100km from the initial position
        self.assertLess(max(orbit.eci[-1] - orbit.eci[0]), 100000)


if __name__ == '__main__':
    unittest.main()
