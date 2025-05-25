import os
from dotenv import load_dotenv

load_dotenv()

# Reddit Configuration
SUBREDDIT = "Pen_Swap"  # The subreddit to monitor
INTERVAL = 60  # Check interval in seconds (5 minutes)
LIMIT = 10  # Number of posts to fetch each check
FLAIR_NAME = "WTS-OPEN"
QUERY = f'flair_name:"{FLAIR_NAME}"'
PEN_MODELS_TO_WATCH = ["Lamy Safari", "Pilot Vanishing Point", "TWSBI Eco", "Metropolitan", "m200", "Opus 88", "Custom 823", "pelikan m200", "lamy 2k", "lamy 2000", "decimo", "opus 88", "pro gear", "vanishing point", "pilot custom", "pilot vp", "capless"]

# Discord Configuration
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))

# Database Configuration
SEEN_POSTS_SHELVE_FILE = "seen_posts_shelf"

# Reddit API Credentials
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT")
