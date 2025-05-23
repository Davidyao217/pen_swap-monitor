import asyncpraw
from src.config import (
    REDDIT_CLIENT_ID,
    REDDIT_CLIENT_SECRET,
    REDDIT_USER_AGENT,
    SUBREDDIT,
    QUERY,
    LIMIT,
    PEN_MODELS_TO_WATCH
)
from src.utils.text_utils import check_body_for_pen_models
from src.utils.db_manager import is_post_seen, mark_post_as_seen

async def initialize_reddit_client():
    """Initialize and return a Reddit API client."""
    return asyncpraw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT
    )

async def fetch_and_send_new_posts(channel, reddit):
    """Fetch new posts from Reddit and send matching ones to Discord."""
    print("Fetching new posts")
    try:
        subreddit = await reddit.subreddit(SUBREDDIT)
        async for submission in subreddit.search(
            QUERY,
            sort='new',
            limit=LIMIT,
            syntax='lucene'
        ):
            # Skip if already seen
            if is_post_seen(submission.id):
                print(f"Skipping already seen post: {submission.id} - {submission.title}")
                continue

            print(f"Processing post: {submission.title}")
            
            # Check for pen models in post body
            found_pen_models = check_body_for_pen_models(submission.selftext, PEN_MODELS_TO_WATCH)

            if found_pen_models:
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