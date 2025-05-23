import asyncpraw
import sys
from datetime import datetime
from config import (
    REDDIT_CLIENT_ID,
    REDDIT_CLIENT_SECRET,
    REDDIT_USER_AGENT,
    SUBREDDIT,
    QUERY,
    LIMIT,
    PEN_MODELS_TO_WATCH
)
from utils.text_utils import check_post_for_pen_models
from utils.db_manager import is_post_seen, mark_post_as_seen

# ------------------------------------------------------------------
# Reddit Client Initialization
# ------------------------------------------------------------------

async def initialize_reddit_client():
    """Initialize and return a Reddit API client."""
    return asyncpraw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT
    )

# ------------------------------------------------------------------
# Post Processing Functions
# ------------------------------------------------------------------

async def fetch_and_send_new_posts(channel, reddit):
    print("Fetching new posts")
    try:
        # Access the subreddit
        subreddit = await reddit.subreddit(SUBREDDIT)
        
        # Search for posts matching our query
        async for submission in subreddit.search(
            QUERY,
            sort='new',
            limit=LIMIT,
            syntax='lucene'
        ):
            # Print separation for logging clarity
            print("\n\n")
            print("-" * 100)
            print(f"Processing post: {submission.id}")
            print("-" * 100)

            # Skip already processed posts
            if is_post_seen(submission.id):
                print(f"Skipping already seen post: {submission.id} - {submission.title}")
                continue
            
            # Combine title and body for analysis
            combined_text = f"{submission.title} {submission.selftext}"
            
            # Print the post content with proper formatting
            print(f"    {submission.title}")
            print("\n    " + submission.selftext.replace("\n", "\n    "))
            print("\n\n")

            # Check if the post contains any watched pen models
            found_pen_models = check_post_for_pen_models(combined_text, PEN_MODELS_TO_WATCH)

            if found_pen_models:
                # If models are found, prepare and send Discord message
                print(f"Found models: {', '.join(found_pen_models)}")
                
                message = f"**{submission.title}**\n"
                message += f"Found: {', '.join(found_pen_models)}\n"
                message += f"https://www.reddit.com{submission.permalink}"
                
                await channel.send(message)
                mark_post_as_seen(submission.id)
                print(f"Marked post as seen: {submission.id}")
            else:
                print(f"No watched models found in post: {submission.title}")
    except Exception as e:
        print(f"Error fetching posts: {e}") 