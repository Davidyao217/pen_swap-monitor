import asyncio
from clients.reddit_client import initialize_reddit_client
from clients.discord_client import run_discord_bot
from utils.db_manager import close_seen_posts_db
from config import PEN_MODELS_TO_WATCH
async def main():
    try:
        # Initialize Reddit instance
        # print the models to watch
        print(PEN_MODELS_TO_WATCH)
        reddit_client = await initialize_reddit_client()
        
        # Run Discord bot
        await run_discord_bot(reddit_client)
    finally:
        # Close database connection
        close_seen_posts_db()

if __name__ == "__main__":
    asyncio.run(main())