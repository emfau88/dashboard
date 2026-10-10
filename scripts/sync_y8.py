#!/usr/bin/env python3
"""Record public Y8 game-page counters once per Europe/Berlin calendar day.

Uses Python's standard library only. This reads *public page numbers*, not
private Y8 Studio analytics. Missing/contradictory data must not become zeros.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "analytics" / "y8.json"
GAMES = {"galalaxy": {"slug": "galalaxy", "title": "Galalaxy"}}
SITE = "https://www.y8.com/games/"
MAX_RESPONSE_BYTES = 2_000_000
VOID_TAGS = frozenset("area base br col embed hr img input link meta param source track wbr".split())


class MetricsError(ValueError):
    """A sample is missing required fields or appears unreliable."""


class Y8PageParser(HTMLParser):
    """Read only numbers from the game's metadata and its Like control."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.elements = []
        self.found = {"title": [], "heading": [], "plays": [], "rating": [], "likes": []}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_map = dict(attrs)
        classes = set((attrs_map.get("class") or "").split())
        in_like_button = attrs_map.get("id") == "voting-button-yes" or any(
            element["like_button"] for element in self.elements
        )
        kind = None
        if tag == "title":
            kind = "title"
        elif tag == "h1" and "block-title" in classes:
            kind = "heading"
        elif tag == "span" and "sub-infos" in classes:
            kind = "plays"
        elif tag == "div" and "rating__number" in classes:
            kind = "rating"
        elif tag == "span" and "votes-count" in classes and in_like_button:
            kind = "likes"
        element = {"tag": tag, "kind": kind, "parts": [], "like_button": in_like_button}
        if tag not in VOID_TAGS:
            self.elements.append(element)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in VOID_TAGS:
            self.handle_endtag(tag)

    def handle_data(self, data: str) -> None:
        for element in self.elements:
            if element["kind"]:
                element["parts"].append(data)

    def handle_endtag(self, tag: str) -> None:
        matching = next((i for i in range(len(self.elements)-1, -1, -1)
                         if self.elements[i]["tag"] == tag), None)
        if matching is None:
            return
        for element in self.elements[matching:]:
            if element["kind"]:
                self.found[element["kind"]].append(" ".join("".join(element["parts"]).split()))
        del self.elements[matching:]


COUNT_PATTERN = re.compile(r"(?:[0-9]+|[1-9][0-9]{0,2}(?:[., \u00a0\u202f][0-9]{3})+)\Z")
PLAY_TEXT = re.compile(r"\s*(.*?)\s+play\s+times\s*", re.IGNORECASE)


def parse_count(value: str) -> int:
    """Accept exact integers and grouped thousands, but no rounded '1.2K' counters."""
    text = value.strip()
    # Disallow odd comma/decimal formatting that might be a rounded value.
    if not (re.fullmatch(r"[0-9]+", text)
            or re.fullmatch(r"[1-9][0-9]{0,2}(?:[,. \u00a0\u202f][0-9]{3})+", text)):
        raise MetricsError(f"Unexpected number format {value!r}")
    return int(re.sub(r"[^0-9]", "", text))


def single_value(values: list, name: str):
    if not values:
        raise MetricsError(f"{name}: missing on Y8 page")
    if len(set(values)) != 1:
        raise MetricsError(f"{name}: conflicting readings {values!r}")
    return values[0]


def parse_metrics(html: str, expected_title: str = "Galalaxy") -> dict:
    parser = Y8PageParser()
    parser.feed(html)
    titles = parser.found["title"] + parser.found["heading"]
    if not any(expected_title.lower() in title.lower() for title in titles):
        raise MetricsError("Wrong page or missing expected game title")

    play_values = []
    for text in parser.found["plays"]:
        match = PLAY_TEXT.fullmatch(text)
        if match:
            play_values.append(parse_count(match.group(1)))
    plays = single_value(play_values, "play times")

    ratings = []
    for text in parser.found["rating"]:
        value = text.strip().replace(",", ".")
        try:
            rating = float(value)
        except ValueError as exc:
            raise MetricsError(f"Invalid Y8 rating {value!r}") from exc
        if not 0 <= rating <= 10:
            raise MetricsError(f"Rating outside Y8 0–10 scale: {rating}")
        ratings.append(round(rating, 2))
    rating = single_value(ratings, "rating")

    likes_values = [parse_count(text) for text in parser.found["likes"]]
    # Y8 can omit the vote count; unknown != zero.
    likes = single_value(likes_values, "likes") if likes_values else None

    return {"plays": plays, "rating": rating, "likes": likes}


def fetch_metrics(slug: str, title: str) -> dict:
    if not any(config["slug"] == slug and config["title"] == title for config in GAMES.values()):
        raise MetricsError("Unrecognised Y8 game configuration")
    url = SITE + slug
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; EmfauGameOps/1.0; +https://github.com/emfau88/dashboard)",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.8",
    })
    with urllib.request.urlopen(req, timeout=20) as response:
        if response.status != 200:
            raise MetricsError(f"HTTP {response.status}")
        location = urlsplit(response.geturl())
        if location.scheme != "https" or location.hostname != "www.y8.com" or location.path != f"/games/{slug}":
            raise MetricsError(f"Unexpected redirect to {response.geturl()}")
        if "html" not in response.headers.get("Content-Type", "").lower():
            raise MetricsError("Y8 did not return HTML")
        raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise MetricsError("Y8 page exceeded size limit")
    return parse_metrics(raw.decode("utf-8"), title)


def load_archive(path: Path = ARCHIVE) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schemaVersion") != 1 or not isinstance(data.get("games"), dict):
        raise MetricsError("Invalid Y8 archive schema")
    for game_id in GAMES:
        history = data["games"].get(game_id)
        if not isinstance(history, list):
            raise MetricsError(f"{game_id}: missing history")
        dates = [point.get("date") for point in history]
        if any(not isinstance(date, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", date)
               for date in dates) or dates != sorted(set(dates)):
            raise MetricsError(f"{game_id}: dates unsorted or duplicated")
        for point in history:
            if type(point.get("plays")) is not int or point["plays"] < 0:
                raise MetricsError(f"{game_id}: invalid play count")
            if type(point.get("rating")) not in (float, int) or not 0 <= point["rating"] <= 10:
                raise MetricsError(f"{game_id}: invalid rating")
            if point.get("likes") is not None and (type(point["likes"]) is not int or point["likes"] < 0):
                raise MetricsError(f"{game_id}: invalid likes")
    return data


def upsert_daily(history: list[dict], sample: dict) -> bool:
    previous = next((point for point in history if point["date"] == sample["date"]), None)
    if any(sample["plays"] < point["plays"] for point in history if point["date"] <= sample["date"]):
        raise MetricsError("Y8 lifetime play count decreased; keeping last verified sample")
    if previous and all(previous.get(k) == sample.get(k) for k in ("plays", "rating", "likes")):
        return False
    if previous:
        history.remove(previous)
    history.append(sample)
    history.sort(key=lambda point: point["date"])
    return True


def collect(data: dict, now: datetime, fetcher=fetch_metrics) -> tuple[int, int, bool]:
    date = now.astimezone(ZoneInfo("Europe/Berlin")).date().isoformat()
    timestamp = now.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    succeeded = failed = 0
    changed = False
    for game_id, config in GAMES.items():
        try:
            fields = fetcher(config["slug"], config["title"])
            sample = {
                "date": date, **fields,
                "source": "y8_public_page",
                "fetchedAt": timestamp,
            }
            if upsert_daily(data["games"][game_id], sample):
                changed = True
            succeeded += 1
            print(f"OK Y8 {game_id}: {fields['plays']} plays, "
                  f"rating {fields['rating']}/10, likes {fields['likes']}", flush=True)
        except (MetricsError, urllib.error.URLError, TimeoutError, OSError, UnicodeError) as exc:
            failed += 1
            print(f"WARNING Y8 {game_id}: {exc}; retaining last verified sample", file=sys.stderr)
    if changed:
        data["updatedAt"] = timestamp
    return succeeded, failed, changed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-live", action="store_true", help="Test the real page without saving")
    args = parser.parse_args()
    data = load_archive()
    successes, failures, modified = collect(data, datetime.now(timezone.utc))
    if args.check_live:
        print("Y8 live probe finished; no files written")
        return 0 if successes and not failures else 1
    if modified:
        ARCHIVE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Updated {ARCHIVE.relative_to(ROOT)}")
    else:
        print("No new Y8 snapshot")
    if failures:
        print(f"WARNING: {failures} Y8 fetch(es) failed, with no fabricated zeros", file=sys.stderr)
    return 0 if successes else 1


if __name__ == "__main__":
    raise SystemExit(main())
