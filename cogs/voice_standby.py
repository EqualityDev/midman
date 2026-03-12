import discord
import asyncio
from discord.ext import commands, tasks
from utils.config import GUILD_ID

VOICE_CHANNEL_ID = 1476351297375440957


class SilenceAudio(discord.AudioSource):
    """Audio source yang memutar keheningan agar bot tidak di-disconnect."""
    def read(self):
        return b'\xf8\xff\xfe'  # Opus silence frame

    def is_opus(self):
        return True


class VoiceStandbyCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.voice_client = None
        self.reconnect_loop.start()
        print("Cog VoiceStandby siap.")

    def cog_unload(self):
        self.reconnect_loop.cancel()
        if self.voice_client:
            asyncio.create_task(self.voice_client.disconnect(force=True))

    @tasks.loop(seconds=20)
    async def reconnect_loop(self):
        try:
            guild = self.bot.get_guild(GUILD_ID)
            if not guild:
                return

            channel = guild.get_channel(VOICE_CHANNEL_ID)
            if not channel:
                print("[VOICE] Channel tidak ditemukan.")
                return

            # Jika sudah connect dan masih connected
            if self.voice_client and self.voice_client.is_connected():
                # Pastikan silence tetap diputar
                if not self.voice_client.is_playing():
                    self.voice_client.play(SilenceAudio(), after=None)
                return

            # Reconnect
            if self.voice_client:
                try:
                    await self.voice_client.disconnect(force=True)
                except Exception:
                    pass

            self.voice_client = await channel.connect(self_deaf=True, self_mute=True)
            self.voice_client.play(SilenceAudio(), after=None)
            print(f"[VOICE] Terhubung ke '{channel.name}'")

        except Exception as e:
            print(f"[VOICE] Error: {e}")

    @reconnect_loop.before_loop
    async def before_reconnect(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(5)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Reconnect segera jika bot di-disconnect."""
        if member.id != self.bot.user.id:
            return
        if before.channel and not after.channel:
            print("[VOICE] Bot di-disconnect, reconnecting...")
            self.voice_client = None
            await asyncio.sleep(2)
            await self.reconnect_loop()


async def setup(bot: commands.Bot):
    await bot.add_cog(VoiceStandbyCog(bot))
