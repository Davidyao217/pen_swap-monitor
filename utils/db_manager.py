import shelve
import threading
from config import SEEN_POSTS_SHELVE_FILE

# Thread lock for database operations to prevent race conditions
_db_lock = threading.Lock()

def is_post_seen(post_id: str) -> bool:
    """
    Check if a post has been seen before.
    
    Args:
        post_id: The Reddit post ID to check
        
    Returns:
        bool: True if the post has been seen, False otherwise
    """
    if not post_id:
        return False
        
    try:
        with _db_lock:
            with shelve.open(SEEN_POSTS_SHELVE_FILE, flag='r') as seen_db:
                return post_id in seen_db
    except FileNotFoundError:
        # Database doesn't exist yet, so post hasn't been seen
        return False
    except Exception as e:
        print(f"Error checking if post is seen: {e}")
        # In case of error, assume post hasn't been seen to avoid missing posts
        return False

def check_and_mark_post_as_seen(post_id: str) -> bool:
    """
    Atomically check if a post has been seen and mark it as seen if not.
    This prevents race conditions where multiple threads could process the same post.
    
    Args:
        post_id: The Reddit post ID to check and mark
        
    Returns:
        bool: True if post was NOT seen before (and is now marked), False if already seen
    """
    if not post_id:
        return False
        
    try:
        with _db_lock:
            with shelve.open(SEEN_POSTS_SHELVE_FILE, flag='c', writeback=True) as seen_db:
                # Check if already seen
                if post_id in seen_db:
                    return False  # Already seen
                
                # Initialize tracking structures if needed
                if '__post_order__' not in seen_db:
                    seen_db['__post_order__'] = []
                
                if '__lifetime_count__' not in seen_db:
                    seen_db['__lifetime_count__'] = 0

                post_order = seen_db['__post_order__']

                # Add new post to the shelf and the ordered list
                seen_db[post_id] = True
                post_order.append(post_id)
                
                # Increment lifetime counter for new posts
                seen_db['__lifetime_count__'] += 1

                # If the list exceeds 100, remove the oldest
                if len(post_order) > 100:
                    oldest_post_id = post_order.pop(0)  # Remove from the beginning
                    if oldest_post_id in seen_db:
                        del seen_db[oldest_post_id]
                
                # Update the ordered list in the shelf
                seen_db['__post_order__'] = post_order
                
                return True  # Successfully marked as new
                
    except Exception as e:
        print(f"Error in atomic check and mark: {e}")
        return False

def get_seen_posts_count() -> int:
    """
    Get the total lifetime number of seen posts.
    
    Returns:
        int: Total number of posts ever seen
    """
    try:
        with _db_lock:
            with shelve.open(SEEN_POSTS_SHELVE_FILE, flag='c', writeback=True) as seen_db:
                # Get recent posts count for consistency check
                recent_count = 0
                if '__post_order__' in seen_db:
                    recent_count = len(seen_db['__post_order__'])
                
                # Check if lifetime counter exists
                if '__lifetime_count__' in seen_db:
                    lifetime_count = seen_db['__lifetime_count__']
                    # Ensure lifetime count is at least as large as recent count
                    if lifetime_count < recent_count:
                        print(f"Warning: Fixing inconsistent lifetime count: {lifetime_count} < {recent_count}")
                        seen_db['__lifetime_count__'] = recent_count
                        lifetime_count = recent_count
                    return lifetime_count
                else:
                    # Initialize lifetime counter if it doesn't exist
                    # Use max of current entries or recent count
                    count = len(seen_db)
                    if '__post_order__' in seen_db:
                        count -= 1
                    if '__lifetime_count__' in seen_db:
                        count -= 1
                    count = max(count, recent_count)
                    seen_db['__lifetime_count__'] = count
                    return max(0, count)
    except FileNotFoundError:
        return 0
    except Exception as e:
        print(f"Error getting seen posts count: {e}")
        return 0

def get_recent_posts_count() -> int:
    """
    Get the count of recent posts in the database (limited to 100).
    
    Returns:
        int: Number of recent posts stored in the database
    """
    try:
        with _db_lock:
            with shelve.open(SEEN_POSTS_SHELVE_FILE, flag='r') as seen_db:
                # Get recent posts count from post_order list
                if '__post_order__' in seen_db:
                    recent_count = len(seen_db['__post_order__'])
                    # Consistency check - should never exceed lifetime count
                    if '__lifetime_count__' in seen_db:
                        lifetime_count = seen_db['__lifetime_count__']
                        if recent_count > lifetime_count:
                            print(f"Warning: Recent count {recent_count} exceeds lifetime count {lifetime_count}")
                            # Don't modify here, just log the issue - will be fixed by get_seen_posts_count
                    return recent_count
                else:
                    # Fallback: Count all keys except special keys
                    count = len(seen_db)
                    # Subtract special keys
                if '__lifetime_count__' in seen_db:
                    count -= 1
                return max(0, count)
    except FileNotFoundError:
        return 0
    except Exception as e:
        print(f"Error getting recent posts count: {e}")
        return 0

def repair_database() -> dict:
    """
    Repair the database by fixing any inconsistencies:
    1. Ensure lifetime count >= recent count
    2. Remove duplicate post IDs
    3. Ensure post_order list contains only existing post IDs
    
    Returns:
        dict: Report of fixes made
    """
    report = {
        "fixed_lifetime_count": False,
        "removed_duplicates": 0,
        "fixed_post_order": False,
        "original_lifetime": 0,
        "new_lifetime": 0,
        "original_recent": 0,
        "new_recent": 0
    }
    
    try:
        with _db_lock:
            with shelve.open(SEEN_POSTS_SHELVE_FILE, flag='c', writeback=True) as seen_db:
                # 1. Analyze current state
                has_lifetime = '__lifetime_count__' in seen_db
                has_post_order = '__post_order__' in seen_db
                
                if has_lifetime:
                    report["original_lifetime"] = seen_db['__lifetime_count__']
                
                # Initialize structures if missing
                if not has_post_order:
                    seen_db['__post_order__'] = []
                
                if not has_lifetime:
                    seen_db['__lifetime_count__'] = 0
                
                # Get all regular post IDs (excluding special keys)
                all_post_ids = [k for k in seen_db.keys() 
                               if k != '__post_order__' and k != '__lifetime_count__']
                
                post_order = seen_db['__post_order__']
                report["original_recent"] = len(post_order)
                
                # 2. Fix post_order list - ensure it contains only valid IDs
                fixed_post_order = [pid for pid in post_order if pid in all_post_ids]
                if len(fixed_post_order) != len(post_order):
                    report["fixed_post_order"] = True
                    seen_db['__post_order__'] = fixed_post_order
                
                # 3. Ensure all posts are in post_order (for older DBs)
                post_order_set = set(fixed_post_order)
                missing_posts = [pid for pid in all_post_ids if pid not in post_order_set]
                
                if missing_posts:
                    # If we found missing posts, add them to post_order
                    # Respect the 100 post limit
                    for pid in missing_posts:
                        fixed_post_order.append(pid)
                        if len(fixed_post_order) > 100:
                            oldest = fixed_post_order.pop(0)
                            # Don't delete the post ID - it's still in lifetime count
                    
                    seen_db['__post_order__'] = fixed_post_order
                    report["fixed_post_order"] = True
                
                # 4. Fix lifetime count if needed
                current_recent_count = len(fixed_post_order)
                current_lifetime_count = seen_db['__lifetime_count__']
                
                if current_lifetime_count < current_recent_count:
                    seen_db['__lifetime_count__'] = current_recent_count
                    report["fixed_lifetime_count"] = True
                
                # 5. Update report with final values
                report["new_recent"] = len(seen_db['__post_order__'])
                report["new_lifetime"] = seen_db['__lifetime_count__']
                
                return report
                
    except Exception as e:
        print(f"Error repairing database: {e}")
        report["error"] = str(e)
        return report

def mark_post_as_seen(post_id: str) -> bool:
    """
    Mark a post as seen and maintain the 100-post limit.
    
    Args:
        post_id: The Reddit post ID to mark as seen
        
    Returns:
        bool: True if successfully marked, False otherwise
    """
    if not post_id:
        return False
        
    try:
        with _db_lock:
            with shelve.open(SEEN_POSTS_SHELVE_FILE, flag='c', writeback=True) as seen_db:
                # Initialize or retrieve the ordered list of post IDs
                if '__post_order__' not in seen_db:
                    seen_db['__post_order__'] = []
                
                # Initialize lifetime counter if it doesn't exist
                if '__lifetime_count__' not in seen_db:
                    seen_db['__lifetime_count__'] = 0

                post_order = seen_db['__post_order__']

                # Check if post is already marked (avoid duplicates)
                if post_id in seen_db:
                    return True

                # Add new post to the shelf and the ordered list
                seen_db[post_id] = True
                post_order.append(post_id)
                
                # Increment lifetime counter for new posts
                seen_db['__lifetime_count__'] += 1

                # If the list exceeds 100, remove the oldest
                if len(post_order) > 100:
                    oldest_post_id = post_order.pop(0)  # Remove from the beginning
                    if oldest_post_id in seen_db:
                        del seen_db[oldest_post_id]
                
                # Update the ordered list in the shelf
                seen_db['__post_order__'] = post_order
                
                # writeback=True ensures changes are automatically synced
                return True
                
    except Exception as e:
        print(f"Error marking post as seen: {e}")
        return False

# Remove the old global database management functions
# keeping this comment for reference of what was removed:
# - get_seen_posts_db()
# - close_seen_posts_db()
# - global _seen_posts_db variable 