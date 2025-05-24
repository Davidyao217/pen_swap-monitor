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
            # Initialize or retrieve the ordered list of post IDs
            if '__post_order__' not in seen_db:
                seen_db['__post_order__'] = []

            post_order = seen_db['__post_order__']

            # Add new post to the shelf and the ordered list
            seen_db[post_id] = True
            post_order.append(post_id)

            # If the list exceeds 100, remove the oldest
            if len(post_order) > 100:
                oldest_post_id = post_order.pop(0) # Remove from the beginning
                if oldest_post_id in seen_db:
                    del seen_db[oldest_post_id]
            
            # Update the ordered list in the shelf
            seen_db['__post_order__'] = post_order
            
            # Ensure changes are written to disk
            seen_db.sync()
    except Exception as e:
        print(f"Error marking post as seen: {e}") 