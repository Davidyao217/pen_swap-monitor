import os
import praw
from dotenv import load_dotenv

load_dotenv()

reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent=os.getenv("REDDIT_USER_AGENT")
)


def fetch_new_submissions(subreddit_name: str, limit: int = 25):
    """
    Fetch latest submissions from a subreddit.
    """
    subreddit = reddit.subreddit(subreddit_name)
    return subreddit.new(limit=limit)