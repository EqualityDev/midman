import discord
from discord.ext import commands
import asyncio
from dotenv import load_dotenv
import os

load_dotenv()
TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

async def main():
    async with bot:
        await bot.load_extension("cogs.midman")
        await bot.start(TOKEN)

asyncio.run(main())
