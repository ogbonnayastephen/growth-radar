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


# ── PDF generator ─────────────────────────────────────────────────────────────
def generate_pdf(top_events: list[dict], total_scanned: int,
                 name: str, email: str) -> bytes:
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    today_str = date.today().strftime("%B %d, %Y")
    recipient = name.strip() or email.strip() or "Community Growth Radar User"

    # Header block
    pdf.set_fill_color(26, 92, 56)
    pdf.rect(0, 0, 210, 38, "F")
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_y(8)
    pdf.cell(0, 10, "COMMUNITY GROWTH RADAR", ln=True, align="C")
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 7, "Event Intelligence Report", ln=True, align="C")
    pdf.set_y(42)

    # Meta
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Generated: {today_str}", ln=True, align="C")
    pdf.cell(0, 6, f"Prepared for: {recipient}", ln=True, align="C")
    pdf.ln(3)

    # Stats bar
    pdf.set_fill_color(240, 247, 243)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(
        0, 10,
        f"  Events Scanned: {total_scanned}     Opportunities Found: {len(top_events)}",
        ln=True, fill=True,
    )
    pdf.ln(4)

    # Events
    for e in top_events:
        name_ev = e.get("name", "Untitled")
        city = e.get("city", "")
        start_date = e.get("start_date") or "TBD"
        score = e.get("opportunity_score", 0)
        action = (e.get("recommended_action") or "").replace("_", " ").title()
        why = e.get("action_reason", "")
        url = e.get("url", "")

        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(26, 92, 56)
        pdf.multi_cell(0, 7, name_ev)

        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 6, f"{city}  |  {start_date}  |  Score: {score}/10", ln=True)
        pdf.cell(0, 6, f"Recommended Action: {action}", ln=True)

        if why:
            pdf.set_font("Helvetica", "I", 10)
            pdf.multi_cell(0, 6, f"Why: {why}")

        if url:
            pdf.set_font("Helvetica", "", 9)
            short_url = url[:80] + "..." if len(url) > 80 else url
            pdf.set_text_color(26, 92, 56)
            try:
                pdf.multi_cell(0, 5, short_url)
            except Exception:
                pdf.cell(0, 5, "URL too long to display", ln=True)
            pdf.set_text_color(0, 0, 0)

        pdf.ln(2)
        pdf.set_draw_color(212, 160, 23)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(4)

    # Footer
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, "Community Growth Radar — free and open source", ln=True, align="C")
    pdf.cell(0, 5, "github.com/ogbonnayastephen/community-growth-radar", ln=True, align="C")

    return bytes(pdf.output())


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

        st.write("Scoring events with Claude AI. This takes a few minutes...")
        all_scored = []
        total_to_score = min(len(events), 200)
        progress = st.progress(0)
        for i, event in enumerate(events[:200]):
            score_data = score_event(event)
            all_scored.append({**event, **score_data})
            if total_to_score > 0:
                progress.progress((i + 1) / total_to_score)

        scored = [e for e in all_scored if e.get("opportunity_score", 0) > 3]

        if not scored:
            st.warning(
                f"Found {len(events)} events but none scored above 3. "
                "This may indicate an API key issue. "
                "Please verify your Anthropic key has credits at console.anthropic.com"
            )
            st.stop()

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

        # ── PDF download ──────────────────────────────────────────────────────
        st.divider()
        today_str = date.today().strftime("%Y-%m-%d")
        pdf_bytes = generate_pdf(top_events, len(events), business_name, report_email)
        st.download_button(
            label="Download PDF Report",
            data=pdf_bytes,
            file_name=f"community-growth-radar-{today_str}.pdf",
            mime="application/pdf",
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
