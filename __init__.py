# Fountain Pen Bot package

# Make config variables directly importable from src
from .config import (
    SUBREDDIT, INTERVAL, LIMIT, FLAIR_NAME, QUERY, PEN_MODELS_TO_WATCH,
    DISCORD_TOKEN, CHANNEL_ID, SEEN_POSTS_SHELVE_FILE,
    REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT
)

# Import key functionality
from .utils import normalize_text, check_post_for_pen_models, is_post_seen, mark_post_as_seen, close_seen_posts_db
from .clients import initialize_reddit_client, run_discord_bot, fetch_and_send_new_posts 