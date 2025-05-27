import asyncpraw
import sys
import asyncio
import time
from datetime import datetime
from config import (
    REDDIT_CLIENT_ID,
    REDDIT_CLIENT_SECRET,
    REDDIT_USER_AGENT,
    SUBREDDIT,
    QUERY
)
from utils.text_utils import check_post_for_pen_models, format_discord_message, get_all_monitoring_search_terms
from utils.db_manager import is_post_seen, mark_post_as_seen

# ------------------------------------------------------------------
# Reddit Client Initialization
# ------------------------------------------------------------------

async def initialize_reddit_client():
    """Initialize and return a Reddit API client with validation."""
    try:
        reddit = asyncpraw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent=REDDIT_USER_AGENT
        )
        
        # Test the connection by making a simple API call
        try:
            test_subreddit = await reddit.subreddit(SUBREDDIT)
            # This will fail if credentials are invalid
            await test_subreddit.load()
            print(f"✅ Reddit API connection verified for r/{SUBREDDIT}")
        except Exception as e:
            print(f"❌ Reddit API test failed: {e}")
            print("Please check your Reddit API credentials in the .env file")
            raise
        
        return reddit
    except Exception as e:
        print(f"❌ Failed to initialize Reddit client: {e}")
        raise

async def retry_with_backoff(func, max_retries=3, base_delay=1):
    """
    Retry a function with exponential backoff.
    
    Args:
        func: Async function to retry
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds (will be exponentially increased)
        
    Returns:
        The result of the function call
        
    Raises:
        The last exception if all retries fail
    """
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return await func()
        except Exception as e:
            last_exception = e
            
            if attempt == max_retries:
                # Last attempt failed, raise the exception
                break
            
            # Calculate delay with exponential backoff
            delay = base_delay * (2 ** attempt)
            
            # Check if it's a rate limit error
            if "429" in str(e) or "rate limit" in str(e).lower():
                print(f"⚠️ Rate limit hit, waiting {delay * 2} seconds before retry {attempt + 1}/{max_retries}")
                await asyncio.sleep(delay * 2)  # Longer wait for rate limits
            else:
                print(f"⚠️ API error: {e}, retrying in {delay} seconds (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(delay)
    
    raise last_exception

# ------------------------------------------------------------------
# Post Processing Functions
# ------------------------------------------------------------------

async def fetch_and_send_new_posts(channel, reddit):
    """Fetch new posts from Reddit and send matching ones to Discord."""
    print("Fetching new posts")
    
    # Get current monitoring list
    pen_models_to_watch = get_all_monitoring_search_terms()
    if not pen_models_to_watch:
        print("No pens being monitored - skipping Reddit check")
        return
    
    print(f"Monitoring {len(pen_models_to_watch)} search terms")
    
    async def fetch_posts():
        """Inner function for retry mechanism."""
        # Access the subreddit
        subreddit = await reddit.subreddit(SUBREDDIT)
        
        posts_processed = 0
        posts_sent = 0
        
        # Search for posts matching our query
        async for submission in subreddit.search(
            QUERY,
            sort='new',
            limit=10,  # Default limit
            syntax='lucene'
        ):
            posts_processed += 1
            
            # Print separation for logging clarity
            print("\n" + "-" * 100)
            print(f"Processing post {posts_processed}: https://www.reddit.com{submission.permalink}")
            print("-" * 100)

            # Skip already processed posts
            if is_post_seen(submission.id):
                print(f"Skipping already seen post: {submission.id} - {submission.title}")
                continue
            
            # Mark as seen (this will prevent reprocessing even if we fail later)
            if not mark_post_as_seen(submission.id):
                print(f"⚠️ Failed to mark post as seen: {submission.id}")
            else:
                print(f"✅ Marked post as seen: {submission.id}")

            # Combine title and body for analysis
            combined_text = f"{submission.title} {submission.selftext}"
            
            # Check if the post contains any watched pen models
            found_pen_models = check_post_for_pen_models(combined_text, pen_models_to_watch)

            if found_pen_models:
                # If models are found, prepare and send Discord message
                print(f"✅ Found models: {', '.join(found_pen_models)}")
                
                try:
                    message = format_discord_message(
                        submission_title=submission.title,
                        combined_text=combined_text,
                        found_pen_models=found_pen_models,
                        permalink=submission.permalink
                    )
                    
                    await channel.send(message)
                    posts_sent += 1
                    print(f"✅ Sent Discord message for post: {submission.title[:50]}...")
                    
                except Exception as discord_error:
                    print(f"❌ Failed to send Discord message: {discord_error}")
                    # Don't re-raise here - we don't want one Discord failure to stop processing
                    
            else:
                print(f"❌ No watched models found in post: {submission.title}")
        
        print(f"\n📊 Summary: Processed {posts_processed} posts, sent {posts_sent} messages")
        return posts_processed, posts_sent

    try:
        # Use retry mechanism for the entire fetch operation
        await retry_with_backoff(fetch_posts, max_retries=3, base_delay=2)
        
    except Exception as e:
        print(f"❌ Final error fetching posts after retries: {e}")
        # Don't re-raise - we want the monitoring to continue despite failures

async def force_search_recent_posts(reddit, limit: int = 10):
    """
    Force search recent posts without checking seen status.
    Returns list of matching posts with their details.
    """
    print(f"Force searching last {limit} posts")
    
    # Get current monitoring search terms
    pen_models_to_watch = get_all_monitoring_search_terms()
    if not pen_models_to_watch:
        print("No pens being monitored - nothing to search for")
        return []
    
    print(f"Searching for {len(pen_models_to_watch)} search terms")
    
    async def search_posts():
        """Inner function for retry mechanism."""
        found_posts = []
        
        # Access the subreddit
        subreddit = await reddit.subreddit(SUBREDDIT)
        
        # Search for posts matching our query
        post_count = 0
        async for submission in subreddit.search(
            QUERY,
            sort='new',
            limit=limit,
            syntax='lucene'
        ):
            post_count += 1
            print(f"Processing post {post_count}/{limit}: {submission.title[:50]}...")

            # Mark as seen for stats tracking
            if not is_post_seen(submission.id):
                if mark_post_as_seen(submission.id):
                    print(f"✅ Marked post as seen: {submission.id}")
                else:
                    print(f"⚠️ Failed to mark post as seen: {submission.id}")

            # Combine title and body for analysis
            combined_text = f"{submission.title} {submission.selftext}"
            
            # Check if the post contains any watched pen models
            found_pen_models = check_post_for_pen_models(combined_text, pen_models_to_watch)

            if found_pen_models:
                print(f"✅ Found models: {', '.join(found_pen_models)}")
                
                # Store post details
                found_posts.append({
                    'submission': submission,
                    'found_models': found_pen_models,
                    'combined_text': combined_text
                })
            else:
                print(f"❌ No matches in: {submission.title[:30]}...")

        print(f"Force search complete: {len(found_posts)} matching posts found")
        return found_posts
    
    try:
        # Use retry mechanism for the search operation
        return await retry_with_backoff(search_posts, max_retries=3, base_delay=2)
        
    except Exception as e:
        print(f"❌ Error in force search after retries: {e}")
        return []  # Return empty list on failure 