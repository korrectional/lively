"""
Configuration and constants for Lively.
"""

import os
from pathlib import Path

# Base data directory (defaults to ~/.lively or custom path)
BASE_DATA_DIR = Path(os.getenv("LIVELY_DATA_DIR", Path.home() / ".lively")).resolve()

# Subdirectories and persistent files
MEMORIES_DIR = BASE_DATA_DIR / "memories"
JOURNAL_DIR = MEMORIES_DIR / "journal"
PROJECTS_DIR = BASE_DATA_DIR / "projects"
BLOG_DIR = BASE_DATA_DIR / "blog"
THOUGHTS_DIR = BASE_DATA_DIR / "thoughts"
WORLD_FILE = BASE_DATA_DIR / "world.json"
GMAIL_TOKEN_FILE = BASE_DATA_DIR / "gmail_token.json"
GMAIL_CREDENTIALS_FILE = BASE_DATA_DIR / "gmail_credentials.json"
SCHEDULE_CONFIG_FILE = BASE_DATA_DIR / "schedule.json"
SENT_EMAILS_FILE = MEMORIES_DIR / "sent_emails.json"

# Server configuration
SERVER_HOST = os.getenv("LIVELY_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("LIVELY_PORT", "8880"))
TAILSCALE_BASE_URL = os.getenv("LIVELY_TAILSCALE_URL", f"http://dietpi:{SERVER_PORT}")

# World boundaries (coordinates: -1000 to +1000, 2000x2000 square)
WORLD_MIN_X = -1000
WORLD_MAX_X = 1000
WORLD_MIN_Y = -1000
WORLD_MAX_Y = 1000
MIN_OBJECT_DISTANCE = float(os.getenv("LIVELY_MIN_OBJECT_DISTANCE", "60.0"))

# Squirrel specifics
SQUIRREL_NAME = "Squirrel"
USER_EMAIL = os.getenv("LIVELY_USER_EMAIL", "tarassekanev@gmail.com")
SQUIRREL_EMAIL = os.getenv("LIVELY_SQUIRREL_EMAIL", "tarassekanev+squirrel@gmail.com")
AGYC_BIN = os.getenv("AGYC_BIN", "agyc")
AGYC_EFFORT = os.getenv("LIVELY_AGYC_EFFORT", "high")

def ensure_directories():
    """Ensure all required runtime data directories exist."""
    BASE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    MEMORIES_DIR.mkdir(parents=True, exist_ok=True)
    JOURNAL_DIR.mkdir(parents=True, exist_ok=True)
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    BLOG_DIR.mkdir(parents=True, exist_ok=True)
    THOUGHTS_DIR.mkdir(parents=True, exist_ok=True)
