import discord
import datetime
from discord.ext import commands
from utils.config import ADMIN_ROLE_ID, ROBUX_CATALOG_CHANNEL_ID, LOG_CHANNEL_ID, STORE_NAME, TICKET_CATEGORY_ID
from utils.db import get_conn

THUMBNAIL = "https://i.imgur.com/CWtUCzj.png"

PRODUCTS = [
    # GAMEPASS
    {"id": 1,  "category": "GAMEPASS", "name": "VIP + LUCK",                "robux": 445},
    {"id": 2,  "category": "GAMEPASS", "name": "MUTATION",                   "robux": 295},
    {"id": 3,  "category": "GAMEPASS", "name": "ADVANCED LUCK",              "robux": 525},
    {"id": 4,  "category": "GAMEPASS", "name": "EXTRA LUCK",                 "robux": 245},
    {"id": 5,  "category": "GAMEPASS", "name": "DOUBLE EXP",                 "robux": 195},
    {"id": 6,  "category": "GAMEPASS", "name": "SELL ANYWHERE",              "robux": 315},
    {"id": 7,  "category": "GAMEPASS", "name": "SMALL LUCK",                 "robux": 50},
    {"id": 8,  "category": "GAMEPASS", "name": "HYPERBOATPACK",              "robux": 999},
    # CRATE
    {"id": 9,  "category": "CRATE",    "name": "VALENTINE CRATE 1X",         "robux": 249},
    {"id": 10, "category": "CRATE",    "name": "VALENTINE CRATE 5X",         "robux": 1245},
    {"id": 11, "category": "CRATE",    "name": "ELDERWOOD CRATE 1X",         "robux": 99},
    {"id": 12, "category": "CRATE",    "name": "ELDERWOOD CRATE 5X",         "robux": 495},
    # BOOST
    {"id": 13, "category": "BOOST",    "name": "BOOST SERVER LUCK X2",       "robux": 99},
    {"id": 14, "category": "BOOST",    "name": "BOOST SERVER LUCK X8 3 JAM", "robux": 800},
    {"id": 15, "category": "BOOST",    "name": "BOOST X8 3 JAM",             "robux": 300},
    {"id": 16, "category": "BOOST",    "name": "BOOST X8 6 JAM",             "robux": 1300},
    {"id": 17, "category": "BOOST",    "name": "BOOST X8 12 JAM",            "robux": 1890},
    {"id": 18, "category": "BOOST",    "name": "BOOST X8 24 JAM",            "robux": 3100},
    # LIMITED
    {"id": 19, "category": "LIMITED",  "name": "DARK MATTER SCYTHE",         "robux": 999},
    {"id": 20, "category": "LIMITED",  "name": "KITTY GUITAR",               "robux": 899},
    {"id": 21, "category": "LIMITED",  "name": "VOIDCRAFT BOAT",             "robux": 549},
]

def get_rate():
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT rate FROM robux_rate WHERE id = 1')
    row = c.fetchone()
    conn.close()
    return row['rate'] if row else 0

def set_rate(rate):
    conn = get_conn()
    c = conn.cursor()
    c.execute('UPDATE robux_rate SET rate = ? WHERE id = 1', (rate,))
    conn.commit()
    conn.close()

def harga(robux, rate):
    if rate == 0:
        return "Belum diset"
    total = robux * rate
    return f"Rp {total:,}"

def build_catalog_embed(rate):
    rate_str = f"Rp {rate:,}/Robux" if rate > 0 else "Belum diset"
    embed = discord.Embed(
        title=f"ROBUX STORE — {STORE_NAME}",
        description=(
            f"Harga dihitung otomatis berdasarkan rate Robux terkini.\n"
            f"Rate saat ini: **{rate_str}**\n\n"
            f"Buka tiket dengan klik tombol di bawah."
        ),
        color=0xE91E63,
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )

    categories = ["GAMEPASS", "CRATE", "BOOST", "LIMITED"]
    labels = {
        "GAMEPASS": "GAMEPASS",
        "CRATE":    "CRATE",
        "BOOST":    "BOOST",
        "LIMITED":  "LIMITED ITEM",
    }

    for cat in categories:
        items = [p for p in PRODUCTS if p["category"] == cat]
        value = ""
        for item in items:
            harga_str = harga(item["robux"], rate)
            value += f"`ID:{item['id']:02d}` {item['name']} ({item['robux']} Robux) — **{harga_str}**\n"
        embed.add_field(name=labels[cat], value=value, inline=False)

    embed.set_thumbnail(url=THUMBNAIL)
    embed.set_footer(text=f"{STORE_NAME} • Harga dapat berubah sewaktu-waktu")
    return embed

class RobuxStore(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.catalog_message_id = None

    async def refresh_catalog(self):
        guild = self.bot.guilds[0] if self.bot.guilds else None
        if not guild:
            return
        ch = guild.get_channel(ROBUX_CATALOG_CHANNEL_ID)
        if not ch:
            return
        rate = get_rate()
        embed = build_catalog_embed(rate)
        if self.catalog_message_id:
            try:
                msg = await ch.fetch_message(self.catalog_message_id)
                await msg.edit(embed=embed)
                return
            except Exception:
                pass
        async for msg in ch.history(limit=20):
            if msg.author == self.bot.user:
                try:
                    await msg.delete()
                except Exception:
                    pass
        sent = await ch.send(embed=embed)
        self.catalog_message_id = sent.id

    @commands.command(name="rate")
    async def set_rate_cmd(self, ctx, *, nilai: str = None):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        await ctx.message.delete()
        if not nilai:
            rate = get_rate()
            rate_str = f"Rp {rate:,}/Robux" if rate > 0 else "Belum diset"
            await ctx.send(f"Rate saat ini: **{rate_str}**", delete_after=10)
            return
        try:
            rate = int(nilai.replace(".", "").replace(",", ""))
        except ValueError:
            await ctx.send("Format salah! Contoh: `!rate 90`", delete_after=5)
            return
        set_rate(rate)
        await ctx.send(f"Rate diupdate: **Rp {rate:,}/Robux**. Catalog sedang diperbarui...", delete_after=5)
        await self.refresh_catalog()

    @commands.command(name="catalog")
    async def catalog_cmd(self, ctx):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        await ctx.message.delete()
        await self.refresh_catalog()
        await ctx.send("Catalog dikirim!", delete_after=5)

async def setup(bot):
    await bot.add_cog(RobuxStore(bot))
    print("Cog RobuxStore siap.")
