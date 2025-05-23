import asyncio
import sys
import os
from pathlib import Path

# One-line path fix that works regardless of where you run it from
sys.path.insert(0, str(Path(__file__).parent.parent))

# Simple imports
from src.clients.reddit_client import initialize_reddit_client
from src.clients.discord_client import run_discord_bot
from src.utils.db_manager import close_seen_posts_db

async def main():
    try:
        # Initialize Reddit instance
        reddit_client = await initialize_reddit_client()
        
        # Run Discord bot
        await run_discord_bot(reddit_client)
    finally:
        # Close database connection
        close_seen_posts_db()

if __name__ == "__main__":
    asyncio.run(main())