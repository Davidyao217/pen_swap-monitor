import asyncio
import time
from clients.reddit_client import initialize_reddit_client
from clients.discord_client import run_discord_bot
from utils.text_utils import get_monitoring_list

async def main():
    """Main function to run both Reddit and Discord clients."""
    start_time = time.time()
    print("Starting Fountain Pen Bot...")
    
    # Print current monitoring status
    monitoring_list = get_monitoring_list()
    print(f"Monitoring {len(monitoring_list)} search terms")
    if monitoring_list:
        print("Current monitoring terms:", monitoring_list[:5], "..." if len(monitoring_list) > 5 else "")
    
    try:
        # Initialize Reddit client
        print("Initializing Reddit client...")
        reddit_client = await initialize_reddit_client()
        reddit_time = time.time()
        print(f"✅ Reddit API connection established in {reddit_time - start_time:.2f}s")
        
        # Run Discord bot with Reddit monitoring
        print("Starting Discord bot (this may take a moment)...")
        await run_discord_bot(reddit_client)
    
    except Exception as e:
        print(f"❌ Error starting bot: {e}")

if __name__ == "__main__":
    asyncio.run(main())