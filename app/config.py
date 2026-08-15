import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Mistral AI API key (https://console.mistral.ai) -- REQUIRED
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY", "")

# SerpAPI key for Google image/news/video/shopping search (https://serpapi.com) -- REQUIRED
SERP_API_KEY = os.environ.get("SERP_API_KEY", "")

# Model assignments -- tune these based on cost/quality tradeoffs
CONTENT_MODEL = os.environ.get("CONTENT_MODEL", "mistral-large-latest")    # Best writing quality
STRUCTURE_MODEL = os.environ.get("STRUCTURE_MODEL", "codestral-latest")    # Best at code/HTML generation
STYLING_MODEL = os.environ.get("STYLING_MODEL", "mistral-medium-latest")   # Good balance for styling task
SUMMARY_MODEL = os.environ.get("SUMMARY_MODEL", "mistral-small-latest")     # Lightweight, fine for summaries

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
