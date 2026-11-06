import unittest

from date import geo


class GeoTests(unittest.TestCase):
    def test_validate(self):
        self.assertEqual(geo.validate_coordinates("40.7", "-74"), (40.7, -74.0))
        for lat, lon in [("abc", 1), (None, 1), ("nan", 0), (0, "inf"), (91, 0), (0, 181)]:
            with self.assertRaises(ValueError):
                geo.validate_coordinates(lat, lon)

    def test_snap_rounds_to_the_grid_and_is_idempotent(self):
        self.assertEqual(geo.snap(40.71281, -74.00601), (40.71, -74.01))
        once = geo.snap(51.50735, -0.12776)
        self.assertEqual(geo.snap(*once), once)

    def test_haversine(self):
        self.assertEqual(geo.haversine_km(10, 20, 10, 20), 0)
        self.assertTrue(3900 < geo.haversine_km(40.7128, -74.0060, 34.0522, -118.2437) < 3980)
        self.assertAlmostEqual(geo.haversine_km(0, 179.5, 0, -179.5), 111.19, delta=0.1)

    def test_labels_are_coarse(self):
        self.assertEqual(geo.distance_label(0.3), "Less than 2 km away")
        self.assertEqual(geo.distance_label(7.8), geo.distance_label(9.9))
        self.assertEqual(geo.distance_label(55.6), "Less than 75 km away")
        self.assertEqual(geo.distance_label(222), "More than 200 km away")
        self.assertIsNone(geo.distance_label(None))


if __name__ == "__main__":
    unittest.main()
