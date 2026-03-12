import discord

from discord.ext import commands

import asyncio

from dotenv import load_dotenv

import os

import re



load_dotenv()

TOKEN = os.getenv("TOKEN")

ERROR_LOG_CHANNEL_ID = int(os.getenv("ERROR_LOG_CHANNEL_ID", 0))

BOT_DIR = os.path.dirname(os.path.abspath(__file__))



intents = discord.Intents.default()

intents.message_content = True

intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)



@bot.event

async def on_ready():

    print(f"[BOT] Login sebagai {bot.user}")

    await asyncio.sleep(8)

    try:
        from utils.config import GUILD_ID
        guild = discord.Object(id=GUILD_ID)
        # Sync ke guild spesifik dulu
        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)
        print(f"[BOT] Synced {len(synced)} slash command(s) to guild {GUILD_ID}")
        # Hapus global commands (biar tidak dobel)
        bot.tree.clear_commands(guild=None)
        await bot.tree.sync()
    except Exception as e:
        print(f"[BOT] Sync error: {e}")

    if not ERROR_LOG_CHANNEL_ID:

        return

    ch = bot.get_channel(ERROR_LOG_CHANNEL_ID)

    if not ch:

        return

    # Baca URL dari cloudflared.log

    cf_url = None

    cf_log = os.path.join(BOT_DIR, "cloudflared.log")

    if os.path.exists(cf_log):

        try:

            with open(cf_log, "r", errors="ignore") as f:

                matches = re.findall(r'https://\S+trycloudflare\.com', f.read())

                if matches:

                    cf_url = matches[-1]

        except Exception:

            pass

    if cf_url:

        embed = discord.Embed(

            title="🌐 Admin Panel Online Password Cellyn123",

            description=f"Admin panel dapat diakses di:\n**{cf_url}**",

            color=0x7c6aff

        )

        embed.set_footer(text="URL ini berubah setiap bot restart.")

    else:

        embed = discord.Embed(

            title="⚠️ Admin Panel",

            description="Bot online tapi URL Cloudflare Tunnel tidak ditemukan.\nCek `cloudflared.log` di server.",

            color=0xFFA500

        )

    await ch.send(embed=embed)



async def main():

    async with bot:

        await bot.load_extension("cogs.midman")

        await bot.load_extension("cogs.vilog")

        await bot.load_extension("cogs.selfroles")

        await bot.load_extension("cogs.robux")

        await bot.load_extension("cogs.ml")

        await bot.load_extension("cogs.nickname_enforcer")

        await bot.load_extension("cogs.jualbeli")

        await bot.load_extension("cogs.ai_chat")
        await bot.load_extension("cogs.testimoni")
        await bot.load_extension("cogs.giveaway")
        await bot.load_extension("cogs.welcome")
        await bot.load_extension("cogs.broadcast")
        await bot.load_extension("cogs.auto_react")
        await bot.load_extension("cogs.server_stats")
        await bot.load_extension("cogs.lainnya")
        await bot.load_extension("cogs.scaset")
        await bot.load_extension("cogs.orders")

        await bot.start(TOKEN)



asyncio.run(main())

