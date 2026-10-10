#!/usr/bin/env python3
"""Capture public Kongregate metrics once per Berlin calendar day.

No credentials or third-party packages required. Missing/invalid replies never
become zero-valued snapshots. Historical values are never silently fabricated.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "analytics" / "kongregate.json"
GAMES = {
    "hexfront": "hexfront",
    "galalaxy": "galalaxy",
    "rooster-rage": "roosterrage-survivor",
}
BASE_URL = "https://www.kongregate.com/games/emfau/"
MAX_RESPONSE_BYTES = 100_000


class MetricsError(ValueError):
    """A response cannot be trusted as a valid Kongregate metrics sample."""


def parse_metrics(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise MetricsError("Response is not a JSON object")
    plays = payload.get("gameplays_count")
    favorites = payload.get("favorites_count")
    if type(plays) is not int or plays < 0:
        raise MetricsError("gameplays_count must be a non-negative integer")
    if type(favorites) is not int or favorites < 0:
        raise MetricsError("favorites_count must be a non-negative integer")

    raw_rating = payload.get("rating")
    if raw_rating is None or raw_rating == "":
        rating = None
    else:
        try:
            rating = float(raw_rating)
        except (ValueError, TypeError) as exc:
            raise MetricsError("rating must be numeric or absent") from exc
        if not math.isfinite(rating) or not 0 <= rating <= 5:
            raise MetricsError("rating outside the 0–5 range")
        rating = round(rating, 2)
    return {"plays": plays, "favorites": favorites, "rating": rating}


def fetch_metrics(slug: str) -> dict:
    if slug not in GAMES.values():
        raise MetricsError("Unknown configured game slug")
    req = urllib.request.Request(
        BASE_URL + slug + "/metrics.json",
        headers={"Accept": "application/json", "User-Agent": "EmfauGameOps/1.0 (daily public metrics)"},
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        if response.status != 200:
            raise MetricsError(f"HTTP {response.status}")
        if response.geturl().split("/")[2] != "www.kongregate.com":
            raise MetricsError("Unexpected redirect away from Kongregate")
        raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise MetricsError("JSON response too large")
        if "json" not in response.headers.get("Content-Type", "").lower():
            raise MetricsError("Unexpected response Content-Type")
    try:
        payload = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise MetricsError("Malformed JSON payload") from exc
    return parse_metrics(payload)


def load_archive(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schemaVersion") != 1 or not isinstance(data.get("games"), dict):
        raise MetricsError("Unsupported analytics archive schema")
    for game_id in GAMES:
        history = data["games"].get(game_id)
        if not isinstance(history, list):
            raise MetricsError(f"{game_id}: history must be a list")
        dates = [item.get("date") for item in history]
        if any(not isinstance(d, str) for d in dates) or dates != sorted(set(dates)):
            raise MetricsError(f"{game_id}: duplicate or unsorted dates")
        for item in history:
            if type(item.get("plays")) is not int or item["plays"] < 0:
                raise MetricsError(f"{game_id}: invalid stored plays")
    return data


def insert_sample(history: list[dict], sample: dict) -> bool:
    day = sample["date"]
    prior = next((item for item in history if item["date"] == day), None)
    previous = [item for item in history if item["date"] < day]
    if previous and sample["plays"] < previous[-1]["plays"]:
        raise MetricsError(f"Plays dropped below previous lifetime snapshot ({previous[-1]['plays']})")
    if prior and all(prior.get(key) == sample[key] for key in ("plays", "favorites", "rating")):
        return False
    if prior is not None:
        history.remove(prior)
    history.append(sample)
    history.sort(key=lambda item: item["date"])
    return True


def collect(data: dict, now: datetime, fetcher=fetch_metrics) -> tuple[int, int, bool]:
    day = now.astimezone(ZoneInfo("Europe/Berlin")).date().isoformat()
    fetched_at = now.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    success = failures = 0
    modified = False
    for game_id, slug in GAMES.items():
        try:
            sample = {"date": day, **fetcher(slug), "source": "kongregate_metrics", "fetchedAt": fetched_at}
            changed = insert_sample(data["games"][game_id], sample)
            if changed:
                modified = True
            success += 1
            print(f"OK {game_id}: {sample['plays']} plays; {sample['favorites']} favorites; rating {sample['rating']}")
        except (MetricsError, urllib.error.URLError, TimeoutError, ValueError) as exc:
            failures += 1
            print(f"WARNING {game_id}: {exc}; previous data retained", file=sys.stderr)
    if modified:
        data["updatedAt"] = fetched_at
    return success, failures, modified


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-live", action="store_true", help="Check feeds without updating the archive")
    args = parser.parse_args()
    data = load_archive(ARCHIVE)
    successes, failures, modified = collect(data, datetime.now(timezone.utc))
    if successes == 0 or (args.check_live and failures):
        return 1
    if args.check_live:
        print("Live probe successful; no files written")
        return 0
    if modified:
        ARCHIVE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Updated {ARCHIVE.relative_to(ROOT)}")
    else:
        print("No changes to daily metrics")
    if failures:
        print(f"WARNING: {failures} feed(s) failed. Missing days are not filled with zeros.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
