import json

import anthropic

CLIENT = anthropic.Anthropic()
MODEL = "claude-sonnet-4-20250514"

SYSTEM_PROMPT = """You are a market entry analyst for The Community Growth Radar. \
Given data about events found in a city, score the city for Black business owners \
considering market activity, untapped opportunity, and ease of entry. \
Return ONLY valid JSON, no markdown, no explanation.

Return JSON:
{
  "city": "<city>",
  "activity_score": <1-10>,
  "opportunity_gap_score": <1-10>,
  "recommended_visit_priority": "<immediate|next_quarter|watch_list>",
  "top_entry_points": ["<entry 1>", "<entry 2>", "<entry 3>"],
  "first_action_when_you_arrive": "<one sentence>"
}"""


def score_city(city: str, event_count: int, high_score_count: int, top_events: list[str]) -> dict:
    top_events_str = "\n".join(f"- {e}" for e in top_events[:3]) if top_events else "None"
    user_msg = (
        f"City: {city}\n"
        f"Total events found: {event_count}\n"
        f"Events scoring above 5: {high_score_count}\n"
        f"Top events:\n{top_events_str}"
    )
    try:
        response = CLIENT.messages.create(
            model=MODEL,
            max_tokens=400,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        text = response.content[0].text.strip()
        return json.loads(text)
    except Exception as e:
        print(f"[WARN] score_city failed for {city}: {e}")
        return {
            "city": city,
            "activity_score": 0,
            "opportunity_gap_score": 0,
            "recommended_visit_priority": "watch_list",
            "top_entry_points": [],
            "first_action_when_you_arrive": "Data unavailable.",
        }


def score_cities(events: list[dict]) -> list[dict]:
    city_map: dict[str, list[dict]] = {}
    for ev in events:
        city = ev.get("city", "Unknown")
        city_map.setdefault(city, []).append(ev)

    city_scores = []
    for city, city_events in city_map.items():
        event_count = len(city_events)
        high_score_count = sum(
            1 for ev in city_events if ev.get("opportunity_score", 0) > 5
        )
        top_events = [
            ev.get("name", "")
            for ev in sorted(
                city_events, key=lambda x: x.get("opportunity_score", 0), reverse=True
            )[:3]
        ]
        score = score_city(city, event_count, high_score_count, top_events)
        city_scores.append(score)

    city_scores.sort(key=lambda x: x.get("activity_score", 0), reverse=True)
    return city_scores
