import os
import asyncio
from dotenv import load_dotenv
import discord
import asyncpraw

load_dotenv()

SUBREDDIT = os.getenv("SUBREDDIT_NAME", "Pen_Swap")
INTERVAL = int(os.getenv("CHECK_INTERVAL"))
LIMIT = int(os.getenv("LIMIT"))
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))
FLAIR_NAME = os.getenv("FLAIR_NAME")
QUERY      = f'flair_name:"{FLAIR_NAME}"'


async def fetch_and_send_new_posts(channel, reddit):
    print("Fetching new posts")
    try:
        subreddit = await reddit.subreddit(SUBREDDIT)
        async for submission in subreddit.search(
            QUERY,
            sort='new',
            limit=LIMIT,
            syntax='lucene'     # optional, makes sure quotes are honored
        ):
            print(submission.title)
            await channel.send(submission.title)
    except Exception as e:
        print(f"Error fetching posts: {e}")

async def main():
    # Initialize Reddit instance
    reddit = asyncpraw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        user_agent=os.getenv("REDDIT_USER_AGENT")
    )
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f'Logged in as {client.user}')
        channel = client.get_channel(CHANNEL_ID)
        while True:
            print("Calling fetch_and_send_new_posts")
            await fetch_and_send_new_posts(channel, reddit)
            await asyncio.sleep(INTERVAL)

    await client.start(DISCORD_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())