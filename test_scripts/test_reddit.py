import os
import praw
from dotenv import load_dotenv

load_dotenv()

SUBREDDIT = os.getenv("SUBREDDIT_NAME", "Pen_Swap")
LIMIT = 10

reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent=os.getenv("REDDIT_USER_AGENT")
)

def test_fetch_submissions():
    try:
        subreddit = reddit.subreddit(SUBREDDIT)
        for submission in subreddit.new(limit=LIMIT):
            print(submission.title)
    except Exception as e:
        print(f"Error fetching posts: {e}")

if __name__ == "__main__":
    test_fetch_submissions()