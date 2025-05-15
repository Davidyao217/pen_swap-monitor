import os
import asyncio
from dotenv import load_dotenv
import discord
import praw

load_dotenv()

SUBREDDIT = os.getenv("SUBREDDIT_NAME", "Pen_Swap")
# INTERVAL = int(os.getenv("CHECK_INTERVAL", 60))
INTERVAL = 10
# LIMIT = int(os.getenv("FETCH_LIMIT", 25))
LIMIT = 10
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))

# Initialize Reddit instance
reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent=os.getenv("REDDIT_USER_AGENT")
)

async def fetch_and_send_new_posts(channel):
    print("Fetching new posts")
    subreddit = reddit.subreddit(SUBREDDIT)
    async for submission in subreddit.new(limit=LIMIT):
        print(submission.title)
        await channel.send(submission.title)

async def main():
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f'Logged in as {client.user}')
        channel = client.get_channel(CHANNEL_ID)
        while True:
            print("Calling fetch_and_send_new_posts")
            await fetch_and_send_new_posts(channel)
            await asyncio.sleep(10)

    await client.start(DISCORD_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())