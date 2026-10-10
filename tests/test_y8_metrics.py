"""Offline verification of Y8 HTML parsing, safe daily archiving and failures."""
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from scripts import sync_y8 as y8


def sample_html(plays="642", rating="8.6", likes="6", title="Galalaxy", duplicate=False):
    part = f"""
      <div class="game-info">
        <div class="rating"><div class="rating__img"></div><div class="rating__number">
          {rating}
        </div></div>
        <span class="sub-infos sub-infos--white">{plays} play times</span>
      </div>
    """
    return f"""<!DOCTYPE html><html><head><title>{title} - Play Now on Y8.com</title>
      </head><body><p>10000 play times from unrelated games</p>{part}
      {part if duplicate else ""}
      <div class="game-info-container__right"><div class="voting-container">
        <div id="voting-button-yes" class="button">
          <span class="votes-count">{likes}</span>
          <span class="control-hint">Like</span>
        </div>
        <div id="voting-button-no"><span class="votes-count">987</span>
          <span class="control-hint">Dislike</span></div>
      </div></div><h1 class="block-title">{title}</h1></body></html>"""


class Y8SyncTests(unittest.TestCase):
    def fresh(self):
        return {"schemaVersion": 1, "updatedAt": None, "games": {"galalaxy": []}}

    def metrics(self, _slug, _title):
        return {"plays": 642, "rating": 8.6, "likes": 6}

    def now(self):
        return datetime(2026, 10, 11, 9, 0, tzinfo=timezone.utc)

    def test_realistic_y8_dom_and_repeated_mobile_markup(self):
        self.assertEqual(y8.parse_metrics(sample_html(duplicate=True)),
                         {"plays": 642, "rating": 8.6, "likes": 6})

    def test_number_groupings_are_exact(self):
        for display in ("1,234", "1.234", "1 234", "1\u202f234"):
            with self.subTest(display=display):
                self.assertEqual(y8.parse_metrics(sample_html(plays=display))["plays"], 1234)
        self.assertEqual(y8.parse_metrics(sample_html(plays="12345"))["plays"], 12345)

    def test_rounded_number_is_not_invented(self):
        with self.assertRaises(y8.MetricsError):
            y8.parse_metrics(sample_html(plays="1.2K"))
        with self.assertRaises(y8.MetricsError):
            y8.parse_metrics(sample_html(plays="1.2"))

    def test_rating_uses_ten_point_y8_scale(self):
        with self.assertRaises(y8.MetricsError):
            y8.parse_metrics(sample_html(rating="12.0"))
        with self.assertRaises(y8.MetricsError):
            y8.parse_metrics(sample_html(rating="not rated"))
        self.assertEqual(y8.parse_metrics(sample_html(rating="8,6"))["rating"], 8.6)

    def test_missing_and_conflicting_plays_rejected(self):
        with self.assertRaises(y8.MetricsError):
            y8.parse_metrics(sample_html(plays="unknown"))
        html = sample_html() + '<span class="sub-infos">600 play times</span>'
        with self.assertRaises(y8.MetricsError):
            y8.parse_metrics(html)

    def test_wrong_title_rejected(self):
        with self.assertRaises(y8.MetricsError):
            y8.parse_metrics(sample_html(title="Different Game"))

    def test_missing_likes_are_unknown_not_zero(self):
        html = sample_html().replace('<span class="votes-count">6</span>', "")
        result = y8.parse_metrics(html)
        self.assertIsNone(result["likes"])

    def test_unrelated_dislikes_are_not_mistaken_for_likes(self):
        result = y8.parse_metrics(sample_html(likes="0"))
        self.assertEqual(result["likes"], 0)

    def test_same_day_does_not_duplicate(self):
        archive = self.fresh()
        self.assertEqual(y8.collect(archive, self.now(), self.metrics), (1, 0, True))
        self.assertEqual(y8.collect(archive, self.now(), self.metrics), (1, 0, False))
        self.assertEqual(len(archive["games"]["galalaxy"]), 1)

    def test_later_same_day_value_replaces_old_one(self):
        archive = self.fresh()
        y8.collect(archive, self.now(), self.metrics)
        reader = lambda slug, title: {"plays": 643, "rating": 8.7, "likes": 6}
        self.assertEqual(y8.collect(archive, self.now(), reader), (1, 0, True))
        self.assertEqual(archive["games"]["galalaxy"][0]["plays"], 643)

    def test_counter_decrease_is_rejected(self):
        archive = self.fresh()
        archive["games"]["galalaxy"].append({"date": "2026-10-10", "plays": 1000, "rating": 8.6})
        self.assertEqual(y8.collect(archive, self.now(), self.metrics), (0, 1, False))
        self.assertEqual(len(archive["games"]["galalaxy"]), 1)

    def test_failure_does_not_add_zero(self):
        archive = self.fresh()
        def broken(slug, title):
            raise y8.MetricsError("No page stats")
        self.assertEqual(y8.collect(archive, self.now(), broken), (0, 1, False))
        self.assertFalse(archive["games"]["galalaxy"])

    def test_berlin_day_boundary(self):
        archive = self.fresh()
        time = datetime(2026, 10, 10, 23, 30, tzinfo=timezone.utc)
        y8.collect(archive, time, self.metrics)
        self.assertEqual(archive["games"]["galalaxy"][0]["date"], "2026-10-11")

    def test_archive_rejects_duplicate_dates(self):
        archive = self.fresh()
        archive["games"]["galalaxy"] = [{"date": "2026-10-11", "plays": 10, "rating": 8.6},
                                        {"date": "2026-10-11", "plays": 11, "rating": 8.6}]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "archive.json"
            path.write_text(json.dumps(archive), encoding="utf-8")
            with self.assertRaises(y8.MetricsError):
                y8.load_archive(path)


if __name__ == "__main__":
    unittest.main()
