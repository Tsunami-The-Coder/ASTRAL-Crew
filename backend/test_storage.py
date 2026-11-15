"""Offline checks: python3 -m unittest backend.test_storage -v"""

import tempfile
import unittest
from pathlib import Path

from backend.storage import SnapshotStore


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "test.sqlite3"
        self.store = SnapshotStore(self.path)
        self.store.initialize()

    def test_empty_database(self):
        self.assertIsNone(self.store.latest())
        self.assertEqual(self.store.history(), [])

    def test_history_orders_event_times_and_limits_to_newest(self):
        for minute in (3, 1, 2):
            self.store.save_synthetic(f"2026-11-14T12:0{minute}:00Z", {"minute": minute})
        rows = self.store.history(limit=2)
        self.assertEqual([row["payload"]["minute"] for row in rows], [2, 3])
        self.assertEqual(rows[-1], self.store.latest())

    def test_history_inclusive_bounds_and_preserved_nulls(self):
        for minute in range(3):
            self.store.save_synthetic(f"2026-11-14T12:0{minute}:00Z", {"voice": None})
        rows = self.store.history(start="2026-11-14T12:01:00+00:00",
                                  end="2026-11-14T12:02:00Z")
        self.assertEqual(len(rows), 2)
        self.assertIsNone(rows[0]["payload"]["voice"])
        self.assertEqual(self.store.history(start="2026-11-15T00:00:00Z"), [])

    def test_history_equal_timestamps_use_insertion_order(self):
        ids = [self.store.save_synthetic("2026-11-14T12:00:00Z", {}) for _ in range(3)]
        self.assertEqual([row["id"] for row in self.store.history(limit=2)], ids[-2:])

    def test_history_invalid_query(self):
        for limit in (0, -1, True, 1.5, 10001):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                self.store.history(limit=limit)
        with self.assertRaises(ValueError):
            self.store.history(start="bad")
        with self.assertRaises(ValueError):
            self.store.history(end="2026-11-14T12:00:00")
        with self.assertRaises(ValueError):
            self.store.history(start="2026-11-15T00:00:00Z", end="2026-11-14T00:00:00Z")

    def test_four_crew_round_trip_and_reopen(self):
        payload = {
            "crew": [{"crew_id": f"AST-{number:02}", "voice": None}
                     for number in range(1, 5)],
            "environment": {"co2_percent": 0.1},
        }
        identifier = self.store.save_synthetic("2026-11-14T12:00:00Z", payload)
        reopened = SnapshotStore(self.path)
        reopened.initialize()
        result = reopened.latest()
        self.assertEqual(result["id"], identifier)
        self.assertEqual(result["payload"], payload)
        self.assertEqual(result["data_origin"], "synthetic")

    def test_latest_uses_event_time_not_arrival_order(self):
        self.store.save_synthetic("2026-11-14T12:00:00.1Z", {"value": "new"})
        self.store.save_synthetic("2026-11-14T12:00:00+00:00", {"value": "old"})
        self.assertEqual(self.store.latest()["payload"]["value"], "new")

    def test_invalid_timestamps(self):
        for timestamp in (None, "bad", "2026-11-14", "2026-11-14T12:00:00",
                          "2026-11-14T12:00:00+01:00"):
            with self.subTest(timestamp=timestamp), self.assertRaises(ValueError):
                self.store.save_synthetic(timestamp, {})
        self.assertIsNone(self.store.latest())

    def test_invalid_payloads_leave_database_empty(self):
        for payload in ([], {1: "bad key"}, {"x": float("nan")},
                        {"x": float("inf")}, {"x": object()}, {"x": (1, 2)}):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                self.store.save_synthetic("2026-11-14T12:00:00Z", payload)
        self.assertIsNone(self.store.latest())


if __name__ == "__main__":
    unittest.main()
