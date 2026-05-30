import csv
import io
import json
import os
import sys
from datetime import date

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrapers.events import scrape_events
from scoring.event_scorer import score_event
from scoring.city_scorer import score_cities
from config import MIN_SCORE_THRESHOLD, TOP_N_EVENTS, PROFILE_PATH, save_profile, load_profile

st.set_page_config(
    page_title="Growth Radar",
    page_icon="📡",
    layout="centered",
)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div style="background:#1d4ed8;padding:32px 24px;border-radius:10px;text-align:center;margin-bottom:8px;">
      <h1 style="color:#ffffff;margin:0;letter-spacing:2px;font-size:28px;">
        Growth Radar
      </h1>
      <p style="color:#bfdbfe;margin:10px 0 4px;font-size:17px;font-weight:600;">
        AI-powered event intelligence for any community, anywhere
      </p>
      <p style="color:#93c5fd;margin:0;font-size:14px;">
        Define your audience. Find where they gather. Show up and grow.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()

# ── How it works ──────────────────────────────────────────────────────────────
with st.expander("How it works"):
    st.markdown(
        """
**Step 1** — Get a free Anthropic API key at [console.anthropic.com](https://console.anthropic.com) (add $5 credit — lasts ~10 runs)

**Step 2** — Enter your key, describe your community, add your keywords, select your cities, and click **Run**

**Step 3** — View your results on screen and download a CSV report

> **Your API key is never stored.** It is used only for your current session and discarded when you close this page.
        """
    )

# ── API Key ───────────────────────────────────────────────────────────────────
st.subheader("API Key")
anthropic_key = st.text_input(
    "Anthropic API Key",
    type="password",
    placeholder="sk-ant-...",
    help="Get yours at console.anthropic.com",
)
st.caption("→ Get your key at [console.anthropic.com](https://console.anthropic.com)")

# ── Community Profile ─────────────────────────────────────────────────────────
st.subheader("Your Community")
st.caption("Define who you are trying to reach. This shapes how every event is scored.")

saved_profile = load_profile()

with st.expander("⚡ Quick setup — paste your website and we'll fill this in for you (optional)"):
    website_url = st.text_input(
        "Your website URL",
        placeholder="e.g. https://yourwebsite.com",
        key="website_url_input",
    )
    if st.button("Auto-fill my profile", key="autofill_btn"):
        if not website_url.strip():
            st.warning("Please enter a URL first.")
        elif not anthropic_key or not anthropic_key.startswith("sk-ant-"):
            st.warning("Please enter your Anthropic API key above first.")
        else:
            with st.spinner("Reading your website and building your profile..."):
                try:
                    import requests as _requests
                    from bs4 import BeautifulSoup as _BS
                    url = website_url.strip()
                    if not url.startswith("http://") and not url.startswith("https://"):
                        url = "https://" + url
                    try:
                        resp = _requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
                    except Exception:
                        www_url = url.replace("https://", "https://www.").replace("http://", "http://www.")
                        resp = _requests.get(www_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
                    soup = _BS(resp.text, "html.parser")
                    for tag in soup(["script", "style", "nav", "footer", "header"]):
                        tag.decompose()
                    page_text = soup.get_text(separator=" ", strip=True)[:3000]

                    import anthropic as _anth
                    _ac = _anth.Anthropic(api_key=anthropic_key)
                    extract_prompt = f"""Read this website content and extract profile information for a community event radar tool.

Website content:
{page_text}

Return ONLY a valid JSON object with these exact keys:
{{
  "community": "one sentence describing who this person/company serves and what they do",
  "keywords": ["5 to 8 comma-separated keywords their community searches for, hyphenated, lowercase"],
  "cities": ["up to 5 US cities most relevant to their work"]
}}

Be specific. Use the actual language from the website. If cities are not mentioned, suggest the top 3 US cities most relevant to their industry."""

                    resp2 = _ac.messages.create(
                        model="claude-sonnet-4-6",
                        max_tokens=500,
                        messages=[{"role": "user", "content": extract_prompt}],
                    )
                    import json as _json
                    import re as _re
                    raw = resp2.content[0].text.strip()
                    raw = _re.sub(r'```json\s*', '', raw)
                    raw = _re.sub(r'```\s*', '', raw)
                    extracted = _json.loads(raw)
                    st.session_state["autofill_community"] = extracted.get("community", "")
                    st.session_state["autofill_keywords"] = ", ".join(extracted.get("keywords", []))
                    st.session_state["autofill_cities"] = set(extracted.get("cities", []))
                    st.success("Profile auto-filled. Review and edit below before running.")
                except Exception as ex:
                    st.error(f"Could not read that URL: {ex}. Try pasting your bio manually instead.")

community_description = st.text_area(
    "Describe your target community",
    value=st.session_state.get("autofill_community", saved_profile.get("community", "")),
    placeholder="e.g. Indie game developers who attend conventions and compete in game jams globally",
    help="Describe your audience precisely. The more specific you are, the better Claude scores events for them.",
    height=100,
)

keywords_raw = st.text_input(
    "Keywords (comma-separated)",
    value=st.session_state.get("autofill_keywords", ", ".join(saved_profile.get("keywords", []))),
    placeholder="e.g. indie-game, game-jam, gaming-convention, esports, pixel-art",
    help="Use terms your community searches for and organizes around. Separate with commas.",
)

# ── City selector ─────────────────────────────────────────────────────────────
st.subheader("Select Your Cities")
st.caption("Choose up to 7 cities to scan this run. You can change these each time you run.")

ALL_CITIES = [
    "Atlanta", "Austin", "Baltimore", "Boston", "Charlotte",
    "Chicago", "Columbus", "Dallas", "Denver", "Detroit",
    "El Paso", "Fort Worth", "Houston", "Indianapolis", "Jacksonville",
    "Kansas City", "Las Vegas", "Los Angeles", "Louisville", "Memphis",
    "Miami", "Milwaukee", "Minneapolis", "Nashville", "New Orleans",
    "New York", "Oakland", "Oklahoma City", "Orlando", "Philadelphia",
    "Phoenix", "Pittsburgh", "Portland", "Raleigh", "Richmond",
    "Sacramento", "San Antonio", "San Diego", "San Francisco", "San Jose",
    "Seattle", "St. Louis", "Tampa", "Tucson", "Virginia Beach",
    "Washington DC",
]

saved_cities = st.session_state.get("autofill_cities", set(saved_profile.get("cities", [])))

selected_cities = []
cols = st.columns(4)
for i, city in enumerate(ALL_CITIES):
    with cols[i % 4]:
        if st.checkbox(city, value=(city in saved_cities), key=f"city_{city}"):
            selected_cities.append(city)

st.caption("Don't see your city? Add it below.")
custom_city_raw = st.text_input(
    "Add a city",
    placeholder="e.g. Baton Rouge, Fresno, Hartford",
    help="Separate multiple cities with commas",
)
if custom_city_raw.strip():
    custom_cities = [c.strip().title() for c in custom_city_raw.split(",") if c.strip()]
    for c in custom_cities:
        if c not in selected_cities:
            selected_cities.append(c)

too_many = len(selected_cities) > 7
if too_many:
    st.warning(f"You selected {len(selected_cities)} cities. Please uncheck some — max 7 per run.")

# ── Run button ────────────────────────────────────────────────────────────────
st.write("")
run_button = st.button(
    "RUN THE RADAR",
    type="primary",
    use_container_width=True,
    disabled=too_many,
)


# ── CSV generator ─────────────────────────────────────────────────────────────
def generate_csv(events: list[dict]) -> bytes:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Event Name", "City", "Date", "Score", "Action", "Why", "URL",
        "Organizer Contact", "Status", "Reached Out (Y/N)", "Meeting Booked (Y/N)",
        "Attended (Y/N)", "Cost ($)", "Leads Generated", "Worth Repeating (Y/N)", "Notes"
    ])
    for e in events:
        writer.writerow([
            e.get("name", ""),
            e.get("city", ""),
            e.get("start_date", "TBD"),
            e.get("opportunity_score", ""),
            e.get("recommended_action", ""),
            e.get("action_reason", ""),
            e.get("url", ""),
            e.get("organizer", ""),
            "", "", "", "", "", "", "", ""
        ])
    return output.getvalue().encode("utf-8")


# ── Validation + execution ────────────────────────────────────────────────────
if run_button:
    if not anthropic_key or not anthropic_key.startswith("sk-ant-"):
        st.error("Please enter a valid Anthropic API key starting with sk-ant-")
        st.stop()

    if not community_description.strip():
        st.error("Please describe your target community")
        st.stop()

    if not keywords_raw.strip():
        st.error("Please enter at least one keyword")
        st.stop()

    if not selected_cities:
        st.error("Please select at least one city")
        st.stop()

    # Parse keywords
    keywords = [k.strip().lower().replace(" ", "-") for k in keywords_raw.split(",") if k.strip()]

    # Save profile for next visit
    save_profile({
        "community": community_description.strip(),
        "keywords": keywords,
        "cities": selected_cities,
    })

    # Set env vars so scoring modules pick them up
    os.environ["ANTHROPIC_API_KEY"] = anthropic_key

    # Reload config with new profile values
    import config
    config.COMMUNITY = community_description.strip()
    config.KEYWORDS = keywords
    config.CITIES = selected_cities

    with st.status("Running the Radar...", expanded=True) as status:
        st.write("Scraping events across your selected cities...")
        events = scrape_events(cities=selected_cities)
        st.write(f"Found {len(events)} events. Filtering past events...")

        if not events:
            st.error("No events found for these cities and keywords. Try different keywords or cities.")
            st.stop()

        scored = []
        failed = 0
        last_error = ""
        progress = st.progress(0)
        sample = events[:150]
        st.write(f"Scoring up to {len(sample)} events with Claude AI. This takes {len(sample)//20} to {len(sample)//10} minutes. Please keep this tab open...")

        for i, event in enumerate(sample):
            try:
                result = score_event(event)
                if "error" in result:
                    failed += 1
                    last_error = result.get("error", "")
                elif result.get("opportunity_score", 0) > 3:
                    scored.append({**event, **result})
            except Exception as ex:
                failed += 1
                last_error = str(ex)
            progress.progress((i + 1) / len(sample))

        st.write(f"Scored {len(sample)} events: {len(scored)} passed, {failed} failed")
        if last_error:
            st.error(f"Scoring error: {last_error}")
        if not scored:
            st.stop()

        st.write("Ranking top opportunities...")
        scored.sort(key=lambda x: x.get("start_date") or "9999")
        top_events = scored[:TOP_N_EVENTS]

        st.write("Scoring cities...")
        city_scores = score_cities(top_events)

        status.update(label="Done!", state="complete")

    st.session_state["top_events"] = top_events
    st.session_state["city_scores"] = city_scores
    st.session_state["community_description"] = community_description

# ── Results table ─────────────────────────────────────────────────────────
top_events = st.session_state.get("top_events", [])
city_scores = st.session_state.get("city_scores", [])
community_description = st.session_state.get("community_description", community_description)

if top_events:
    st.markdown("### Your Top Events — Plan Ahead")

    header_cols = st.columns([3, 1.5, 1.2, 1, 1.8, 2, 2])
    for col, label in zip(header_cols, ["Event", "City", "Date", "Score", "Action", "Why", ""]):
        col.markdown(f"**{label}**")

    st.divider()

    for e in top_events:
        name_ev = e.get("name", "Untitled")
        url = e.get("url", "")
        city = e.get("city", "")
        start_date = e.get("start_date") or "TBD"
        score = e.get("opportunity_score", 0)
        action = (e.get("recommended_action") or "").replace("_", " ").title()
        why = e.get("action_reason", "")

        if score >= 9:
            score_md = f"**:red[{score}/10]**"
        elif score >= 7:
            score_md = f"**:orange[{score}/10]**"
        else:
            score_md = f"{score}/10"

        event_key = f"outreach_{url or name_ev}"

        row = st.columns([3, 1.5, 1.2, 1, 1.8, 2, 2])
        row[0].markdown(f"[{name_ev}]({url})" if url else name_ev)
        row[1].write(city)
        row[2].write(start_date)
        row[3].markdown(score_md)
        row[4].write(action)
        row[5].write(why)
        if row[6].button("Email", key=f"btn_{event_key}"):
            st.session_state[f"show_{event_key}"] = not st.session_state.get(f"show_{event_key}", False)

        if st.session_state.get(f"show_{event_key}"):
            if not st.session_state.get(f"email_{event_key}"):
                with st.spinner("Writing outreach email..."):
                    import anthropic as _anth
                    _client = _anth.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
                    outreach_prompt = f"""Write a short, warm, first outreach email from a founder to an event organizer.

Founder's community: {community_description}
Event name: {name_ev}
Event city: {city}
Event date: {start_date}
Organizer: {e.get('organizer', 'the organizing team')}
Why this event matters to them: {why}

Write a subject line and email body. Keep it under 150 words. Sound human, not corporate. The goal is to start a conversation about sponsoring, tabling, or partnering at this event. Do not use em dashes.

Format the output as plain text only. Start with "Subject: " on the first line, then a blank line, then the email body. No markdown, no asterisks, no bold formatting."""

                    try:
                        resp = _client.messages.create(
                            model="claude-sonnet-4-6",
                            max_tokens=400,
                            messages=[{"role": "user", "content": outreach_prompt}],
                        )
                        st.session_state[f"email_{event_key}"] = resp.content[0].text.strip()
                    except Exception as ex:
                        st.session_state[f"email_{event_key}"] = f"Error: {ex}"

            with st.expander("✉ Outreach Email", expanded=True):
                st.text_area(
                    "Copy this email",
                    value=st.session_state.get(f"email_{event_key}", ""),
                    height=220,
                    key=f"ta_{event_key}",
                )

    st.divider()
    today_str = date.today().strftime("%Y-%m-%d")
    csv_bytes = generate_csv(top_events)
    st.download_button(
        label="Download Report (CSV — opens in Excel)",
        data=csv_bytes,
        file_name=f"growth-radar-{today_str}.csv",
        mime="text/csv",
        use_container_width=True,
    )

# ── GitHub Actions Sync ───────────────────────────────────────────────────────
st.divider()
with st.expander("⚙️ Sync your profile to the weekly email automation (GitHub Actions)"):
    st.markdown("""
**Want your weekly email to use your current community profile?**

Every time you update your community, keywords, or cities — copy the JSON below and update your GitHub secret.

**Steps:**
1. Copy the JSON below
2. Go to your GitHub repo → **Settings → Secrets and variables → Actions**
3. Find `RADAR_PROFILE` and click **Update** (or **New secret** if first time)
4. Paste the JSON as the value and save
5. Your next automated run will use this profile
""")
    import json as _json
    current_profile = {
        "community": community_description if community_description else saved_profile.get("community", ""),
        "keywords": [k.strip() for k in keywords_raw.split(",") if k.strip()] if keywords_raw else saved_profile.get("keywords", []),
        "cities": selected_cities if selected_cities else saved_profile.get("cities", []),
    }
    st.text_area(
        "Copy this and paste it as your RADAR_PROFILE secret on GitHub",
        value=_json.dumps(current_profile, indent=2),
        height=200,
        key="profile_json_display",
    )

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "Growth Radar is free and open source. "
    "Built by Ogbonnaya Isaac Stephen (Zicky). "
    "[github.com/ogbonnayastephen/growth-radar](https://github.com/ogbonnayastephen/growth-radar)"
)
