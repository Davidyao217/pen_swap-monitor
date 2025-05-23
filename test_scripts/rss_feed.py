import os
import asyncio
from dotenv import load_dotenv
import feedparser
import discord

load_dotenv()

# ── Configuration ───────────────────────────────────────
SUBREDDIT     = os.getenv("SUBREDDIT_NAME", "Pen_Swap")
FLAIR_NAME    = os.getenv("FLAIR_NAME", "WTS-OPEN")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 60))  # seconds
DISCORD_TOKEN  = os.getenv("DISCORD_TOKEN")
CHANNEL_ID     = int(os.getenv("DISCORD_CHANNEL_ID"))
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT")
# ── End configuration ───────────────────────────────────

# RSS URL for the subreddit’s “new” feed
RSS_URL = f"https://www.reddit.com/r/{SUBREDDIT}/new/.rss"

async def monitor_feed(channel):
    seen = set()
    print(f"Starting RSS feed monitoring on {RSS_URL}")
    while True:
        print("Fetching new posts")
        # Set a custom User-Agent
        feed = feedparser.parse(RSS_URL, request_headers={'User-Agent': REDDIT_USER_AGENT})
        if feed.status == 403:
            print("Access to the RSS feed is forbidden. Check your User-Agent or consider using Reddit's API.")
        else:
            for entry in reversed(feed.entries):
                # Each entry.tags is a list of dicts with 'term' and 'scheme'
                flair_terms = {
                    tag['term']
                    for tag in entry.get('tags', [])
                    if tag.get('scheme') == 'flair'
                }
                if FLAIR_NAME in flair_terms and entry.id not in seen:
                    print(f"Found new post: {entry.title}")
                    seen.add(entry.id)
                    title = entry.title
                    link  = entry.link
                    await channel.send(f"🔔 **{title}**\n{link}")
        await asyncio.sleep(CHECK_INTERVAL)

async def main():
    intents = discord.Intents.default()
    client  = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f"Logged in as {client.user}")
        channel = client.get_channel(CHANNEL_ID)
        # Start the RSS polling loop in the background
        client.loop.create_task(monitor_feed(channel))

    await client.start(DISCORD_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
