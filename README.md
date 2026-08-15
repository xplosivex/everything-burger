# Everything Burger 🍔

**The burger that does everything.**

> **Public instance:** a live deployment can be found at **https://everythingburger.ai** (if it's up when you click). Sign up at **https://everythingburger.ai/signup**. Note: email-based password recovery isn't wired up, so remember your login or make a new account if you forget.

Everything Burger is a gamified, AI-powered webpage generator. Type any prompt — no matter how nonsensical — and the app uses your AI backend of choice (**Mistral**, OpenAI, Claude, or Ollama) to generate a complete, styled HTML5 page. Every generation picks a random **page archetype** (a tabloid newspaper, a wanted poster, a yearbook, a court ruling, a grocery receipt, and 36 more), so the same prompt never produces the same format twice. Pages are enriched with real Google search results (images, news, videos, and shopping) via **SerpAPI** when a key is configured.

The whole thing is wrapped in an RPG-style progression system: generating pages earns you **crumbs** (in-app currency), **XP**, and **levels**. Crumbs buy **items** (consumables, artifacts, and trinkets) from the Emporium, which you can use, sell, trade, or trade up for rarer loot. You also earn **achievements**, complete **daily quests**, and compete on a community feed of generated pages with votes and comments.

## Features

- **AI page generation** — a 3-stage pipeline (content → structure → styling) driven by 40 random page archetypes, with live progress via WebSockets
- **Archetype system** — each generation picks a random archetype (tabloid, wiki article, wanted poster, game manual, yearbook, court ruling, and more), each with its own content voice, layout, theme, and format-specific elements
- **Twists & modifiers** — 1–2 random twists shape the writing voice; 1–3 random modifiers (weighted) add quirky structural/styling flourishes to every page
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
| Realtime | Flask-SocketIO (threading / long-polling) |
| ORM / Migrations | Flask-SQLAlchemy + Flask-Migrate (Alembic) |
| Server | Waitress (threaded WSGI) |
| Queue / State | Redis |
| AI | Mistral / OpenAI / Claude / Ollama (BYOK) |
| Search | SerpAPI (Google) |
| Scraping / Images | BeautifulSoup4, Pillow, Selenium (headless Chrome) |
| Database | SQLite (WAL mode) |
| Frontend | Tailwind CSS (CDN), Socket.IO client, Google Fonts |

## Requirements

- **Python 3.10+** (developed on 3.14)
- **Redis** — the task queue and generation state live in Redis. Run it with `redis-server` (or `podman run -d -p 6379:6379 redis:7-alpine`).
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

Then edit `.env` and fill in your keys. **You need an API key for your AI backend of choice** (default: `MISTRAL_API_KEY`). A `SERP_API_KEY` is optional but recommended for richer pages.

| Variable | Required | Description | Where to get it |
|---|---|---|---|
| `AI_BACKEND` | ⬜ | `mistral` (default), `openai`, `claude`, or `ollama` | — |
| `MISTRAL_API_KEY` | one of | AI content generation, trinket naming, summaries | [console.mistral.ai](https://console.mistral.ai) |
| `OPENAI_API_KEY` | one of | OpenAI backend | [platform.openai.com](https://platform.openai.com) |
| `ANTHROPIC_API_KEY` | one of | Claude backend | [console.anthropic.com](https://console.anthropic.com) |
| `OLLAMA_API_KEY` | for Ollama Cloud | Ollama backend (`AI_BACKEND=ollama`) | [ollama.com](https://ollama.com) |
| `SERP_API_KEY` | ⬜ (recommended) | Google image/news/video/shopping search | [serpapi.com](https://serpapi.com) |
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

Pick the startup profile that matches how many people you expect to serve:

| Profile | Command | Concurrency |
|---|---|---|
| Small (~25 users) | `python run.py 1` | 8 request threads, 4 background workers |
| Medium (~150 users) | `python run.py 2` | 24 request threads, 12 background workers |
| Large (~1000 users) | `python run.py 3` | 80 request threads, 32 background workers |

You can also set `EB2_PROFILE=1|2|3` in the environment. It defaults to profile 2.

```bash
python run.py 2
```

Then open <http://localhost:8000> and create an account.

> **Startup:** `python run.py` boots waitress and embedded queue workers in a single process. Jobs are pushed to Redis by the web app and consumed by the workers, so background work survives restarts. For production, run it behind a reverse proxy (nginx/Caddy) with TLS and set `BASE_URL` to your real domain.

## Configuration Reference

All configuration is read from environment variables (or `.env`). See [`.env.example`](.env.example) for the full list with comments.

### AI provider (Bring Your Own Key)

The app supports four AI backends, selected with `AI_BACKEND`. Each needs its own key (self-hosted Ollama excepted). Mistral is the default and recommended.

| Backend | `AI_BACKEND` | Key env var | Console |
|---|---|---|---|
| Mistral (recommended) | `mistral` | `MISTRAL_API_KEY` | https://console.mistral.ai |
| OpenAI | `openai` | `OPENAI_API_KEY` | https://platform.openai.com |
| Claude | `claude` | `ANTHROPIC_API_KEY` | https://console.anthropic.com |
| Ollama Cloud | `ollama` | `OLLAMA_API_KEY` | https://ollama.com |
| Ollama (self-hosted) | `ollama` | none | set `OLLAMA_BASE_URL=http://localhost:11434` |

### Model tuning

Each backend has sensible defaults per stage; override them in `.env` to balance cost vs. quality:

| Variable | Default (per backend) | Role |
|---|---|---|
| `CONTENT_MODEL` | mistral-large-latest / gpt-5.6-terra / claude-sonnet-5 / llama3.2 | Best writing quality |
| `STRUCTURE_MODEL` | codestral-latest / gpt-5.6-terra / claude-sonnet-5 / llama3.2 | Best at code/HTML generation |
| `STYLING_MODEL` | mistral-medium-latest / gpt-5.6-terra / claude-sonnet-5 / llama3.2 | Tailwind styling pass |
| `SUMMARY_MODEL` | mistral-small-latest / gpt-5.6-luna / claude-haiku-4-5 / llama3.2 | Lightweight summaries |

### Prompt configuration

The system prompts that drive generation are hardcoded in `app/generation/` (content, structure, and styling modules). Tweak them to change how pages are generated.

The **archetype catalog** lives in `app/generation/archetypes/` as JSON files — one per archetype (40 total), plus `twists.json` (100 writing twists) and `modifiers.json` (300 structural/styling modifiers). Each archetype file defines its content styles, layouts, themes, image-count ranges, and a pool of 10–20 format-specific elements (each with content, HTML, and styling fragments). Add a new `.json` file there and it's automatically available to generation.

## Project Structure

```
.
├── run.py                  # Entry point: waitress + embedded Redis queue workers + profile (1|2|3)
├── app/
│   ├── __init__.py         # App factory: config, extensions, blueprint registration
│   ├── config.py           # Environment-based configuration (API keys, models, SMTP)
│   ├── extensions.py       # Flask extensions (db, csrf, limiter, socketio, migrate)
│   ├── models.py           # SQLAlchemy models + item/achievement/quest definitions
│   ├── utils.py            # login_required decorator, flash_message helper
│   ├── email.py            # SMTP password-reset + welcome emails
│   ├── queue.py            # Redis task queue (enqueue/dequeue)
│   ├── worker.py           # Embedded queue worker threads (consume jobs)
│   ├── tasks.py            # Background task handlers (generate, iterate, watcher)
│   ├── state.py            # Redis-backed generation task state
│   ├── generation/         # AI page generation pipeline
│   │   ├── archetypes/      # JSON data: 40 archetype files + twists.json + modifiers.json
│   │   ├── archetypes.py    # Archetype/twist/modifier loading + selection
│   │   ├── content.py       # Stage 1: content generation (archetype voice + twists)
│   │   ├── structure.py    # Stage 2: HTML structure (archetype layout + modifiers)
│   │   ├── styling.py      # Stage 3: Tailwind styling (archetype theme + modifiers)
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

1. **Generate** — you submit a prompt on the dashboard. The request is pushed onto a Redis queue; an embedded worker runs the 3-stage pipeline using your configured AI backend (Mistral, OpenAI, Claude, or Ollama):
   - **Pick a format** — a random archetype is chosen (tabloid, wiki article, wanted poster, yearbook, court ruling, grocery receipt, and 36 more), plus 1–2 writing twists and 1–3 structural modifiers.
   - **Content** — the model writes the whole page in the archetype's voice, following the twists and a random premise/angle.
   - **Structure** — the model builds ONE cohesive HTML5 document in the archetype's layout (columns, TOC, centered poster, etc.), including 3–9 randomly selected format-specific elements.
   - **Styling** — the model applies one unified theme (single background, one accent palette, one font pairing) so the page reads as a single designed artifact.
   - Real images/news/videos/shopping results are fetched from Google in parallel when a SerpAPI key is present, and the result is pushed to your page via Socket.IO.
2. **Reward** — completing a generation rolls for item drops, grants crumbs/XP, and checks achievements and daily quests.
3. **Iterate** — every page can be regenerated. Each version is stored as a `PageIteration`, and a "Watcher" AI scores it with a mood, summary, and points.
4. **Play** — spend crumbs in the Emporium, use/sell/trade items, trade up rarities, and show off your best pages on your profile.

## Deployment Notes

- The built-in server (`python run.py`) serves the app through **Waitress**, a production-grade threaded WSGI server. Pick the startup profile (1 = small, 2 = medium, 3 = large) to match your expected traffic.
- Background work (page generation, iteration rewrites, watcher verdicts) is pushed onto a **Redis queue** and consumed by embedded worker threads sized by the chosen profile. The task queue and task state live in Redis, so pending work survives restarts.
- The SQLite database runs in **WAL mode** with a busy timeout, so concurrent readers and a single writer proceed without lock errors.
- For production, put it behind a reverse proxy (nginx/Caddy) with TLS, and set `BASE_URL` to your real domain.
- Sessions are signed with `SECRET_KEY` — set a fixed value in `.env` so users stay logged in across restarts.
- The SQLite database lives in `instance/database.db`. Back it up regularly.
- Rate limiting (Flask-Limiter) and CSRF protection (Flask-WTF) are enabled by default.

## Known Limitations

- **Modular architecture** — the app is split into `app/generation/` (AI pipeline) and `app/routes/` (blueprints), with models, config, and helpers in separate modules.
- **Archetype data is JSON** — the archetype catalog, twists, and modifiers live in `app/generation/archetypes/*.json`. Adding a new archetype is just dropping in a new JSON file, but the content/layout/theme fragments are prompt text, so output quality depends on how well the model follows them.
- **Redis dependency** — the task queue and generation state require Redis; the app will not start without it.
- **SQLite** — fine for a personal project; swap to PostgreSQL for heavy multi-user traffic.
- **No test suite** — the project has no automated tests yet.

## License

This is a personal project. No license is specified — all rights reserved by the author.
