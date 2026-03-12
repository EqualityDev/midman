import discord
import asyncio
import datetime
from discord.ext import commands, tasks
from utils.config import GUILD_ID

VOICE_CHANNEL_ID = 1477832806871728349


class VoiceStandbyCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.voice_client = None
        self.reconnect_loop.start()
        print("Cog VoiceStandby siap.")

    def cog_unload(self):
        self.reconnect_loop.cancel()
        if self.voice_client:
            asyncio.create_task(self.voice_client.disconnect())

    @tasks.loop(minutes=1)
    async def reconnect_loop(self):
        try:
            guild = self.bot.get_guild(GUILD_ID)
            if not guild:
                return

            channel = guild.get_channel(VOICE_CHANNEL_ID)
            if not channel:
                print("[VOICE] Channel tidak ditemukan.")
                return

            # Sudah connect dan masih connected — tidak perlu apa-apa
            if self.voice_client and self.voice_client.is_connected():
                return

            # Connect atau reconnect
            if self.voice_client:
                try:
                    await self.voice_client.disconnect(force=True)
                except Exception:
                    pass

            self.voice_client = await channel.connect(self_deaf=True, self_mute=True)
            print(f"[VOICE] Terhubung ke '{channel.name}'")

        except Exception as e:
            print(f"[VOICE] Reconnect error: {e}")

    @reconnect_loop.before_loop
    async def before_reconnect(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(5)


async def setup(bot: commands.Bot):
    await bot.add_cog(VoiceStandbyCog(bot))
