"""Run with: python -m unittest discover -s tests -v"""

import unittest
from datetime import datetime, timezone

from vessel_data import normalize_vessels


class NormalizeVesselsTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc)

    def test_moving_vessel_coordinates_and_speed(self):
        features = [{
            "id": 123456789,
            "geometry": {"type": "Point", "coordinates": [4.25, 51.91]},
            "properties": {"mmsi": 123456789, "kind": "vessel", "name": "TEST SHIP", "sog": 12.5, "seen": "2026-11-09T11:55:00Z"},
        }]
        rows = normalize_vessels(features, self.now)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["lat"], 51.91)
        self.assertEqual(rows[0]["lon"], 4.25)
        self.assertEqual(rows[0]["status"], "Moving")
        self.assertEqual(rows[0]["age_minutes"], 5.0)

    def test_stationary_is_not_called_anchored(self):
        features = [{
            "geometry": {"type": "Point", "coordinates": [9.9, 53.5]},
            "properties": {"mmsi": 111111111, "sog": 0.3},
        }]
        self.assertEqual(normalize_vessels(features, self.now)[0]["status"], "Nearly stationary")

    def test_non_vessel_and_invalid_geometry_excluded(self):
        features = [
            {"geometry": {"type": "Point", "coordinates": [10, 60]}, "properties": {"kind": "aton", "mmsi": 111}},
            {"geometry": None, "properties": {"kind": "vessel", "mmsi": 222}},
            {"geometry": {"type": "Point", "coordinates": [500, 60]}, "properties": {"kind": "vessel", "mmsi": 333}},
        ]
        self.assertEqual(normalize_vessels(features, self.now), [])

    def test_missing_speed_and_deduplication(self):
        vessel = {"geometry": {"type": "Point", "coordinates": [10, 60]}, "properties": {"mmsi": 123}}
        rows = normalize_vessels([vessel, vessel], self.now)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["status"], "Unknown speed")
        self.assertIsNone(rows[0]["speed_kn"])


if __name__ == "__main__":
    unittest.main()
