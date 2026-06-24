import json
import os
from datetime import date, timedelta

_SEEN_PATH = os.path.join(os.path.dirname(__file__), "seen_events.json")


def _load_raw() -> dict:
    if not os.path.exists(_SEEN_PATH):
        return {}
    try:
        with open(_SEEN_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def load_seen(days: int = 14) -> set:
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    return {url for url, seen_date in _load_raw().items() if seen_date >= cutoff}


def save_seen(urls: list) -> None:
    today = date.today().isoformat()
    existing = _load_raw()
    cutoff = (date.today() - timedelta(days=60)).isoformat()
    existing = {url: d for url, d in existing.items() if d >= cutoff}
    for url in urls:
        if url:
            existing[url] = today
    with open(_SEEN_PATH, "w") as f:
        json.dump(existing, f)


def filter_new(events: list) -> tuple:
    """Remove events seen in the last 14 days. Returns (new_events, skipped_count)."""
    seen = load_seen()
    new = [e for e in events if e.get("url", "") not in seen]
    return new, len(events) - len(new)
