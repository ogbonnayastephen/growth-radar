import sys
import time
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import schedule
from dotenv import load_dotenv

load_dotenv()

import config
from config import MIN_SCORE_THRESHOLD, TOP_N_EVENTS, MAX_EVENTS_TO_SCORE, load_profile
from scrapers.events import scrape_events
from scoring.event_scorer import score_event
from scoring.city_scorer import score_cities
from alerts.digest import send_batch_email


def _load_profile_into_config():
    """
    Load audience profile into config at runtime.
    Priority order:
    1. RADAR_PROFILE environment variable (JSON string) — used by GitHub Actions
    2. radar_profile.json file — used by local runs
    3. Config defaults — fallback
    """
    profile = {}

    # Try env var first (GitHub Actions / cloud)
    radar_profile_env = os.environ.get("RADAR_PROFILE", "").strip()
    if radar_profile_env:
        try:
            import json as _json
            profile = _json.loads(radar_profile_env)
            print("[INFO] Loaded profile from RADAR_PROFILE environment variable.")
        except Exception as e:
            print(f"[WARN] Could not parse RADAR_PROFILE env var: {e}. Falling back to file.")

    # Fall back to radar_profile.json
    if not profile:
        profile = load_profile()
        if profile:
            print("[INFO] Loaded profile from radar_profile.json.")

    if not profile:
        print("[INFO] No profile found — using config defaults.")

    if profile.get("community"):
        config.COMMUNITY = profile["community"]
    if profile.get("keywords"):
        config.KEYWORDS = profile["keywords"]
    if profile.get("cities"):
        config.CITIES = profile["cities"]

    print(f"[INFO] Community: {config.COMMUNITY}")
    print(f"[INFO] Keywords: {', '.join(config.KEYWORDS[:5])}{'...' if len(config.KEYWORDS) > 5 else ''}")
    print(f"[INFO] Cities pool: {', '.join(config.CITIES)}")


def run_radar():
    print(f"\n{'='*60}")
    print(f"  Growth Radar — Run started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    _load_profile_into_config()

    # 1. Scrape
    events = scrape_events()
    raw_count = len(events)
    print(f"[INFO] Raw scraped events: {raw_count}")

    # 2. Cap before scoring
    events_to_score = events[:MAX_EVENTS_TO_SCORE]

    # 3. Score events
    print(f"[INFO] Scoring {len(events_to_score)} events with Claude...")
    scored_events = []
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_to_event = {executor.submit(score_event, ev): ev for ev in events_to_score}
        for future in as_completed(future_to_event):
            ev = future_to_event[future]
            try:
                score_data = future.result()
            except Exception:
                score_data = {"opportunity_score": 0, "alert_priority": "backlog", "error": "failed"}
            scored_events.append({**ev, **score_data})

    # 4. Filter by score threshold
    high_score_events = [e for e in scored_events if e.get("opportunity_score", 0) > MIN_SCORE_THRESHOLD]
    print(f"[INFO] Events with score > {MIN_SCORE_THRESHOLD}: {len(high_score_events)}")

    # 5. Sort by date ascending
    high_score_events.sort(key=lambda e: e.get("start_date") or "9999-99-99")

    # 6. Keep top N
    top_events = high_score_events[:TOP_N_EVENTS]
    print(f"[INFO] Top {TOP_N_EVENTS} kept: {len(top_events)}")

    # 7. Score cities
    print("[INFO] Scoring cities...")
    city_scores = score_cities(scored_events)
    print(f"[INFO] Cities scored: {len(city_scores)}")

    # 8. Send email
    if top_events:
        send_batch_email(top_events, city_scores, raw_count)
    else:
        print("[INFO] No high-score events found — skipping email.")

    # 9. Summary
    print(f"\n{'='*60}")
    print("  RUN COMPLETE")
    print(f"{'='*60}")
    print(f"  Raw scraped:     {raw_count}")
    print(f"  Score > {MIN_SCORE_THRESHOLD}:       {len(high_score_events)}")
    print(f"  Top {TOP_N_EVENTS} kept:     {len(top_events)}")
    print(f"  Cities scored:   {len(city_scores)}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    if "--once" in sys.argv:
        run_radar()
        sys.exit(0)

    schedule.every(48).hours.do(run_radar)
    schedule.every().monday.at("07:00").do(run_radar)

    run_radar()

    while True:
        schedule.run_pending()
        time.sleep(60)
