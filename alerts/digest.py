import requests
import os
import json
from datetime import date


def _score_color(score: int) -> str:
    if score >= 9:
        return "color:#CC0000;font-weight:bold;"
    if score >= 7:
        return "color:#E07000;font-weight:bold;"
    return "color:#666666;"


def _priority_badge(priority: str) -> str:
    colors = {"immediate": "#1A5C38", "next_quarter": "#D4A017", "watch_list": "#888888"}
    bg = colors.get(priority, "#888888")
    label = priority.replace("_", " ").title()
    return f'<span style="background:{bg};color:#fff;padding:2px 8px;border-radius:4px;font-size:12px;">{label}</span>'


def build_html(events: list[dict], city_scores: list[dict], total_scanned: int) -> str:
    today = date.today().strftime("%B %d, %Y")
    upcoming_count = len(events)
    cities_scored = len(city_scores)

    rows = ""
    for ev in events:
        score = ev.get("opportunity_score", 0)
        color = _score_color(score)
        name = ev.get("name", "Unknown Event")
        url = ev.get("url", "#")
        city = ev.get("city", "")
        start_date = ev.get("start_date") or "TBD"
        action = ev.get("recommended_action", "").replace("_", " ").title()
        reason = ev.get("action_reason", "")

        rows += f"""
        <tr>
          <td style="padding:10px 8px;border-bottom:1px solid #eee;">
            <a href="{url}" style="color:#1A5C38;font-weight:600;text-decoration:none;">{name}</a>
          </td>
          <td style="padding:10px 8px;border-bottom:1px solid #eee;white-space:nowrap;">{city}</td>
          <td style="padding:10px 8px;border-bottom:1px solid #eee;white-space:nowrap;">{start_date}</td>
          <td style="padding:10px 8px;border-bottom:1px solid #eee;text-align:center;">
            <span style="{color}">{score}/10</span>
          </td>
          <td style="padding:10px 8px;border-bottom:1px solid #eee;white-space:nowrap;">{action}</td>
          <td style="padding:10px 8px;border-bottom:1px solid #eee;font-size:13px;color:#444;">{reason}</td>
        </tr>"""

    city_rows = ""
    for cs in city_scores:
        city = cs.get("city", "")
        activity = cs.get("activity_score", 0)
        gap = cs.get("opportunity_gap_score", 0)
        priority = cs.get("recommended_visit_priority", "watch_list")
        first_action = cs.get("first_action_when_you_arrive", "")
        badge = _priority_badge(priority)
        city_rows += f"""
        <tr>
          <td style="padding:10px 8px;border-bottom:1px solid #eee;font-weight:600;">{city}</td>
          <td style="padding:10px 8px;border-bottom:1px solid #eee;text-align:center;">{activity}/10</td>
          <td style="padding:10px 8px;border-bottom:1px solid #eee;text-align:center;">{gap}/10</td>
          <td style="padding:10px 8px;border-bottom:1px solid #eee;">{badge}</td>
          <td style="padding:10px 8px;border-bottom:1px solid #eee;font-size:13px;color:#444;">{first_action}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Community Growth Radar</title>
</head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f5;padding:20px 0;">
    <tr><td align="center">
      <table width="680" cellpadding="0" cellspacing="0" style="max-width:680px;width:100%;background:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.1);">

        <!-- Header -->
        <tr>
          <td style="background:#1A5C38;padding:32px 40px;text-align:center;">
            <h1 style="margin:0;color:#ffffff;font-size:28px;letter-spacing:2px;text-transform:uppercase;">
              Community Growth Radar
            </h1>
            <p style="margin:8px 0 0;color:#a8d5b5;font-size:14px;">{today}</p>
          </td>
        </tr>

        <!-- Headline -->
        <tr>
          <td style="padding:32px 40px 16px;text-align:center;">
            <h2 style="margin:0;color:#D4A017;font-size:22px;">
              {upcoming_count} Upcoming Events — Plan Ahead
            </h2>
          </td>
        </tr>

        <!-- Stats bar -->
        <tr>
          <td style="padding:0 40px 24px;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td style="text-align:center;padding:16px;background:#f9f9f9;border-radius:6px;">
                  <span style="color:#1A5C38;font-size:20px;font-weight:bold;">{total_scanned}</span>
                  <span style="color:#666;font-size:13px;"> events scanned</span>
                  &nbsp;&nbsp;·&nbsp;&nbsp;
                  <span style="color:#1A5C38;font-size:20px;font-weight:bold;">{upcoming_count}</span>
                  <span style="color:#666;font-size:13px;"> upcoming</span>
                  &nbsp;&nbsp;·&nbsp;&nbsp;
                  <span style="color:#1A5C38;font-size:20px;font-weight:bold;">{cities_scored}</span>
                  <span style="color:#666;font-size:13px;"> cities scored</span>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- Events Table -->
        <tr>
          <td style="padding:0 40px 32px;">
            <h3 style="color:#1A5C38;border-bottom:2px solid #1A5C38;padding-bottom:8px;">Top Scored Events</h3>
            <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;font-size:14px;">
              <thead>
                <tr style="background:#f0f7f3;">
                  <th style="padding:10px 8px;text-align:left;color:#1A5C38;font-size:12px;text-transform:uppercase;">Event</th>
                  <th style="padding:10px 8px;text-align:left;color:#1A5C38;font-size:12px;text-transform:uppercase;">City</th>
                  <th style="padding:10px 8px;text-align:left;color:#1A5C38;font-size:12px;text-transform:uppercase;">Date</th>
                  <th style="padding:10px 8px;text-align:center;color:#1A5C38;font-size:12px;text-transform:uppercase;">Score</th>
                  <th style="padding:10px 8px;text-align:left;color:#1A5C38;font-size:12px;text-transform:uppercase;">Action</th>
                  <th style="padding:10px 8px;text-align:left;color:#1A5C38;font-size:12px;text-transform:uppercase;">Why</th>
                </tr>
              </thead>
              <tbody>
                {rows}
              </tbody>
            </table>
          </td>
        </tr>

        <!-- City Scores -->
        <tr>
          <td style="padding:0 40px 32px;">
            <h3 style="color:#1A5C38;border-bottom:2px solid #D4A017;padding-bottom:8px;">Top Cities</h3>
            <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;font-size:14px;">
              <thead>
                <tr style="background:#fffbf0;">
                  <th style="padding:10px 8px;text-align:left;color:#1A5C38;font-size:12px;text-transform:uppercase;">City</th>
                  <th style="padding:10px 8px;text-align:center;color:#1A5C38;font-size:12px;text-transform:uppercase;">Activity</th>
                  <th style="padding:10px 8px;text-align:center;color:#1A5C38;font-size:12px;text-transform:uppercase;">Gap Score</th>
                  <th style="padding:10px 8px;text-align:left;color:#1A5C38;font-size:12px;text-transform:uppercase;">Priority</th>
                  <th style="padding:10px 8px;text-align:left;color:#1A5C38;font-size:12px;text-transform:uppercase;">First Action When You Arrive</th>
                </tr>
              </thead>
              <tbody>
                {city_rows}
              </tbody>
            </table>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="background:#1A5C38;padding:20px 40px;text-align:center;">
            <p style="margin:0;color:#a8d5b5;font-size:13px;">
              Community Growth Radar · Free &amp; Open Source
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""
    return html


def send_batch_email(events: list[dict], city_scores: list[dict], total_scanned: int):
    api_key = os.getenv("RESEND_API_KEY")
    to_email = os.getenv("ALERT_EMAIL")

    if not api_key or not to_email:
        print("[ERROR] RESEND_API_KEY or ALERT_EMAIL not set")
        return

    html = build_html(events, city_scores, total_scanned)
    today_date = date.today().strftime("%Y-%m-%d")
    top_city = city_scores[0]["city"] if city_scores else "N/A"
    subject = (
        f"Community Growth Radar — {len(events)} Upcoming Events"
        f" | Top City: {top_city} | {today_date}"
    )

    response = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "from": "Community Growth Radar <onboarding@resend.dev>",
            "to": [to_email],
            "subject": subject,
            "html": html,
        },
    )

    if response.status_code in (200, 201):
        print(f"[INFO] Email sent to {to_email}")
    else:
        print(f"[ERROR] Resend failed: {response.status_code} {response.text}")
