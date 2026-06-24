import json
import os
import re
import sys

import anthropic

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

MODEL = "claude-sonnet-4-6"
_CLIENT = None

def _get_client():
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    return _CLIENT


def _build_system_prompt(community=None) -> str:
    community = community or getattr(config, "COMMUNITY", "business owners and entrepreneurs")
    return f"""You are a market expansion strategist helping a founder identify which US cities have the most untapped opportunity for community outreach.

The founder's target community is: {community}

Given event intelligence for a city, output ONLY a valid JSON object — no markdown, no commentary — with these exact keys:
{{
  "city": "<string>",
  "activity_score": <1-10>,
  "opportunity_gap_score": <1-10>,
  "recommended_visit_priority": "<immediate|next_quarter|watch_list>",
  "top_3_entry_points": ["<string>", "<string>", "<string>"],
  "first_action_when_you_arrive": "<one sentence tactical first step>"
}}"""


def score_city(
    city: str,
    event_count: int,
    group_count: int,
    top_event_names: list[str],
    community: str = None,
) -> dict:
    community = community or getattr(config, "COMMUNITY", "business owners and entrepreneurs")
    prompt = (
        f"City: {city}\n"
        f"Events found: {event_count}\n"
        f"Distinct organizers found: {group_count}\n"
        f"Top event names: {json.dumps(top_event_names)}\n"
        f"Target community: {community}"
    )

    try:
        response = _get_client().messages.create(
            model=MODEL,
            max_tokens=400,
            system=_build_system_prompt(community),
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        result = json.loads(text)
        result.setdefault("city", city)
        return result
    except Exception as e:
        print(f"[WARN] score_city failed for '{city}': {e}")
        return {
            "city": city,
            "activity_score": 0,
            "opportunity_gap_score": 0,
            "recommended_visit_priority": "watch_list",
            "top_3_entry_points": [],
            "first_action_when_you_arrive": "",
        }


def score_cities(scored_events: list[dict], community: str = None) -> list[dict]:
    cities_seen = {}
    for e in scored_events:
        city = e.get("city", "")
        if city:
            if city not in cities_seen:
                cities_seen[city] = []
            cities_seen[city].append(e)

    results = []
    for city, events in cities_seen.items():
        top_names = [e.get("name", "") for e in events[:3]]
        organizer_count = len(set(
            e.get("organizer", "").strip()
            for e in events
            if e.get("organizer", "").strip()
        ))
        cs = score_city(city, len(events), organizer_count or len(events), top_names, community)
        results.append(cs)

    results.sort(key=lambda x: x.get("opportunity_gap_score", 0), reverse=True)
    return results
