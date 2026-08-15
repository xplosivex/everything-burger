# Everything Burger 🍔

**The burger that does everything.**

Everything Burger is a gamified, AI-powered webpage generator. Type any prompt — no matter how nonsensical — and the app uses **Mistral AI** to generate a complete, styled HTML5 page enriched with real Google search results (images, news, videos, and shopping) via **SerpAPI**.

The whole thing is wrapped in an RPG-style progression system: generating pages earns you **crumbs** (in-app currency), **XP**, and **levels**. Crumbs buy **items** (consumables, artifacts, and trinkets) from the Emporium, which you can use, sell, trade, or trade up for rarer loot. You also earn **achievements**, complete **daily quests**, and compete on a community feed of generated pages with votes and comments.

## Features

- **AI page generation** — a 3-stage pipeline (content → structure → styling) using Mistral AI models, with live progress via WebSockets
- **Real search enrichment** — images, news, videos, and shopping results pulled from Google via SerpAPI
- **Page iterations** — regenerate and iterate on any page, with a "Watcher" AI that scores each version
- **RPG economy** — crumbs, XP, levels, daily quests, and achievements
- **Item system** — consumables, artifacts, and trinkets with rarities (common → mythical), quality rolls, trade-ups, and a player marketplace
- **Community** — public page feed, profiles with featured pages, votes, and nested comments
- **Auth** — signup/login, password reset via email, and profile customization with AI-searched avatars/banners

## Tech Stack

| Category | Technology |
|---|---|
| Framework | Flask 3.x |
| Realtime | Flask-SocketIO + gevent |
| ORM / Migrations | Flask-SQLAlchemy + Flask-Migrate (Alembic) |
| Server | gevent WSGIServer (WebSocket handler) |
| AI | Mistral AI SDK |
| Search | SerpAPI (Google) |
| Scraping / Images | BeautifulSoup4, Pillow, Selenium (headless Chrome) |
| Database | SQLite |
| Frontend | Tailwind CSS (CDN), Socket.IO client, Google Fonts |

## Requirements

- **Python 3.10+** (developed on 3.14)
- **Chrome / Chromium** installed (used by Selenium to screenshot generated pages for thumbnails)
- API keys for the services you want to use (see below)

## Quick Start

### 1. Clone & set up the environment

```bash
git clone https://github.com/xplosivex/everything-burger.git
cd everything-burger

python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure your API keys

```bash
cp .env.example .env
```

Then edit `.env` and fill in your keys. **At minimum you need `MISTRAL_API_KEY` and `SERP_API_KEY`** for page generation to work.

| Variable | Required | Description | Where to get it |
|---|---|---|---|
| `MISTRAL_API_KEY` | ✅ | AI content generation, trinket naming, summaries | [console.mistral.ai](https://console.mistral.ai) |
| `SERP_API_KEY` | ✅ | Google image/news/video/shopping search | [serpapi.com](https://serpapi.com) |
| `SMTP_SERVER` / `SMTP_PORT` / `SMTP_USERNAME` / `SMTP_PASSWORD` | ⬜ | Password reset + welcome emails | Your mail provider |
| `BASE_URL` | ⬜ | Public URL used in password reset links | — |
| `SECRET_KEY` | ⬜ | Session signing key (set a fixed value so logins survive restarts) | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `HOST` / `PORT` | ⬜ | Bind address/port for the built-in server (default `0.0.0.0:8000`) | — |

> **Note:** The `.env` file is gitignored and never committed. Never commit real API keys.

### 3. Initialize the database

The database is created automatically on first run (`instance/database.db`). If you make schema changes, use Flask-Migrate:

```bash
flask db upgrade
```

### 4. Run it

```bash
python run.py
```

Then open <http://localhost:8000> and create an account.

## Configuration Reference

All configuration is read from environment variables (or `.env`). See [`.env.example`](.env.example) for the full list with comments.

### Model tuning

The generation pipeline uses four Mistral models. Override them in `.env` to balance cost vs. quality:

| Variable | Default | Role |
|---|---|---|
| `CONTENT_MODEL` | `mistral-large-latest` | Best writing quality |
| `STRUCTURE_MODEL` | `codestral-latest` | Best at code/HTML generation |
| `STYLING_MODEL` | `mistral-medium-latest` | Tailwind styling pass |
| `SUMMARY_MODEL` | `mistral-small-latest` | Lightweight summaries |

### Prompt configuration

The system prompts that drive generation are hardcoded in `app/generation/` (content, structure, and styling modules). Tweak them to change how pages are generated.

## Project Structure

```
.
├── run.py                  # Entry point: gevent WSGIServer + WebSocket handler
├── app/
│   ├── __init__.py         # App factory: config, extensions, blueprint registration
│   ├── config.py           # Environment-based configuration (API keys, models, SMTP)
│   ├── extensions.py       # Flask extensions (db, csrf, limiter, socketio, migrate)
│   ├── models.py           # SQLAlchemy models + item/achievement/quest definitions
│   ├── utils.py            # login_required decorator, flash_message helper
│   ├── email.py            # SMTP password-reset + welcome emails
│   ├── state.py            # In-memory generation state
│   ├── generation/         # AI page generation pipeline
│   │   ├── blocks.py       # Content block definitions (staple/common/exotic)
│   │   ├── palette.py      # Weighted block palette selection
│   │   ├── content.py      # Stage 1: content generation (Mistral)
│   │   ├── structure.py    # Stage 2: HTML structure (Mistral)
│   │   ├── styling.py      # Stage 3: Tailwind styling (Mistral)
│   │   ├── images.py       # Google image fetching (SerpAPI)
│   │   ├── serp.py         # News/video/shopping enrichment (SerpAPI)
│   │   ├── effects.py      # Item effect application to generated HTML
│   │   ├── achievements.py # Achievement checks + crumb/XP rewards
│   │   ├── math.py         # create_complex_calculation helper
│   │   ├── iterations.py   # Page iteration + Watcher verdict generation
│   │   └── pipeline.py     # Main orchestrator
│   └── routes/             # Flask blueprints
│       ├── auth.py         # signup, login, logout, password reset
│       ├── pages.py        # view/save/vote/comment/delete pages
│       ├── profile.py      # profiles, featured pages, avatar/banner search
│       ├── generation.py   # dashboard, generate, regenerate, result
│       ├── inventory.py    # inventory, sell, use, toggle tradeable
│       ├── emporium.py     # shop, buy, list for sale, trade-ups
│       ├── achievements.py # achievements + daily quests
│       ├── iterations.py   # iterate pages, watcher verdicts
│       ├── misc.py         # clear-messages
│       └── helpers.py      # shared quest/achievement helpers
├── requirements.txt        # Python dependencies
├── .env.example            # Template for environment configuration
├── migrations/             # Alembic migrations
├── templates/              # 13 standalone Jinja2 templates
└── static/
    ├── cursors/            # Custom cursor images
    ├── icons/              # Item icons (artifacts, consumables, trinkets)
    └── page_assets/        # Loading animations
```

## How It Works

1. **Generate** — you submit a prompt on the dashboard. A gevent greenlet runs the 3-stage Mistral pipeline (content → structure → Tailwind styling), fetching real images/news/videos/shopping results from Google in parallel.
2. **Reward** — completing a generation rolls for item drops, grants crumbs/XP, and checks achievements and daily quests.
3. **Iterate** — every page can be regenerated. Each version is stored as a `PageIteration`, and a "Watcher" AI scores it with a mood, summary, and points.
4. **Play** — spend crumbs in the Emporium, use/sell/trade items, trade up rarities, and show off your best pages on your profile.

## Deployment Notes

- The built-in server (`python run.py`) is a gevent WSGIServer with WebSocket support — suitable for small-to-medium deployments.
- For production, put it behind a reverse proxy (nginx/Caddy) with TLS, and set `BASE_URL` to your real domain.
- Sessions are signed with `SECRET_KEY` — set a fixed value in `.env` so users stay logged in across restarts.
- The SQLite database lives in `instance/database.db`. Back it up regularly.
- Rate limiting (Flask-Limiter) and CSRF protection (Flask-WTF) are enabled by default.

## Known Limitations

- **Modular architecture** — the app is split into `app/generation/` (AI pipeline) and `app/routes/` (blueprints), with models, config, and helpers in separate modules.
- **In-memory generation state** — pending/completed generations are stored in a process-local dict and lost on restart.
- **SQLite** — fine for a personal project; swap to PostgreSQL for heavy multi-user traffic.
- **No test suite** — the project has no automated tests yet.

## License

This is a personal project. No license is specified — all rights reserved by the author.
