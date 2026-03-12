import discord
import asyncio
from discord.ext import commands, tasks
from utils.config import GUILD_ID

VOICE_CHANNEL_ID = 1476351297375440957


class SilenceAudio(discord.AudioSource):
    def read(self):
        return b'\xf8\xff\xfe'

    def is_opus(self):
        return True


class VoiceStandbyCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._reconnecting = False
        self.reconnect_loop.start()
        print("Cog VoiceStandby siap.")

    def cog_unload(self):
        self.reconnect_loop.cancel()

    def _get_voice_client(self):
        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            return None
        return guild.voice_client

    @tasks.loop(seconds=30)
    async def reconnect_loop(self):
        if self._reconnecting:
            return
        try:
            self._reconnecting = True
            guild = self.bot.get_guild(GUILD_ID)
            if not guild:
                return

            channel = guild.get_channel(VOICE_CHANNEL_ID)
            if not channel:
                print("[VOICE] Channel tidak ditemukan.")
                return

            vc = guild.voice_client

            # Sudah connect di channel yang benar
            if vc and vc.is_connected() and vc.channel.id == VOICE_CHANNEL_ID:
                if not vc.is_playing():
                    vc.play(SilenceAudio(), after=None)
                return

            # Disconnect dulu kalau di channel lain
            if vc and vc.is_connected():
                await vc.disconnect(force=True)
                await asyncio.sleep(1)

            vc = await channel.connect(self_deaf=True, self_mute=True)
            await asyncio.sleep(1)
            if not vc.is_playing():
                vc.play(SilenceAudio(), after=None)
            print(f"[VOICE] Terhubung ke '{channel.name}'")

        except Exception as e:
            print(f"[VOICE] Error: {e}")
        finally:
            self._reconnecting = False

    @reconnect_loop.before_loop
    async def before_reconnect(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(5)


async def setup(bot: commands.Bot):
    await bot.add_cog(VoiceStandbyCog(bot))
