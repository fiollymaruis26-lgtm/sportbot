import os

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
SPORTSDB_API_KEY = os.getenv("SPORTSDB_API_KEY", "3")
SPORTSDB_BASE_URL = f"https://www.thesportsdb.com/api/v1/json/{SPORTSDB_API_KEY}"

SPORT_ALIASES = {
    "foot": "Soccer",
    "football": "Soccer",
    "soccer": "Soccer",
    "basket": "Basketball",
    "basketball": "Basketball",
    "cricket": "Cricket",
    "tennis": "Tennis",
}

SPORT_EMOJIS = {
    "Soccer": "⚽",
    "Basketball": "🏀",
    "Cricket": "🏏",
    "Tennis": "🎾",
}
