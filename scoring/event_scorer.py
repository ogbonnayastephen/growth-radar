import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import anthropic

CLIENT = anthropic.Anthropic()
MODEL = "claude-sonnet-4-20250514"

SYSTEM_PROMPT = """You are a growth intelligence analyst for The Community Growth Radar, \
a free tool that helps Black business owners find events where they can grow, partner, and connect. \
Your target audience is Black business owners and entrepreneurs in the United States. \
Score each event for its value to this audience. Return ONLY valid JSON, no markdown, no explanation.

High-value criteria:
- Events with vendor/expo floors or sponsorship tiers score highest
- Events run by HBCU networks, Urban League, NAACP, Black chambers score high
- Government procurement or certification events score highest
- Events during Black History Month, Juneteenth, HBCU homecoming score high
- Business networking events with 100+ expected business owners score high
- Cultural celebrations where vendors/sponsors have booths score high

Return JSON:
{
  "opportunity_score": <1-10>,
  "estimated_black_business_attendance": <int>,
  "event_category": "<cultural_festival|business_expo|professional_networking|government_program|hbcu_event|religious|entertainment|other>",
  "business_value_fit": "<low|medium|high>",
  "recommended_action": "<attend_and_table|sponsor_booth|partner_with_organizer|send_ambassador|vendor_booth|monitor|skip>",
  "action_reason": "<one sentence, specific>",
  "organizer_partnership_potential": "<low|medium|high>",
  "alert_priority": "<urgent|this_week|backlog>"
}"""

_FAILURE = {"opportunity_score": 0, "alert_priority": "backlog", "error": "failed"}


def parse_json_response(text: str) -> dict:
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    text = text.strip()
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return json.loads(match.group())
    return json.loads(text)


def _call_claude(event: dict) -> dict:
    user_msg = (
        f"Event Name: {event.get('name', 'Unknown')}\n"
        f"City: {event.get('city', 'Unknown')}\n"
        f"Organizer: {event.get('organizer', 'Unknown')}\n"
        f"Date: {event.get('start_date', 'Unknown')}\n"
        f"Description: {event.get('description', '')}\n"
        f"URL: {event.get('url', '')}"
    )
    response = CLIENT.messages.create(
        model=MODEL,
        max_tokens=500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )
    text = response.content[0].text.strip()
    return parse_json_response(text)


def score_event(event: dict) -> dict:
    try:
        result = _call_claude(event)
        time.sleep(1.5)
        return result
    except Exception as e:
        print(f"[WARN] score_event failed for '{event.get('name')}': {e}")
        return dict(_FAILURE)


def score_events_batch(events: list[dict]) -> list[dict]:
    results = [None] * len(events)
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_to_index = {executor.submit(score_event, ev): i for i, ev in enumerate(events)}
        for future in as_completed(future_to_index):
            idx = future_to_index[future]
            try:
                results[idx] = future.result()
            except Exception:
                results[idx] = dict(_FAILURE)
    return results
