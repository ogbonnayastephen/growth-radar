# Growth Radar

**Open-source AI event intelligence engine for small business growth — audience-aware, multi-source, fully automated.**

---

## The Problem

In-person presence at the right events — trade expos, business association conferences, cultural festivals with vendor floors, government procurement seminars, and professional networking gatherings — remains one of the highest-return growth channels available to small businesses. Research consistently shows that event-led outreach generates stronger conversion rates and longer customer relationships than digital-only acquisition, particularly for businesses serving specific community demographics.

Yet for the 33 million small businesses operating in the United States, systematic event discovery does not exist.

Event listings are fragmented across dozens of platforms. There is no intelligence layer to distinguish a regional expo with 800 target customers from a generic mixer with none. A business owner in Houston targeting Black-owned food entrepreneurs, a consultant in Chicago reaching indie software developers, or a service provider in Atlanta serving immigrant-owned businesses — none of them have access to a tool that understands their specific audience and evaluates events accordingly.

The consequence is a structural disadvantage: small businesses either attend events blindly, wasting scarce marketing budgets on low-yield gatherings, or they disengage from in-person growth entirely. Enterprise competitors with dedicated marketing teams do not face this constraint. The gap between large and small business event strategy is not a resource gap — it is an intelligence gap.

**Growth Radar was designed to close that gap.**

---

## What Growth Radar Does

Growth Radar is an open-source AI agent that discovers, scores, and delivers weekly event intelligence tailored to the exact audience a business owner defines. It aggregates events across multiple platforms, evaluates each one against the user's specific community and keywords using large language model reasoning, and delivers a structured digest to their inbox — automatically, every week, without manual effort.

The system operates in three phases:

### Phase 1 — Discovery

Growth Radar queries multiple event platforms in parallel across up to 7 cities per run:

- **AlleEvents** — the largest US aggregator of local and regional events, covering expos, cultural festivals, association meetings, and community gatherings
- **Luma** — the primary platform for professional, tech, and startup-adjacent events
- **Ticketmaster Discovery API** — structured event data covering conferences, cultural celebrations, large-scale expos, and civic events, with attendance and venue detail

This multi-source strategy surfaces events that no single platform aggregates, including events that are poorly indexed, locally organized, or platform-exclusive. After aggregation, events are deduplicated by URL and filtered to remove past dates. Events seen in previous runs are automatically excluded, ensuring the weekly digest remains fresh rather than repeating the same listings.

### Phase 2 — Scoring

Each discovered event is evaluated by Claude (Anthropic's large language model) against two dimensions of the user's profile: the community description (who they serve) and their keywords (how that community self-organizes).

The scoring model assesses:

- Presence of vendor floors, sponsorship tiers, or exhibitor opportunities
- Expected attendance from the user's specific target audience
- Organizer type and credibility (established associations, chambers of commerce, government bodies)
- Event category alignment with the user's growth objectives
- Partnership and long-term relationship potential with the organizing entity

Each event receives a structured score with a recommended action and plain-language justification. Cities are independently scored for activity level and opportunity gap — a measure of how much untapped potential exists in that market relative to competitive presence.

When a city shows a significant week-over-week surge in event activity (2x or greater), a **Hot City Alert** appears at the top of the weekly email digest, flagging an emerging market opportunity before it becomes widely known.

### Phase 3 — Delivery

Top-scored events are compiled into a structured HTML email and delivered on an automated weekly schedule. Each entry in the digest includes the event name, city, date, AI score, recommended action, and the model's reasoning. The digest is designed to support immediate decision-making: a business owner should be able to read it in five minutes and know exactly which events to act on and how.

For each event, the Streamlit interface generates a personalized first outreach email to the event organizer — including context about the user's audience, why the event is relevant, and a clear ask — in under 30 seconds.

---

## Capability Summary

| Capability | Description |
|---|---|
| Audience-aware AI scoring | Each event is evaluated against your exact community description and keywords, not a generic category taxonomy |
| Multi-source event aggregation | AlleEvents, Luma, and Ticketmaster queried in parallel per city per run |
| City opportunity intelligence | Activity scores and opportunity gap scores per city, with a tactical first-step recommendation |
| Hot city alerts | Detects and surfaces week-over-week surges in city event activity in the weekly email digest |
| Cross-run deduplication | Events seen in the prior 14 days are automatically excluded; state persists across automated runs |
| One-click outreach generation | Produces a personalized organizer outreach email per event in under 30 seconds |
| Outreach status tracking | Mark events as Contacted, Meeting Booked, Attending, or Skip — statuses populate the CSV export |
| Automated weekly pipeline | GitHub Actions runs the full pipeline every Monday at 6am EST — no manual intervention required |
| Profile auto-fill from website | Paste a URL and Claude extracts your community, keywords, and recommended cities automatically |
| Structured CSV export | Full report with pre-built tracker columns for CRM or spreadsheet-based pipeline management |
| Streamlit web interface | Browser-based UI for on-demand scans, result review, outreach generation, and status tracking |
| Open source and self-hostable | Full source code available under MIT license; no vendor lock-in, no subscription required |

---

## Who This Is For

Growth Radar is designed for operators whose growth depends on in-person presence:

- **Small business owners and founders** who need systematic event discovery without a dedicated marketing team
- **Community organizers and association leaders** who must identify where their members gather and how to engage them
- **Growth marketers at early-stage companies** running lean, multi-city event strategies on limited budgets
- **Consultants and professional service providers** whose client pipeline is built through in-person relationship development

The tool is particularly effective for businesses whose target customers attend cultural festivals, trade expos, business association events, government procurement seminars, and professional networking gatherings — event categories that are chronically underrepresented in generic discovery tools and inaccessible to businesses without marketing infrastructure.

---

## System Architecture

```
growth-radar/
├── main.py              # Headless pipeline: scrape → deduplicate → score → alert → email
├── app.py               # Streamlit UI: interactive runs, outreach generator, status tracker
├── config.py            # Profile loader, runtime configuration, scoring thresholds
├── dedup.py             # Cross-run event deduplication engine (14-day rolling window)
├── city_history.py      # City activity history tracking and hot-city surge detection
├── scrapers/
│   └── events.py        # AlleEvents, Luma, and Ticketmaster Discovery API scrapers
├── scoring/
│   ├── event_scorer.py  # Claude AI event scoring — audience and keyword aware
│   └── city_scorer.py   # Claude AI city opportunity scoring — distinct organizer aware
├── alerts/
│   └── digest.py        # HTML email builder with hot city alerts and Resend delivery
└── .github/workflows/
    └── radar.yml        # GitHub Actions weekly schedule with run-state persistence
```

The headless pipeline (`main.py`) and the interactive interface (`app.py`) share the same scoring and scraping modules. Audience profile state is isolated per invocation in the Streamlit interface, preventing cross-user contamination in shared hosting environments.

---

## Live Demo

**[growth-radar.streamlit.app](https://growth-radar.streamlit.app)** — No installation required. Bring your Anthropic API key and run a complete city scan in under 3 minutes.

---

## Quick Start (Local Installation)

**Requirements:** Python 3.11+

```bash
git clone https://github.com/ogbonnayastephen/growth-radar
cd growth-radar
pip install -r requirements.txt
cp .env.example .env
# Populate .env with your API keys (see API Keys section below)
python3 main.py --once
```

To launch the interactive Streamlit interface:

```bash
streamlit run app.py
```

---

## API Keys

| Key | Source | Required | Purpose |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) | Yes | Powers all AI scoring and outreach generation (~$0.50 per full run) |
| `RESEND_API_KEY` | [resend.com](https://resend.com) | Yes (email) | Delivers the weekly HTML digest via Resend's transactional email API |
| `RESEND_FROM_EMAIL` | Your verified Resend sender address | Yes (email) | From address displayed on the weekly digest |
| `ALERT_EMAIL` | Your email address | Yes (email) | Destination inbox for the weekly digest |
| `TICKETMASTER_API_KEY` | [developer.ticketmaster.com](https://developer.ticketmaster.com) | Optional | Expands event coverage with Ticketmaster's structured event database (free tier: 5,000 calls/day). For Streamlit Cloud deployments, add to app Secrets. For GitHub Actions, add as a repository secret. Gracefully bypassed if the daily limit is reached. |

All keys are loaded from environment variables. The Streamlit interface accepts the Anthropic key at runtime and never persists it to disk or transmits it to any third party.

---

## Automated Weekly Email — GitHub Actions Setup

Growth Radar is designed to run fully autonomously once configured. No cron server, no cloud compute subscription, and no ongoing manual work are required.

**Configuration steps:**

1. Fork this repository to your GitHub account
2. Navigate to **Settings → Secrets and variables → Actions** and add the following repository secrets:
   - `ANTHROPIC_API_KEY`
   - `RESEND_API_KEY`
   - `RESEND_FROM_EMAIL`
   - `ALERT_EMAIL`
   - `RADAR_PROFILE` — your audience profile as a JSON string (copy from the Streamlit app's sync panel)
   - `TICKETMASTER_API_KEY` (optional)
3. Enable GitHub Actions on your fork
4. The pipeline will execute automatically every **Monday at 6:00am EST**
5. Manual runs can be triggered at any time via **Actions → Run workflow**

After each automated run, the pipeline commits updated `seen_events.json` and `city_history.json` files back to your repository. These files enable cross-run deduplication and hot-city surge detection to function correctly across consecutive weekly runs without external database infrastructure.

---

## Audience Profile

The audience profile is the core configuration that determines what Growth Radar discovers and how it scores. It contains three fields:

| Field | Description | Example |
|---|---|---|
| `community` | A precise one-sentence description of your target audience | `"Black-owned food and beverage businesses in the Southern US seeking retail distribution and vendor market opportunities"` |
| `keywords` | Terms your target audience searches for and organizes around | `food-expo, black-business, culinary, vendor-market, small-batch, farmers-market` |
| `cities` | US cities to include in each scan (maximum 7 per run) | `Houston, Atlanta, New Orleans, Memphis, Charlotte` |

Profiles are defined through the Streamlit app (with optional website auto-fill) or directly in `radar_profile.json`. For automated runs, the profile is delivered via the `RADAR_PROFILE` environment variable, which takes priority over the local file.

---

## AI Scoring Model

Claude evaluates each event against the audience profile and returns a structured JSON object:

| Field | Type | Description |
|---|---|---|
| `opportunity_score` | Integer (1–10) | Relevance score for the user's specific audience and keywords |
| `estimated_target_attendance` | Integer | Estimated number of attendees from the target community |
| `event_category` | String | Classification: `cultural_festival`, `business_expo`, `professional_networking`, `government_program`, `association_event`, `religious`, `entertainment`, `other` |
| `business_value_fit` | String | `low`, `medium`, or `high` assessment of business development potential |
| `recommended_action` | String | `attend_and_table`, `sponsor_booth`, `partner_with_organizer`, `send_ambassador`, `vendor_booth`, `monitor`, or `skip` |
| `action_reason` | String | One-sentence explanation of the recommended action |
| `organizer_partnership_potential` | String | `low`, `medium`, or `high` assessment of long-term organizer relationship value |
| `alert_priority` | String | `urgent`, `this_week`, or `backlog` |

Events scoring below the configured threshold (`MIN_SCORE_THRESHOLD`, default: 5) are filtered before inclusion in the digest.

---

## Customization

| Parameter | Location | Default | Description |
|---|---|---|---|
| Audience, keywords, cities | Streamlit app or `radar_profile.json` | — | Core audience configuration |
| `MIN_SCORE_THRESHOLD` | `config.py` | `5` | Minimum AI score required for inclusion in the digest |
| `TOP_N_EVENTS` | `config.py` | `50` | Maximum events included in each email digest |
| `MAX_EVENTS_TO_SCORE` | `config.py` | `200` | Maximum events submitted to Claude per run (cost control) |
| `CITIES_PER_RUN` | `config.py` | `7` | Cities scanned per automated run when no explicit list is provided |
| Deduplication window | `dedup.py` | `14 days` | Events seen within this window are excluded from subsequent runs |
| Email design | `alerts/digest.py` | — | Full HTML email template; modify layout, colors, and sections as needed |
| Additional event sources | `scrapers/events.py` | — | Add new scraper functions and register them in `scrape_events()` |

---

## License

MIT License — free to use, modify, fork, and deploy. Attribution appreciated but not required.

---

*Growth Radar is built and maintained by Ogbonnaya Isaac Stephen.*
*Source: [github.com/ogbonnayastephen/growth-radar](https://github.com/ogbonnayastephen/growth-radar)*
