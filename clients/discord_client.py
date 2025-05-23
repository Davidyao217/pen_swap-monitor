import asyncio
import discord
from config import DISCORD_TOKEN, CHANNEL_ID, INTERVAL
from clients.reddit_client import fetch_and_send_new_posts

async def run_discord_bot(reddit_client):
    """Initialize and run the Discord bot."""
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f'Logged in as {client.user}')
        channel = client.get_channel(CHANNEL_ID)
        while True:
            print("Calling fetch_and_send_new_posts")
            await fetch_and_send_new_posts(channel, reddit_client)
            await asyncio.sleep(INTERVAL)

    await client.start(DISCORD_TOKEN) 