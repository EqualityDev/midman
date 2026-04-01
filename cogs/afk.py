"""
cogs/afk.py — AFK System
!afk [alasan] — set AFK
Kirim pesan = hapus AFK otomatis
Mention user AFK = bot kasih notif
"""
import discord
from discord.ext import commands

class AFK(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.afk_users = {}  # user_id -> {"reason": str, "original_nick": str}

    @commands.command(name="afk")
    async def afk_cmd(self, ctx, *, reason: str = "AFK"):
        user = ctx.author
        if user.id in self.afk_users:
            await ctx.send(f"{user.mention} kamu sudah AFK.", delete_after=5)
            return

        original_nick = user.display_name
        self.afk_users[user.id] = {"reason": reason, "original_nick": original_nick}

        try:
            new_nick = f"[AFK] {original_nick}"
            if len(new_nick) > 32:
                new_nick = new_nick[:32]
            await user.edit(nick=new_nick)
        except Exception:
            pass

        await ctx.message.delete()
        await ctx.send(f"{user.mention} sekarang AFK: **{reason}**", delete_after=5)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if not message.guild:
            return

        # Cek apakah user yang kirim pesan lagi AFK → hapus AFK
        if message.author.id in self.afk_users:
            # Skip kalau pesannya adalah command !afk
            if message.content.strip().startswith("!afk"):
                return

            data = self.afk_users.pop(message.author.id)

            try:
                await message.author.edit(nick=data["original_nick"] or None)
            except Exception:
                pass

            await message.channel.send(
                f"Selamat datang kembali {message.author.mention}! Status AFK kamu dihapus.",
                delete_after=5
            )

        # Cek mention ke user yang AFK
        if message.mentions:
            notified = set()
            for mentioned in message.mentions:
                # FIX: skip bot & skip yang sudah dinotif
                if mentioned.bot:
                    continue
                if mentioned.id in self.afk_users and mentioned.id not in notified:
                    data = self.afk_users[mentioned.id]
                    await message.channel.send(
                        f"{message.author.mention}, {mentioned.display_name}** sedang AFK: **{data['reason']}**",
                        delete_after=10
                    )
                    notified.add(mentioned.id)


async def setup(bot):
    await bot.add_cog(AFK(bot))
    print("Cog AFK siap.")
