import asyncio
import datetime
import discord
from discord.ext import commands, tasks
from utils.config import (
    ADMIN_ROLE_ID, LOG_CHANNEL_ID, STORE_NAME,
    TICKET_CATEGORY_ID, TRANSCRIPT_CHANNEL_ID
)
from utils.db import get_conn
from utils.counter import next_ticket_number
from utils.transcript import generate as generate_transcript

THUMBNAIL = "https://i.imgur.com/CWtUCzj.png"
CATALOG_CHANNEL_ID = 1476349829113315489
COLOR_LAINNYA = 0x5865F2  # Discord blurple

# ── PRODUK DEFAULT ─────────────────────────────────────────────────────────────
DEFAULT_PRODUCTS = [
    # Cloud Phone
    {"id": 1,  "category": "CLOUD PHONE", "name": "REDFINGER VIP 7DAY",   "harga": 20500},
    {"id": 2,  "category": "CLOUD PHONE", "name": "REDFINGER KVIP 7DAY",  "harga": 37500},
    {"id": 3,  "category": "CLOUD PHONE", "name": "REDFINGER SVIP 7DAY",  "harga": 42000},
    {"id": 4,  "category": "CLOUD PHONE", "name": "REDFINGER XVIP 7DAY",  "harga": 102000},
    {"id": 5,  "category": "CLOUD PHONE", "name": "REDFINGER VIP 30DAY",  "harga": 62000},
    {"id": 6,  "category": "CLOUD PHONE", "name": "REDFINGER KVIP 30DAY", "harga": 95500},
    {"id": 7,  "category": "CLOUD PHONE", "name": "REDFINGER SVIP 30DAY", "harga": 102000},
    {"id": 8,  "category": "CLOUD PHONE", "name": "REDFINGER XVIP 30DAY", "harga": 318000},
    # Nitro
    {"id": 9,  "category": "DISCORD NITRO", "name": "NITRO BOOST 1 MONTH", "harga": 25000},
    {"id": 10, "category": "DISCORD NITRO", "name": "NITRO BOOST 3 MONTH", "harga": 50000},
]


# ── DATABASE ───────────────────────────────────────────────────────────────────
def _init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS lainnya_products (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            name     TEXT NOT NULL,
            harga    INTEGER NOT NULL,
            active   INTEGER DEFAULT 1
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS lainnya_tickets (
            channel_id    INTEGER PRIMARY KEY,
            user_id       INTEGER,
            item_id       INTEGER,
            item_name     TEXT,
            category      TEXT,
            harga         INTEGER,
            payment_method TEXT,
            admin_id      INTEGER,
            opened_at     TEXT,
            warned        INTEGER DEFAULT 0,
            warn_message_id INTEGER,
            last_activity TEXT
        )
    ''')
    # Seed produk default jika tabel kosong
    c.execute("SELECT COUNT(*) as cnt FROM lainnya_products")
    if c.fetchone()["cnt"] == 0:
        for p in DEFAULT_PRODUCTS:
            c.execute(
                "INSERT INTO lainnya_products (id, category, name, harga, active) VALUES (?,?,?,?,1)",
                (p["id"], p["category"], p["name"], p["harga"])
            )
    conn.commit()
    conn.close()


def load_lainnya_products():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, category, name, harga FROM lainnya_products WHERE active=1 ORDER BY category, id")
    rows = c.fetchall()
    conn.close()
    return [{"id": r["id"], "category": r["category"], "name": r["name"], "harga": r["harga"]} for r in rows]


def save_lainnya_ticket(ticket: dict):
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO lainnya_tickets
        (channel_id, user_id, item_id, item_name, category, harga, payment_method,
         admin_id, opened_at, warned, warn_message_id, last_activity)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    ''', (
        ticket["channel_id"], ticket["user_id"], ticket.get("item_id"),
        ticket.get("item_name"), ticket.get("category"), ticket.get("harga"),
        ticket.get("payment_method"), ticket.get("admin_id"),
        ticket.get("opened_at"), ticket.get("warned", 0),
        ticket.get("warn_message_id"), ticket.get("last_activity"),
    ))
    conn.commit()
    conn.close()


def delete_lainnya_ticket(channel_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM lainnya_tickets WHERE channel_id=?", (channel_id,))
    conn.commit()
    conn.close()


def load_lainnya_tickets():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM lainnya_tickets")
    rows = c.fetchall()
    conn.close()
    return {row["channel_id"]: dict(row) for row in rows}


# ── CATALOG EMBED & VIEW ───────────────────────────────────────────────────────
def build_catalog_embed(products):
    embed = discord.Embed(
        title=f"CELLYN STORE — {STORE_NAME}",
        description=(
            "Tersedia layanan Cloud Phone, Discord Nitro, dan lainnya.\n"
            "Klik tombol kategori di bawah untuk melihat produk."
        ),
        color=COLOR_LAINNYA,
    )
    categories = {}
    for p in products:
        categories.setdefault(p["category"], []).append(p)

    for cat, items in categories.items():
        value = "\n".join(f"• {p['name']} — **Rp {p['harga']:,}**" for p in items)
        embed.add_field(name=cat, value=value, inline=False)

    embed.add_field(
        name="Pembayaran",
        value="QRIS • DANA • Bank Transfer",
        inline=False
    )
    embed.set_thumbnail(url=THUMBNAIL)
    embed.set_footer(text=f"{STORE_NAME} • Klik tombol untuk order")
    return embed


class CategoryButton(discord.ui.Button):
    def __init__(self, category, products):
        super().__init__(
            label=category,
            style=discord.ButtonStyle.primary,
            custom_id=f"lainnya_cat_{category.replace(' ', '_')}"
        )
        self.category = category
        self.products = products

    async def callback(self, interaction: discord.Interaction):
        options = [
            discord.SelectOption(
                label=p["name"],
                description=f"Rp {p['harga']:,}",
                value=str(p["id"])
            ) for p in self.products
        ]
        view = discord.ui.View(timeout=60)
        view.add_item(ItemSelect(options, self.category))
        await interaction.response.send_message(
            f"Pilih item **{self.category}**:",
            view=view,
            ephemeral=True
        )


class CatalogView(discord.ui.View):
    def __init__(self, products):
        super().__init__(timeout=None)
        categories = {}
        for p in products:
            categories.setdefault(p["category"], []).append(p)
        for cat, items in categories.items():
            self.add_item(CategoryButton(cat, items))


class ItemSelect(discord.ui.Select):
    def __init__(self, options, category):
        super().__init__(
            placeholder=f"Pilih item {category}...",
            options=options,
            custom_id=f"lainnya_select_{category.replace(' ', '_')}"
        )
        self.category = category

    async def callback(self, interaction: discord.Interaction):
        item_id = int(self.values[0])
        products = load_lainnya_products()
        item = next((p for p in products if p["id"] == item_id), None)
        if not item:
            await interaction.response.send_message("Item tidak ditemukan!", ephemeral=True)
            return

        guild = interaction.guild
        member = interaction.user
        cog = interaction.client.cogs.get("LainnyaStore")

        # Cek tiket aktif
        for ch_id, t in cog.active_tickets.items():
            if t["user_id"] == member.id:
                existing = guild.get_channel(ch_id)
                if existing:
                    await interaction.response.send_message(
                        f"Kamu masih punya tiket aktif di {existing.mention}!",
                        ephemeral=True
                    )
                    return

        await interaction.response.defer(ephemeral=True)

        cat_channel = guild.get_channel(TICKET_CATEGORY_ID)
        admin_role = guild.get_role(ADMIN_ROLE_ID)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        if admin_role:
            overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel_name = f"order-{member.name}"
        channel = await guild.create_text_channel(
            name=channel_name,
            category=cat_channel,
            overwrites=overwrites,
        )

        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        ticket = {
            "channel_id": channel.id,
            "user_id": member.id,
            "item_id": item["id"],
            "item_name": item["name"],
            "category": item["category"],
            "harga": item["harga"],
            "payment_method": None,
            "admin_id": None,
            "opened_at": now,
            "last_activity": now,
            "warned": 0,
            "warn_message_id": None,
        }
        cog.active_tickets[channel.id] = ticket
        save_lainnya_ticket(ticket)

        embed = discord.Embed(
            title=f"ORDER {item['category']} — {STORE_NAME}",
            color=COLOR_LAINNYA,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.add_field(name="Member", value=member.mention, inline=True)
        embed.add_field(name="Item", value=item["name"], inline=True)
        embed.add_field(name="Harga", value=f"Rp {item['harga']:,}", inline=True)
        embed.add_field(
            name="Cara Bayar",
            value="Ketik **1** — QRIS  |  **2** — DANA  |  **3** — Bank Transfer",
            inline=False
        )
        embed.add_field(
            name="Catatan",
            value="Setelah pembayaran dikonfirmasi, admin akan memproses pesanan kamu.",
            inline=False
        )
        embed.set_thumbnail(url=THUMBNAIL)
        embed.set_footer(text=STORE_NAME)

        admin_mention = admin_role.mention if admin_role else ""
        await channel.send(
            content=f"{member.mention} {admin_mention}\n"
                    f"Pesanan baru! Segera konfirmasi metode pembayaran.",
            embed=embed
        )
        await interaction.followup.send(
            f"Tiket order kamu dibuat di {channel.mention}!", ephemeral=True
        )


# ── COG ────────────────────────────────────────────────────────────────────────
class LainnyaStore(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_tickets = {}
        _init_db()
        self.auto_close_loop.start()

    def cog_unload(self):
        self.auto_close_loop.cancel()

    async def cog_load(self):
        self.bot.loop.create_task(self._restore_tickets())

    async def _restore_tickets(self):
        await self.bot.wait_until_ready()
        tickets = load_lainnya_tickets()
        for ch_id, t in tickets.items():
            self.active_tickets[ch_id] = t
        print(f"[LainnyaStore] Restored {len(tickets)} tiket")

    @tasks.loop(minutes=30)
    async def auto_close_loop(self):
        await self.bot.wait_until_ready()
        now = datetime.datetime.now(datetime.timezone.utc)
        to_close = []
        for ch_id, ticket in self.active_tickets.items():
            last = datetime.datetime.fromisoformat(ticket["last_activity"])
            if last.tzinfo is None:
                last = last.replace(tzinfo=datetime.timezone.utc)
            diff = (now - last).total_seconds()
            if diff >= 7200:
                to_close.append(ch_id)
            elif diff >= 3600 and not ticket.get("warned"):
                guild = self.bot.guilds[0] if self.bot.guilds else None
                if guild:
                    ch = guild.get_channel(ch_id)
                    if ch:
                        try:
                            msg = await ch.send(
                                "⚠️ Tiket ini akan otomatis ditutup dalam **1 jam** jika tidak ada aktivitas.\n"
                                "Segera konfirmasi pembayaran atau hubungi admin."
                            )
                            ticket["warned"] = 1
                            ticket["warn_message_id"] = msg.id
                            save_lainnya_ticket(ticket)
                        except Exception:
                            pass
        for ch_id in to_close:
            ticket = self.active_tickets.get(ch_id)
            if not ticket:
                continue
            guild = self.bot.guilds[0] if self.bot.guilds else None
            if guild:
                ch = guild.get_channel(ch_id)
                if ch:
                    try:
                        await ch.send("🔒 Tiket ditutup otomatis karena tidak ada aktivitas selama 2 jam.")
                        await asyncio.sleep(3)
                        await ch.delete()
                    except Exception:
                        pass
            delete_lainnya_ticket(ch_id)
            del self.active_tickets[ch_id]

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        ch_id = message.channel.id
        if ch_id not in self.active_tickets:
            return
        ticket = self.active_tickets[ch_id]
        ticket["last_activity"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Pilih metode bayar
        if ticket.get("payment_method") is None and message.content.strip() in ["1", "2", "3"]:
            methods = {"1": "QRIS", "2": "DANA", "3": "Bank Transfer"}
            ticket["payment_method"] = methods[message.content.strip()]
            save_lainnya_ticket(ticket)
            await message.channel.send(
                f"✅ Metode pembayaran: **{ticket['payment_method']}**\n"
                f"Silakan lakukan pembayaran sebesar **Rp {ticket['harga']:,}** dan kirim bukti transfer."
            )

    @commands.command(name="kirimkatalog_lainnya")
    async def kirim_katalog(self, ctx):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        products = load_lainnya_products()
        embed = build_catalog_embed(products)
        view = CatalogView(products)
        ch = ctx.guild.get_channel(CATALOG_CHANNEL_ID)
        if ch:
            await ch.send(embed=embed, view=view)
            await ctx.send("✅ Katalog berhasil dikirim!", delete_after=5)
        else:
            await ctx.send("❌ Channel katalog tidak ditemukan!", delete_after=5)


async def setup(bot: commands.Bot):
    await bot.add_cog(LainnyaStore(bot))
