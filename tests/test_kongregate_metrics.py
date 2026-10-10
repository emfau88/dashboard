"""Offline tests for daily Kongregate tracking (no network calls)."""
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from scripts import sync_kongregate as sync


class KongregateMetricsTests(unittest.TestCase):
    def fresh(self):
        return {"schemaVersion": 1, "updatedAt": None, "games": {key: [] for key in sync.GAMES}}

    def now(self):
        return datetime(2026, 10, 11, 6, 35, tzinfo=timezone.utc)

    def test_parse_real_feed_shape(self):
        payload = {"gameplays_count": 1604, "favorites_count": 6, "rating": "2.77",
                   "game_statistics": "<li>...</li>"}
        self.assertEqual(sync.parse_metrics(payload), {"plays": 1604, "favorites": 6, "rating": 2.77})

    def test_invalid_gameplay_counts_are_rejected(self):
        for value in ("1,604", -2, None, True, 3.5):
            with self.subTest(value=value), self.assertRaises(sync.MetricsError):
                sync.parse_metrics({"gameplays_count": value, "favorites_count": 3, "rating": "2.7"})

    def test_bad_rating_or_favorites_are_rejected(self):
        for bad in ("nan", "-1", "9", "garbled"):
            with self.subTest(bad=bad), self.assertRaises(sync.MetricsError):
                sync.parse_metrics({"gameplays_count": 9, "favorites_count": 1, "rating": bad})
        with self.assertRaises(sync.MetricsError):
            sync.parse_metrics({"gameplays_count": 9, "favorites_count": False, "rating": "2.5"})

    def test_daily_idempotency(self):
        data = self.fresh()
        reader = lambda slug: {"plays": 150, "favorites": 3, "rating": 2.75}
        self.assertEqual(sync.collect(data, self.now(), reader), (3, 0, True))
        before = json.dumps(data, sort_keys=True)
        self.assertEqual(sync.collect(data, self.now(), reader), (3, 0, False))
        self.assertEqual(before, json.dumps(data, sort_keys=True))
        self.assertEqual(len(data["games"]["hexfront"]), 1)

    def test_same_day_uses_newest_observation(self):
        data = self.fresh()
        sync.collect(data, self.now(), lambda _: {"plays": 150, "favorites": 3, "rating": 2.75})
        result = sync.collect(data, self.now(), lambda _: {"plays": 152, "favorites": 4, "rating": 2.75})
        self.assertEqual(result, (3, 0, True))
        history = data["games"]["hexfront"]
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["plays"], 152)

    def test_dropped_counter_is_not_recorded(self):
        data = self.fresh()
        data["games"]["hexfront"].append({"date": "2026-10-10", "plays": 200, "source": "user_reported"})
        result = sync.collect(data, self.now(), lambda _: {"plays": 100, "favorites": 1, "rating": None})
        self.assertEqual(result, (2, 1, True))
        self.assertEqual(len(data["games"]["hexfront"]), 1)
        self.assertEqual(data["games"]["hexfront"][0]["plays"], 200)

    def test_partial_failure_does_not_write_zeros(self):
        data = self.fresh()
        def reader(slug):
            if slug == "galalaxy":
                raise sync.MetricsError("Feed down")
            return {"plays": 40, "favorites": 1, "rating": None}
        self.assertEqual(sync.collect(data, self.now(), reader), (2, 1, True))
        self.assertEqual(data["games"]["galalaxy"], [])

    def test_archive_rejects_duplicate_dates(self):
        data = self.fresh()
        data["games"]["hexfront"] = [
            {"date": "2026-10-10", "plays": 30},
            {"date": "2026-10-10", "plays": 31},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "k.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(sync.MetricsError):
                sync.load_archive(path)

    def test_berlin_local_day_used(self):
        data = self.fresh()
        night_utc = datetime(2026, 10, 10, 23, 15, tzinfo=timezone.utc)
        sync.collect(data, night_utc, lambda _: {"plays": 1, "favorites": 1, "rating": 4})
        self.assertEqual(data["games"]["hexfront"][0]["date"], "2026-10-11")


if __name__ == "__main__":
    unittest.main()
