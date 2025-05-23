import os
from dotenv import load_dotenv

load_dotenv()

# Reddit Configuration
SUBREDDIT = os.getenv("SUBREDDIT_NAME", "Pen_Swap")
INTERVAL = int(os.getenv("CHECK_INTERVAL"))
LIMIT = int(os.getenv("LIMIT"))
FLAIR_NAME = "WTS-OPEN"
QUERY = f'flair_name:"{FLAIR_NAME}"'
PEN_MODELS_TO_WATCH = ["Lamy Safari", "Pilot Vanishing Point", "TWSBI Eco"]

# Discord Configuration
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))

# Database Configuration
SEEN_POSTS_SHELVE_FILE = "seen_posts_shelf"

# Reddit API Credentials
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT") 