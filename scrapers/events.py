import re
import time
import requests
from datetime import datetime, date
from bs4 import BeautifulSoup
from dateutil import parser as dateutil_parser

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}


def _get_cities_for_run() -> list[str]:
    week_number = datetime.utcnow().isocalendar()[1]
    start_index = (week_number * config.CITIES_PER_RUN) % len(config.CITIES)
    cities = []
    for i in range(config.CITIES_PER_RUN):
        cities.append(config.CITIES[(start_index + i) % len(config.CITIES)])
    return cities


_DATE_PATTERN = re.compile(
    r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2},?\s+\d{4}',
    re.IGNORECASE,
)


def _parse_date(date_str: str):
    if not date_str:
        return None
    date_str = date_str.strip()
    try:
        return dateutil_parser.parse(date_str, fuzzy=True).date()
    except Exception:
        return None


def _extract_date_from_card(card) -> str | None:
    # 1. <time datetime="...">
    time_tag = card.select_one("time[datetime]")
    if time_tag:
        val = time_tag.get("datetime", "").strip()
        if val:
            return val

    # 2. Any element whose class contains "date" or "time"
    for tag in card.select("[class*='date'], [class*='time']"):
        val = tag.get("datetime") or tag.get_text(strip=True)
        if val:
            return val

    # 3. Meta tags inside the card fragment
    for meta in card.select("meta[content]"):
        name = (meta.get("name") or meta.get("property") or "").lower()
        if "date" in name or "time" in name:
            val = meta.get("content", "").strip()
            if val:
                return val

    # 4. Regex scan of the raw card HTML
    match = _DATE_PATTERN.search(card.get_text(" "))
    if match:
        return match.group(0)

    return None


def _scrape_allevents(city: str, keyword: str) -> list[dict]:
    city_slug = city.lower().replace(" ", "-")
    url = f"https://allevents.in/{city_slug}/{keyword}"
    events = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return events
        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.select("li.item") or soup.select("div.event-item") or soup.select("[class*='event-card']")
        for card in cards:
            name_tag = card.select_one("h2, h3, .event-title, [class*='title']")
            link_tag = card.select_one("a[href]")
            desc_tag = card.select_one("p, [class*='desc']")
            org_tag = card.select_one("[class*='organizer'], [class*='org']")

            name = name_tag.get_text(strip=True) if name_tag else None
            event_url = link_tag["href"] if link_tag else None
            if event_url and not event_url.startswith("http"):
                event_url = "https://allevents.in" + event_url
            raw_date = _extract_date_from_card(card)
            description = desc_tag.get_text(strip=True)[:400] if desc_tag else ""
            organizer = org_tag.get_text(strip=True) if org_tag else ""

            if name and event_url:
                events.append({
                    "source": "allevents",
                    "city": city,
                    "name": name,
                    "description": description,
                    "start_date": raw_date,
                    "url": event_url,
                    "organizer": organizer,
                    "attendee_capacity": 0,
                })
    except Exception as e:
        print(f"[WARN] allevents scrape failed for {city}/{keyword}: {e}")
    return events


def _scrape_luma(city: str, keyword: str) -> list[dict]:
    query = f"{keyword}+{city}".replace(" ", "+")
    url = f"https://lu.ma/search?q={query}"
    events = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return events
        soup = BeautifulSoup(resp.text, "html.parser")
        cards = (
            soup.select("a[href*='/event/']")
            or soup.select("[class*='event-card']")
            or soup.select("[class*='EventCard']")
        )
        for card in cards:
            name_tag = card.select_one("h2, h3, [class*='title'], [class*='name']")
            link_tag = card if card.name == "a" else card.select_one("a[href]")
            date_tag = card.select_one("time, [class*='date'], [class*='time']")
            desc_tag = card.select_one("p, [class*='desc']")
            org_tag = card.select_one("[class*='host'], [class*='organizer']")

            name = name_tag.get_text(strip=True) if name_tag else card.get_text(strip=True)[:80]
            event_url = link_tag["href"] if link_tag and link_tag.get("href") else None
            if event_url and not event_url.startswith("http"):
                event_url = "https://lu.ma" + event_url
            raw_date = None
            if date_tag:
                raw_date = date_tag.get("datetime") or date_tag.get_text(strip=True)
            description = desc_tag.get_text(strip=True)[:400] if desc_tag else ""
            organizer = org_tag.get_text(strip=True) if org_tag else ""

            if name and event_url:
                events.append({
                    "source": "luma",
                    "city": city,
                    "name": name,
                    "description": description,
                    "start_date": raw_date,
                    "url": event_url,
                    "organizer": organizer,
                    "attendee_capacity": 0,
                })
    except Exception as e:
        print(f"[WARN] luma scrape failed for {city}/{keyword}: {e}")
    return events


def _scrape_ticketmaster(city: str, keyword: str) -> list[dict]:
    api_key = os.environ.get("TICKETMASTER_API_KEY", "").strip()
    if not api_key:
        return []

    today = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    events = []
    try:
        resp = requests.get(
            "https://app.ticketmaster.com/discovery/v2/events.json",
            params={
                "apikey": api_key,
                "keyword": keyword,
                "city": city,
                "countryCode": "US",
                "startDateTime": today,
                "size": 20,
                "sort": "date,asc",
            },
            timeout=15,
        )
        if resp.status_code == 429:
            print("[WARN] Ticketmaster daily limit reached — skipping for this run.")
            return events
        if resp.status_code != 200:
            return events

        items = resp.json().get("_embedded", {}).get("events", [])
        for item in items:
            name = item.get("name", "")
            event_url = item.get("url", "")
            start_date = item.get("dates", {}).get("start", {}).get("localDate")

            venues = item.get("_embedded", {}).get("venues", [{}])
            city_name = venues[0].get("city", {}).get("name", city) if venues else city

            classifications = item.get("classifications", [])
            segment = classifications[0].get("segment", {}).get("name", "") if classifications else ""
            genre = classifications[0].get("genre", {}).get("name", "") if classifications else ""
            category_str = " - ".join(filter(None, [segment, genre]))

            info = item.get("info") or item.get("pleaseNote") or ""
            price_ranges = item.get("priceRanges", [])
            price_note = f" Tickets from ${price_ranges[0].get('min', 0):.0f}." if price_ranges else ""
            description = f"{category_str}. {info}{price_note}".strip(". ")

            if name and event_url:
                events.append({
                    "source": "ticketmaster",
                    "city": city_name,
                    "name": name,
                    "description": description[:400],
                    "start_date": start_date,
                    "url": event_url,
                    "organizer": "",
                    "attendee_capacity": 0,
                })
    except Exception as e:
        print(f"[WARN] ticketmaster scrape failed for {city}/{keyword}: {e}")
    return events


def scrape_events(cities: list[str] = None, keywords: list[str] = None) -> list[dict]:
    run_cities = cities or _get_cities_for_run()
    run_keywords = keywords or config.KEYWORDS
    print(f"[INFO] Scraping cities this run: {', '.join(run_cities)}")

    has_ticketmaster = bool(os.environ.get("TICKETMASTER_API_KEY", "").strip())
    if has_ticketmaster:
        print("[INFO] Ticketmaster API key found — including Ticketmaster results.")

    all_events = []
    for city in run_cities:
        for keyword in run_keywords:
            all_events.extend(_scrape_allevents(city, keyword))
            time.sleep(1)
            all_events.extend(_scrape_luma(city, keyword))
            time.sleep(1)
            if has_ticketmaster:
                all_events.extend(_scrape_ticketmaster(city, keyword))
                time.sleep(0.5)

    print(f"[INFO] Scraped {len(all_events)} events.")

    seen_urls = set()
    deduped = []
    for ev in all_events:
        url = ev.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            deduped.append(ev)
    print(f"[INFO] After dedup: {len(deduped)}.")

    today = date.today()
    filtered = []
    for ev in deduped:
        raw = ev.get("start_date")
        parsed = _parse_date(str(raw)) if raw else None
        if parsed is None:
            ev["start_date"] = None
            filtered.append(ev)
        elif parsed >= today:
            ev["start_date"] = parsed.isoformat()
            filtered.append(ev)

    print(f"[INFO] After date filter: {len(filtered)}.")
    return filtered
