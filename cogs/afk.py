"""
cogs/afk.py — AFK System
!afk [alasan] — set AFK
Kirim pesan = hapus AFK otomatis
Mention user AFK = bot kasih notif
AFK state persistent di SQLite (table: afk_users)
"""
import discord
from discord.ext import commands
from utils.db import get_conn

def init_afk_table():
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS afk_users (
            user_id       INTEGER PRIMARY KEY,
            reason        TEXT DEFAULT 'AFK',
            original_nick TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_afk(user_id: int, reason: str, original_nick: str):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO afk_users (user_id, reason, original_nick) VALUES (?, ?, ?)",
        (user_id, reason, original_nick)
    )
    conn.commit()
    conn.close()

def delete_afk(user_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM afk_users WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def load_all_afk() -> dict:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT user_id, reason, original_nick FROM afk_users")
    rows = c.fetchall()
    conn.close()
    return {row["user_id"]: {"reason": row["reason"], "original_nick": row["original_nick"]} for row in rows}


class AFK(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        init_afk_table()
        self.afk_users = load_all_afk()
        print(f"[AFK] Loaded {len(self.afk_users)} AFK user(s) dari DB.")

    @commands.command(name="afk")
    async def afk_cmd(self, ctx, *, reason: str = "AFK"):
        user = ctx.author
        if user.id in self.afk_users:
            await ctx.send(f"{user.mention} kamu sudah AFK.", delete_after=5)
            return

        original_nick = user.display_name
        self.afk_users[user.id] = {"reason": reason, "original_nick": original_nick}
        save_afk(user.id, reason, original_nick)

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
            delete_afk(message.author.id)

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
                if mentioned.bot:
                    continue
                if mentioned.id in self.afk_users and mentioned.id not in notified:
                    data = self.afk_users[mentioned.id]
                    await message.channel.send(
                        f"{message.author.mention}, **{mentioned.display_name}** sedang AFK: **{data['reason']}**",
                        delete_after=10
                    )
                    notified.add(mentioned.id)


async def setup(bot):
    await bot.add_cog(AFK(bot))
    print("Cog AFK siap.")
