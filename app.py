import csv
import io
import os
import sys
from datetime import date

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrapers.events import scrape_events
from scoring.event_scorer import score_event
from scoring.city_scorer import score_city
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
        download your report as a PDF.
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

**Step 2** — Enter your key below, select your cities, and click **Run**

**Step 3** — View your results on screen and download a PDF report

> **Your key is never stored.** It is used only for your current session and discarded when you close this page.
        """
    )

# ── Inputs ────────────────────────────────────────────────────────────────────
st.subheader("API Key")

anthropic_key = st.text_input(
    "Anthropic API Key",
    type="password",
    placeholder="sk-ant-...",
    help="Get yours at console.anthropic.com — $5 credit lasts about 10 runs",
)
st.caption("→ Get your key at [console.anthropic.com](https://console.anthropic.com)")

st.subheader("Report Details (optional)")

business_name = st.text_input(
    "Your Name or Business Name",
    placeholder="e.g. Zicky Consulting",
    help="Appears in the PDF header",
)

report_email = st.text_input(
    "Your Email Address",
    placeholder="you@email.com",
    help="Shown on the PDF as 'Report prepared for' — not used to send anything",
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


# ── CSV generator ─────────────────────────────────────────────────────────────
def generate_csv(events: list[dict]) -> bytes:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Event Name", "City", "Date", "Score", "Action", "Why", "URL"])
    for e in events:
        writer.writerow([
            e.get("name", ""),
            e.get("city", ""),
            e.get("start_date", "TBD"),
            e.get("opportunity_score", ""),
            e.get("recommended_action", ""),
            e.get("action_reason", ""),
            e.get("url", ""),
        ])
    return output.getvalue().encode("utf-8")


# ── Validation + execution ────────────────────────────────────────────────────
if run_button:
    if not anthropic_key or not anthropic_key.startswith("sk-ant-"):
        st.error("Please enter a valid Anthropic API key starting with sk-ant-")
        st.stop()

    if not selected_cities:
        st.error("Please select at least one city")
        st.stop()

    os.environ["ANTHROPIC_API_KEY"] = anthropic_key

    with st.status("Running the Radar...", expanded=True) as status:
        st.write("Scraping events across your selected cities...")
        events = scrape_events(cities=selected_cities)
        st.write(f"Found {len(events)} events. Filtering past events...")

        if not events:
            st.error("No events found for these cities. Try selecting different cities.")
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

        st.write(f"Ranking top opportunities...")
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

        status.update(label="Done!", state="complete")

    # ── Results table ─────────────────────────────────────────────────────────
    if top_events:
        st.markdown("### Your Top Events — Plan Ahead")

        header_cols = st.columns([3, 1.5, 1.2, 0.8, 1.8, 3])
        for col, label in zip(
            header_cols,
            ["Event", "City", "Date", "Score", "Action", "Why"],
        ):
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

            row = st.columns([3, 1.5, 1.2, 0.8, 1.8, 3])
            row[0].markdown(f"[{name_ev}]({url})" if url else name_ev)
            row[1].write(city)
            row[2].write(start_date)
            row[3].markdown(score_md)
            row[4].write(action)
            row[5].write(why)

        # ── CSV download ──────────────────────────────────────────────────────
        st.divider()
        today_str = date.today().strftime("%Y-%m-%d")
        csv_bytes = generate_csv(top_events)
        st.download_button(
            label="Download Report (CSV — opens in Excel)",
            data=csv_bytes,
            file_name=f"community-growth-radar-{today_str}.csv",
            mime="text/csv",
            use_container_width=True,
        )
    else:
        st.info("No high-scoring events found for the selected cities. Try adding more cities or lowering the score threshold in config.py.")

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
