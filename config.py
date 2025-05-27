import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def validate_config():
    """
    Validate all required configuration and exit if critical config is missing.
    Returns True if all validation passes.
    """
    errors = []
    warnings = []
    
    # Validate Discord configuration
    discord_token = os.getenv('DISCORD_TOKEN')
    if not discord_token:
        errors.append("DISCORD_TOKEN is required")
    elif len(discord_token.strip()) < 50:  # Discord tokens are typically ~70 characters
        errors.append("DISCORD_TOKEN appears to be invalid (too short)")
    
    # Validate Discord Channel ID
    channel_id_str = os.getenv('DISCORD_CHANNEL_ID')
    if not channel_id_str:
        errors.append("DISCORD_CHANNEL_ID is required")
    else:
        try:
            channel_id = int(channel_id_str)
            if channel_id <= 0:
                errors.append("DISCORD_CHANNEL_ID must be a positive integer")
        except ValueError:
            errors.append(f"DISCORD_CHANNEL_ID must be a valid integer, got: {channel_id_str}")
    
    # Validate Reddit configuration
    reddit_client_id = os.getenv('REDDIT_CLIENT_ID')
    if not reddit_client_id:
        errors.append("REDDIT_CLIENT_ID is required")
    elif len(reddit_client_id.strip()) < 10:
        errors.append("REDDIT_CLIENT_ID appears to be invalid (too short)")
    
    reddit_client_secret = os.getenv('REDDIT_CLIENT_SECRET')
    if not reddit_client_secret:
        errors.append("REDDIT_CLIENT_SECRET is required")
    elif len(reddit_client_secret.strip()) < 20:
        errors.append("REDDIT_CLIENT_SECRET appears to be invalid (too short)")
    
    # Validate optional configurations with warnings
    interval_str = os.getenv('INTERVAL', '60')
    try:
        interval = int(interval_str)
        if interval < 30:
            warnings.append(f"INTERVAL={interval} is very low, may hit rate limits")
        elif interval > 3600:
            warnings.append(f"INTERVAL={interval} is very high, may miss posts")
    except ValueError:
        errors.append(f"INTERVAL must be a valid integer, got: {interval_str}")
    
    # Print results
    if warnings:
        print("⚠️  Configuration Warnings:")
        for warning in warnings:
            print(f"   - {warning}")
        print()
    
    if errors:
        print("❌ Configuration Errors:")
        for error in errors:
            print(f"   - {error}")
        print("\nPlease check your .env file or environment variables.")
        print("Required variables: DISCORD_TOKEN, DISCORD_CHANNEL_ID, REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET")
        return False
    
    return True

# Validate configuration on import
config_valid = validate_config()

if not config_valid:
    print("❌ Critical configuration errors found. Exiting.")
    sys.exit(1)

# Discord configuration (validated above)
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID'))

# Reddit configuration (validated above)
REDDIT_CLIENT_ID = os.getenv('REDDIT_CLIENT_ID')
REDDIT_CLIENT_SECRET = os.getenv('REDDIT_CLIENT_SECRET')
REDDIT_USER_AGENT = os.getenv('REDDIT_USER_AGENT', 'fountain-pen-bot/1.0')

# Monitoring configuration
INTERVAL = int(os.getenv('INTERVAL', '60'))
SUBREDDIT = os.getenv('SUBREDDIT', 'Pen_Swap')

print(f"✅ Configuration loaded successfully")
print(f"   - Monitoring subreddit: r/{SUBREDDIT}")
print(f"   - Check interval: {INTERVAL} seconds")
print(f"   - Discord channel ID: {CHANNEL_ID}")

# Reddit Configuration
FLAIR_NAME = "WTS-OPEN"
QUERY = f'flair_name:"{FLAIR_NAME}"'

# Database Configuration
SEEN_POSTS_SHELVE_FILE = "seen_posts_shelf"
