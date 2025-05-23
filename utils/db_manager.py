import shelve
from config import SEEN_POSTS_SHELVE_FILE

# Global shelve database to avoid opening it repeatedly
_seen_posts_db = None

def get_seen_posts_db():
    global _seen_posts_db
    if _seen_posts_db is None:
        try:
            _seen_posts_db = shelve.open(SEEN_POSTS_SHELVE_FILE)
        except Exception as e:
            print(f"Error opening seen posts database: {e}")
    return _seen_posts_db

def close_seen_posts_db():
    global _seen_posts_db
    if _seen_posts_db is not None:
        try:
            _seen_posts_db.close()
            _seen_posts_db = None
        except Exception as e:
            print(f"Error closing seen posts database: {e}")

def is_post_seen(post_id: str) -> bool:
    try:
        seen_db = get_seen_posts_db()
        if seen_db is not None:
            return post_id in seen_db
        return False
    except Exception as e:
        print(f"Error checking if post is seen: {e}")
        return False

def mark_post_as_seen(post_id: str):
    try:
        seen_db = get_seen_posts_db()
        if seen_db is not None:
            seen_db[post_id] = True
            # Ensure changes are written to disk
            seen_db.sync()
    except Exception as e:
        print(f"Error marking post as seen: {e}") 