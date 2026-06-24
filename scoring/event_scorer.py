import json
import re
import time
import os

import anthropic

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

MODEL = "claude-sonnet-4-6"
_CLIENT = None

def _get_client():
    global _CLIENT
    if _CLIENT is None or not _CLIENT.api_key:
        _CLIENT = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    return _CLIENT


def _build_system_prompt(community=None, keywords=None) -> str:
    community = community or getattr(config, "COMMUNITY", "business owners and entrepreneurs")
    kws = keywords or getattr(config, "KEYWORDS", [])
    keywords_str = ", ".join(kws[:10]) if kws else "business, networking, community"
    return f"""You are a growth intelligence analyst helping a founder find events where they can grow, partner, and connect.

The founder's target community is: {community}
Keywords their community searches for: {keywords_str}

Score each event for its value to this specific audience. Return ONLY valid JSON, no markdown, no explanation.

High-value criteria:
- Events with vendor/expo floors or sponsorship tiers score highest
- Events run by established associations or chambers relevant to this community score high
- Government procurement or certification events score highest
- Large networking events with 100+ expected attendees from this community score high
- Cultural celebrations where vendors/sponsors have booths score high

Return JSON:
{{
  "opportunity_score": <1-10>,
  "estimated_target_attendance": <int>,
  "event_category": "<cultural_festival|business_expo|professional_networking|government_program|association_event|religious|entertainment|other>",
  "business_value_fit": "<low|medium|high>",
  "recommended_action": "<attend_and_table|sponsor_booth|partner_with_organizer|send_ambassador|vendor_booth|monitor|skip>",
  "action_reason": "<one sentence, specific>",
  "organizer_partnership_potential": "<low|medium|high>",
  "alert_priority": "<urgent|this_week|backlog>"
}}"""


_FAILURE = {"opportunity_score": 0, "alert_priority": "backlog", "error": "failed"}


def parse_json_response(text: str) -> dict:
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    text = text.strip()
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return json.loads(match.group())
    return json.loads(text)


def _call_claude(event: dict, community=None, keywords=None) -> dict:
    user_msg = (
        f"Event Name: {event.get('name', 'Unknown')}\n"
        f"City: {event.get('city', 'Unknown')}\n"
        f"Organizer: {event.get('organizer', 'Unknown')}\n"
        f"Date: {event.get('start_date', 'Unknown')}\n"
        f"Description: {event.get('description', '')}\n"
        f"URL: {event.get('url', '')}"
    )
    response = _get_client().messages.create(
        model=MODEL,
        max_tokens=500,
        system=_build_system_prompt(community, keywords),
        messages=[{"role": "user", "content": user_msg}],
    )
    text = response.content[0].text.strip()
    return parse_json_response(text)


def score_event(event: dict, community=None, keywords=None) -> dict:
    try:
        result = _call_claude(event, community, keywords)
        time.sleep(1.5)
        return result
    except Exception as e:
        import traceback
        print(f"[WARN] score_event failed for '{event.get('name')}': {e}")
        traceback.print_exc()
        return {"opportunity_score": 0, "alert_priority": "backlog", "error": str(e)}
