import asyncio
from clients.reddit_client import initialize_reddit_client
from clients.discord_client import run_discord_bot
from utils.text_utils import get_monitoring_list

async def main():
    """Main function to run both Reddit and Discord clients."""
    print("Starting Fountain Pen Bot...")
    
    # Print current monitoring status
    monitoring_list = get_monitoring_list()
    print(f"Monitoring {len(monitoring_list)} search terms")
    if monitoring_list:
        print("Current monitoring terms:", monitoring_list[:5], "..." if len(monitoring_list) > 5 else "")
    
    try:
        # Initialize Reddit client
        reddit_client = await initialize_reddit_client()
        print("✅ Reddit client initialized")
        
        # Run Discord bot with Reddit monitoring
        await run_discord_bot(reddit_client)
    
    except Exception as e:
        print(f"❌ Error starting bot: {e}")

if __name__ == "__main__":
    asyncio.run(main())