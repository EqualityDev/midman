import os
import asyncio
import discord
from discord.ext import commands
import aiohttp

RELAY_SOURCE_CHANNEL_ID = int(os.getenv("RELAY_SOURCE_CHANNEL_ID", "0"))
RELAY_WEBHOOK_URL = os.getenv("RELAY_WEBHOOK_URL", "")
RELAY_INCLUDE_BOT = os.getenv("RELAY_INCLUDE_BOT", "1") == "1"
RELAY_ALLOW_MENTIONS = os.getenv("RELAY_ALLOW_MENTIONS", "0") == "1"


def _can_run():
    return RELAY_SOURCE_CHANNEL_ID and RELAY_WEBHOOK_URL


def _embed_dict(embed: discord.Embed):
    try:
        return embed.to_dict()
    except Exception:
        return None


def _allowed_mentions():
    if RELAY_ALLOW_MENTIONS:
        return {"parse": ["users", "roles", "everyone"]}
    return {"parse": []}


class RelayCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._session = None

    async def cog_load(self):
        if not _can_run():
            print("[Relay] Disabled (missing RELAY_SOURCE_CHANNEL_ID or RELAY_WEBHOOK_URL)")
            return
        self._session = aiohttp.ClientSession()
        print(f"[Relay] Enabled for channel {RELAY_SOURCE_CHANNEL_ID}")

    async def cog_unload(self):
        if self._session:
            await self._session.close()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not _can_run():
            return
        if message.channel.id != RELAY_SOURCE_CHANNEL_ID:
            return
        if not RELAY_INCLUDE_BOT and message.author.bot:
            return

        # Build payload
        embeds = [e for e in ([_embed_dict(e) for e in message.embeds] if message.embeds else []) if e]
        content = message.content or ""

        # Forward attachment URLs if present
        if message.attachments:
            urls = "\n".join(a.url for a in message.attachments)
            content = f"{content}\n{urls}".strip()

        payload = {
            "content": content,
            "embeds": embeds[:10],
            "allowed_mentions": _allowed_mentions(),
            "username": message.author.display_name,
            "avatar_url": message.author.display_avatar.url,
        }

        try:
            async with self._session.post(RELAY_WEBHOOK_URL, json=payload, timeout=10) as resp:
                if resp.status >= 400:
                    text = await resp.text()
                    print(f"[Relay] Webhook error {resp.status}: {text[:200]}")
        except Exception as e:
            print(f"[Relay] Failed: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(RelayCog(bot))
    print("Cog Relay siap.")
