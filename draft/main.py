import os
import asyncio
from dotenv import load_dotenv
import discord
from reddit_monitor import fetch_new_submissions
from filter import matches
from db import init_db, is_new, mark_seen
from discord_bot import PenMonitorBot

load_dotenv()

SUBREDDIT = os.getenv("SUBREDDIT_NAME", "Pen_Swap")
INTERVAL = int(os.getenv("CHECK_INTERVAL", 60))
LIMIT = int(os.getenv("FETCH_LIMIT", 25))

async def monitor_loop(bot: PenMonitorBot):
    db = await init_db()
    await bot.wait_until_ready()

    while True:
        try:
            submissions = fetch_new_submissions(SUBREDDIT, limit=LIMIT)
            for post in submissions:
                if matches(post) and await is_new(db, post.id):
                    await mark_seen(db, post.id)
                    await bot.send_listing(
                        title=post.title,
                        url=f"https://reddit.com{post.permalink}",
                        author=post.author.name if post.author else "[deleted]",
                        timestamp=post.created_utc,
                        image_url=post.url if hasattr(post, 'url') else None
                    )
        except Exception as e:
            print(f"Error in monitor loop: {e}")
        await asyncio.sleep(INTERVAL)

async def main():
    intents = discord.Intents.default()
    bot = PenMonitorBot(intents=intents)
    await bot.start(os.getenv("DISCORD_TOKEN"))
    await monitor_loop(bot)

if __name__ == "__main__":
    asyncio.run(main())