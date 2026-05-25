# The Community Growth Radar

An open-source AI agent that finds events, expos, and community
gatherings for Black business owners across US cities —
scored by AI and delivered to your inbox twice a week.

## Quick Start

```bash
git clone https://github.com/YOURUSERNAME/community-growth-radar
cd community-growth-radar
pip install -r requirements.txt
cp .env.example .env
# Add your API keys to .env
python main.py
```

## Get Your API Keys

| Key | Source | Purpose |
|-----|--------|---------|
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) | Powers AI scoring |
| `RESEND_API_KEY` | [resend.com](https://resend.com) | Free email delivery |

## How It Works

1. **Scrape** — Rotates through 7 of 16 major US cities per run, searching AlleEvents and Luma for events matching 18 community keywords.
2. **Score** — Claude AI scores each event 1–10 for relevance to Black business owners: vendor floors, procurement events, HBCU networks, and more.
3. **Deliver** — Sends one HTML email with the top 50 events sorted by date, plus city-level opportunity scores.

## Customization

- **Cities & keywords** → Edit [config.py](config.py)
- **AI scoring criteria** → Edit [scoring/event_scorer.py](scoring/event_scorer.py)
- **Score threshold** → Change `MIN_SCORE_THRESHOLD` in [config.py](config.py)
- **Email design** → Edit [alerts/digest.py](alerts/digest.py)

## Deploy (GitHub Actions — completely free)

1. Push this repo to GitHub
2. Go to **Settings → Secrets → Actions** and add:
   - `ANTHROPIC_API_KEY`
   - `RESEND_API_KEY`
   - `ALERT_EMAIL`
3. Enable Actions — runs automatically every **Monday and Thursday at 7am UTC**
4. Trigger a manual run anytime via **Actions → Run workflow**

## Project Structure

```
community-growth-radar/
├── main.py              # Orchestrator — runs the full pipeline
├── config.py            # Cities, keywords, thresholds
├── scrapers/
│   └── events.py        # AlleEvents + Luma scrapers
├── scoring/
│   ├── event_scorer.py  # Claude AI event scoring
│   └── city_scorer.py   # Claude AI city opportunity scoring
├── alerts/
│   └── digest.py        # HTML email builder + Resend sender
└── .github/workflows/
    └── radar.yml        # GitHub Actions schedule
```

## License

MIT — free to use, fork, and build on.
