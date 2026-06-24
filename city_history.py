import json
import os
from datetime import date

_HISTORY_PATH = os.path.join(os.path.dirname(__file__), "city_history.json")


def _load() -> dict:
    if not os.path.exists(_HISTORY_PATH):
        return {}
    try:
        with open(_HISTORY_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def save_history(city_counts: dict) -> None:
    history = _load()
    today = date.today().isoformat()
    history[today] = city_counts
    # Keep last 8 weeks of history
    for old in sorted(history.keys())[:-8]:
        del history[old]
    with open(_HISTORY_PATH, "w") as f:
        json.dump(history, f)


def get_hot_cities(current_counts: dict) -> list:
    """Return cities with 2x+ more events than the previous recorded run."""
    history = _load()
    if not history:
        return []
    prev = history[sorted(history.keys())[-1]]
    hot = []
    for city, count in current_counts.items():
        prev_count = prev.get(city, 0)
        if prev_count > 0 and count >= prev_count * 2 and count >= 3:
            hot.append({
                "city": city,
                "current": count,
                "previous": prev_count,
                "multiplier": round(count / prev_count, 1),
            })
    return sorted(hot, key=lambda x: x["multiplier"], reverse=True)
