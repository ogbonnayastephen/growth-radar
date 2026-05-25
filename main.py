import sys
import time
import json
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import schedule
from dotenv import load_dotenv

load_dotenv()

from config import MIN_SCORE_THRESHOLD, TOP_N_EVENTS, MAX_EVENTS_TO_SCORE
from scrapers.events import scrape_events
from scoring.event_scorer import score_event
from scoring.city_scorer import score_cities
from alerts.digest import send_batch_email


def run_radar():
    print(f"\n{'='*60}")
    print(f"  Community Growth Radar — Run started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    # 1. Scrape
    events = scrape_events()
    raw_count = len(events)
    print(f"[INFO] Raw scraped events: {raw_count}")

    after_date_filter = raw_count  # scrape_events() already date-filters

    # 2. Cap before scoring to control API costs
    events_to_score = events[:MAX_EVENTS_TO_SCORE]

    # 3. Score events using ThreadPoolExecutor
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
            merged = {**ev, **score_data}
            scored_events.append(merged)

    # 4. Filter by score threshold
    high_score_events = [e for e in scored_events if e.get("opportunity_score", 0) > MIN_SCORE_THRESHOLD]
    print(f"[INFO] Events with score > {MIN_SCORE_THRESHOLD}: {len(high_score_events)}")

    # 5. Sort by start_date ascending (None/missing dates go last)
    def sort_key(e):
        d = e.get("start_date")
        return d if d else "9999-99-99"

    high_score_events.sort(key=sort_key)

    # 6. Keep top N
    top_events = high_score_events[:TOP_N_EVENTS]
    print(f"[INFO] Top {TOP_N_EVENTS} kept: {len(top_events)}")

    # 7. Score cities
    print("[INFO] Scoring cities...")
    city_scores = score_cities(scored_events)
    print(f"[INFO] Cities scored: {len(city_scores)}")

    # 8. Send email if we have events
    if len(top_events) > 0:
        send_batch_email(top_events, city_scores, raw_count)
    else:
        print("[INFO] No high-score events found — skipping email.")

    # 9. Summary
    upcoming = sum(1 for e in top_events if e.get("start_date"))
    print(f"\n{'='*60}")
    print("  RUN COMPLETE")
    print(f"{'='*60}")
    print(f"  Raw scraped:       {raw_count}")
    print(f"  After date filter: {after_date_filter}")
    print(f"  Score > {MIN_SCORE_THRESHOLD}:         {len(high_score_events)}")
    print(f"  Top {TOP_N_EVENTS} kept:       {len(top_events)}")
    print(f"  Cities scored:     {len(city_scores)}")
    print(f"  Upcoming events:   {upcoming}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    if "--once" in sys.argv:
        run_radar()
        sys.exit(0)

    schedule.every(48).hours.do(run_radar)
    schedule.every().monday.at("07:00").do(run_radar)

    run_radar()  # run once on startup

    while True:
        schedule.run_pending()
        time.sleep(60)
