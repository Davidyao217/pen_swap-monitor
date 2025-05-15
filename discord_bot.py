import os
import discord
from dotenv import load_dotenv

load_dotenv()

class PenMonitorBot(discord.Client):
    def __init__(self, **options):
        super().__init__(**options)
        self.channel_id = int(os.getenv("DISCORD_CHANNEL_ID"))
        self.ready = False

    async def on_ready(self):
        print(f"Logged in as {self.user}")
        self.ready = True

    async def send_listing(self, title: str, url: str, author: str, timestamp: float, image_url: str = None):
        channel = self.get_channel(self.channel_id)
        if channel:
            embed = discord.Embed(
                title=title,
                url=url,
                timestamp=discord.utils.snowflake_time(discord.utils.time_snowflake())
            )
            embed.set_author(name=author)
            if image_url and image_url.lower().endswith((".jpg", ".png", ".gif")):
                embed.set_image(url=image_url)
            await channel.send(embed=embed)