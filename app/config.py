import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ---------------------------------------------------------------------------
# AI BACKEND (Bring Your Own Key)
# ---------------------------------------------------------------------------
# Pick the AI provider for page generation. Supported values:
#   mistral  (recommended)  https://console.mistral.ai
#   openai                   https://platform.openai.com
#   claude                   https://console.anthropic.com
#   ollama                   Ollama Cloud (https://ollama.com) or a self-hosted
#                            Ollama server. For self-hosted, set OLLAMA_BASE_URL
#                            to your server (e.g. http://localhost:11434). For
#                            Ollama Cloud, use the default base URL and set
#                            OLLAMA_API_KEY.
#
# All backends require their API key (self-hosted Ollama is the exception).
# ---------------------------------------------------------------------------
AI_BACKEND = os.environ.get("AI_BACKEND", "mistral")

MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
OLLAMA_API_KEY = os.environ.get("OLLAMA_API_KEY", "")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "https://ollama.com")

# Model assignments -- tune these based on cost/quality tradeoffs.
# These are per-backend defaults; the app resolves the right model for
# whatever AI_BACKEND is configured. CONTENT_*_MODEL / etc. can override.
CONTENT_MODEL = os.environ.get("CONTENT_MODEL", "")    # e.g. mistral-large-latest, gpt-4o, claude-sonnet-4-5, llama3.2
STRUCTURE_MODEL = os.environ.get("STRUCTURE_MODEL", "")  # Best at code/HTML generation
STYLING_MODEL = os.environ.get("STYLING_MODEL", "")     # Good balance for styling task
SUMMARY_MODEL = os.environ.get("SUMMARY_MODEL", "")      # Lightweight, fine for summaries

# SerpAPI key for Google image/news/video/shopping search (https://serpapi.com).
# Optional but recommended: without it, pages are generated without real
# images / news / video / shopping enrichment.
SERP_API_KEY = os.environ.get("SERP_API_KEY", "")
SERP_ENABLED = bool(SERP_API_KEY)

# Email configuration (used for password reset + welcome emails)
SMTP_SERVER = os.environ.get("SMTP_SERVER", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_ENABLED = bool(SMTP_SERVER and SMTP_USERNAME and SMTP_PASSWORD)

# Redis connection used for the task queue and generation state.
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# Public base URL used in password reset links (e.g. https://yourdomain.com)
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")

# Stable secret key for sessions. Set a fixed value in .env so sessions
# survive restarts. Falls back to a random key (sessions reset on restart).
SECRET_KEY = os.environ.get("SECRET_KEY", os.urandom(24))
