import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrapers.events import scrape_events
from scoring.event_scorer import score_event
from scoring.city_scorer import score_city
from alerts.digest import send_batch_email
import config
from config import MIN_SCORE_THRESHOLD, TOP_N_EVENTS

st.set_page_config(
    page_title="Community Growth Radar",
    page_icon="📡",
    layout="centered",
)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div style="background:#1A5C38;padding:32px 24px;border-radius:10px;text-align:center;margin-bottom:8px;">
      <h1 style="color:#ffffff;margin:0;letter-spacing:2px;font-size:28px;">
        Community Growth Radar
      </h1>
      <p style="color:#D4A017;margin:10px 0 4px;font-size:17px;font-weight:600;">
        Free AI-powered event intelligence for Black business owners
      </p>
      <p style="color:#a8d5b5;margin:0;font-size:14px;">
        Finds events where you can sponsor, partner, attend, and grow —
        delivered to your inbox.
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

**Step 2** — Get a free Resend API key at [resend.com](https://resend.com) (sign up with Google)

**Step 3** — Enter both keys below, select your cities, and click **Run**

**Step 4** — Check your inbox in 10–15 minutes

> **Your keys are never stored.** They are used only for your current session and discarded when you close this page.
        """
    )

# ── API Keys ──────────────────────────────────────────────────────────────────
st.subheader("API Keys")

anthropic_key = st.text_input(
    "Anthropic API Key",
    type="password",
    placeholder="sk-ant-...",
    help="Get yours at console.anthropic.com — $5 credit lasts about 10 runs",
)
st.caption("→ Get your key at [console.anthropic.com](https://console.anthropic.com)")

resend_key = st.text_input(
    "Resend API Key",
    type="password",
    placeholder="re_...",
    help="Get yours free at resend.com",
)
st.caption("→ Get your key at [resend.com](https://resend.com)")

alert_email = st.text_input(
    "Your Email Address",
    placeholder="you@email.com",
    help="Where your intelligence report will be sent",
)

# ── City selector ─────────────────────────────────────────────────────────────
st.subheader("Select Your Cities")
st.caption("Choose up to 7 cities to scan this run")

ALL_CITIES = [
    "Atlanta", "Houston", "Chicago", "New York", "Washington DC",
    "Los Angeles", "Philadelphia", "Charlotte", "Detroit", "Memphis",
    "Baltimore", "Dallas", "Miami", "Oakland", "New Orleans", "Richmond",
]
DEFAULT_CITIES = {"Atlanta", "Houston", "Baltimore", "Dallas", "Washington DC"}

selected_cities = []
cols = st.columns(3)
for i, city in enumerate(ALL_CITIES):
    with cols[i % 3]:
        if st.checkbox(city, value=(city in DEFAULT_CITIES), key=f"city_{city}"):
            selected_cities.append(city)

too_many = len(selected_cities) > 7
if too_many:
    st.warning("Please select 7 or fewer cities for best results.")

# ── Run button ────────────────────────────────────────────────────────────────
st.write("")
run_button = st.button(
    "RUN THE RADAR",
    type="primary",
    use_container_width=True,
    disabled=too_many,
)

# ── Validation + execution ────────────────────────────────────────────────────
if run_button:
    if not anthropic_key or not anthropic_key.startswith("sk-ant-"):
        st.error("Please enter a valid Anthropic API key starting with sk-ant-")
        st.stop()

    if not resend_key or not resend_key.startswith("re_"):
        st.error("Please enter a valid Resend API key starting with re_")
        st.stop()

    if not alert_email or "@" not in alert_email:
        st.error("Please enter a valid email address")
        st.stop()

    if not selected_cities:
        st.error("Please select at least one city")
        st.stop()

    # Inject keys into environment for this session
    os.environ["ANTHROPIC_API_KEY"] = anthropic_key
    os.environ["RESEND_API_KEY"] = resend_key
    os.environ["ALERT_EMAIL"] = alert_email

    # Override config with user-selected cities
    config.CITIES = selected_cities
    config.CITIES_PER_RUN = len(selected_cities)

    with st.status("Running the Radar...", expanded=True) as status:
        st.write("Scraping events across your selected cities...")
        events = scrape_events()
        st.write(f"Found {len(events)} events. Filtering past events...")

        st.write("Scoring events with Claude AI. This takes a few minutes...")
        scored = []
        total_to_score = min(len(events), 200)
        progress = st.progress(0)
        for i, event in enumerate(events[:200]):
            score = score_event(event)
            if score.get("opportunity_score", 0) > MIN_SCORE_THRESHOLD:
                scored.append({**event, **score})
            progress.progress((i + 1) / total_to_score)

        st.write(f"Scored {len(scored)} relevant events. Ranking top opportunities...")
        scored.sort(key=lambda x: x.get("start_date") or "9999")
        top_events = scored[:TOP_N_EVENTS]

        st.write("Scoring cities...")
        city_scores = []
        for city in set(e["city"] for e in top_events):
            city_events = [e for e in top_events if e["city"] == city]
            cs = score_city(
                city,
                len(city_events),
                len(city_events),
                [e["name"] for e in city_events[:3]],
            )
            city_scores.append(cs)

        st.write("Sending your report via email...")
        send_batch_email(top_events, city_scores, len(events))

        status.update(label="Done!", state="complete")

    st.success(
        f"Your report is on its way to **{alert_email}**. "
        "Check your inbox in the next few minutes. "
        "Check spam if it doesn't arrive."
    )

    # Preview top 5
    if top_events:
        st.subheader("Preview: Top 5 Events")
        preview = [
            {
                "Event Name": e.get("name", ""),
                "City": e.get("city", ""),
                "Score": e.get("opportunity_score", 0),
                "Action": (e.get("recommended_action") or "").replace("_", " ").title(),
                "Why": e.get("action_reason", ""),
            }
            for e in top_events[:5]
        ]
        st.dataframe(preview, use_container_width=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "Community Growth Radar is free and open source. "
    "Built for Black business owners by Ogbonnaya Isaac Stephen (Zicky). "
    "[github.com/ogbonnayastephen/community-growth-radar](https://github.com/ogbonnayastephen/community-growth-radar)"
)
st.caption(
    "Developer? Fork the repo and run your own instance with your own API keys. "
    "Full setup guide in the README."
)
