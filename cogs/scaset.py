import time
import asyncio
import json
import datetime
import discord
from discord.ext import commands, tasks
from utils.config import (
    ADMIN_ROLE_ID, LOG_CHANNEL_ID, STORE_NAME,
    TICKET_CATEGORY_ID, TRANSCRIPT_CHANNEL_ID, GUILD_ID
)
from utils.db import get_conn
from utils.counter import next_ticket_number
from utils.transcript import generate as generate_transcript

THUMBNAIL = "https://i.imgur.com/CWtUCzj.png"
CATALOG_CHANNEL_ID = 1476349829113315489
COLOR_SCASET = 0xF0A500


# ── DATABASE ───────────────────────────────────────────────────────────────────
def _init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS scaset_tickets (
            channel_id      INTEGER PRIMARY KEY,
            user_id         INTEGER,
            payment_method  TEXT,
            items           TEXT DEFAULT '[]',
            admin_id        INTEGER,
            embed_message_id INTEGER,
            opened_at       TEXT,
            warned          INTEGER DEFAULT 0,
            warn_message_id INTEGER,
            last_activity   TEXT
        )
    ''')
    conn.commit()
    conn.close()


def save_scaset_ticket(ticket: dict):
    conn = get_conn()
    c = conn.cursor()
    items_json = json.dumps(ticket.get("items", []), ensure_ascii=False)
    c.execute('''
        INSERT OR REPLACE INTO scaset_tickets
        (channel_id, user_id, payment_method, items, admin_id, embed_message_id,
         opened_at, warned, warn_message_id, last_activity)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    ''', (
        ticket["channel_id"], ticket["user_id"], ticket.get("payment_method"),
        items_json, ticket.get("admin_id"), ticket.get("embed_message_id"),
        ticket.get("opened_at"), ticket.get("warned", 0),
        ticket.get("warn_message_id"), ticket.get("last_activity"),
    ))
    conn.commit()
    conn.close()


def delete_scaset_ticket(channel_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM scaset_tickets WHERE channel_id=?", (channel_id,))
    conn.commit()
    conn.close()


def load_scaset_tickets():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM scaset_tickets")
    rows = c.fetchall()
    conn.close()
    result = {}
    for row in rows:
        t = dict(row)
        t["items"] = json.loads(t.get("items") or "[]")
        result[row["channel_id"]] = t
    return result


def _get_catalog_msg_id():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT value FROM bot_state WHERE key='scaset_catalog_msg_id'")
    row = c.fetchone()
    conn.close()
    return int(row["value"]) if row and row["value"] else None


def _set_catalog_msg_id(msg_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO bot_state (key,value) VALUES ('scaset_catalog_msg_id',?)",
              (str(msg_id),))
    conn.commit()
    conn.close()


# ── EMBED ──────────────────────────────────────────────────────────────────────
def build_ticket_embed(ticket: dict, member, admin=None):
    items = ticket.get("items", [])
    subtotal = sum(i.get("harga", 0) for i in items)
    embed = discord.Embed(
        title=f"SC/ASET GAME — {STORE_NAME}",
        color=COLOR_SCASET,
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    embed.add_field(name="Admin", value=admin.mention if admin else "Menunggu admin...", inline=True)
    embed.add_field(name="Member", value=member.mention if member else str(ticket["user_id"]), inline=True)
    embed.add_field(name="\u200b", value="\u200b", inline=False)
    if items:
        for i, item in enumerate(items, 1):
            embed.add_field(
                name=f"Item {i} — {item['nama']}",
                value=f"Qty: **{item['qty']}**  |  Total: **Rp {item['harga']:,}**",
                inline=False
            )
        embed.add_field(name="Subtotal", value=f"**Rp {subtotal:,}**", inline=False)
    else:
        embed.add_field(name="Item", value="*Belum ada item — admin gunakan `!additem`*", inline=False)
    embed.add_field(
        name="Metode Bayar",
        value=ticket.get("payment_method") or "*Menunggu konfirmasi member...*",
        inline=False
    )
    embed.add_field(
        name="Instruksi",
        value=(
            "**1.** Ketik `1` QRIS · `2` DANA · `3` Bank Transfer\n"
            "**2.** Beritahu admin item yang ingin dibeli\n"
            "Admin akan informasikan stok dan harga."
        ),
        inline=False
    )
    embed.set_footer(text=STORE_NAME)
    return embed


def build_admin_guide_embed():
    embed = discord.Embed(title="📋 Panduan Admin — SC/Aset Game", color=0x2ECC71)
    embed.add_field(
        name="Tambah Item",
        value="`!additem <nama> <qty> <harga_total>`\nContoh: `!additem Batu Evo 3 15000`",
        inline=False
    )
    embed.add_field(
        name="Hapus Item",
        value="`!delitem <nomor>`\nContoh: `!delitem 1`",
        inline=False
    )
    embed.add_field(
        name="Tutup Tiket",
        value="`!done` — tutup tiket sukses\n`!cancel [alasan]` — batalkan tiket",
        inline=False
    )
    embed.set_footer(text="Embed tiket otomatis update setiap perubahan item")
    return embed


# ── CATALOG VIEW (persistent) ──────────────────────────────────────────────────
class ScasetInfoView(discord.ui.View):
    """Info layanan Scaset + tombol Lanjutkan/Batal."""
    def __init__(self):
        super().__init__(timeout=120)

    @discord.ui.button(label="✅ Lanjutkan", style=discord.ButtonStyle.success, custom_id="scaset_info_lanjut")
    async def lanjutkan(self, interaction: discord.Interaction, button: discord.ui.Button):
        await _open_scaset_ticket(interaction)

    @discord.ui.button(label="❌ Batal", style=discord.ButtonStyle.danger, custom_id="scaset_info_batal")
    async def batal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Dibatalkan.", embed=None, view=None)


async def _open_scaset_ticket(interaction: discord.Interaction):
    """Helper: buat channel tiket scaset."""
    guild = interaction.guild
    member = interaction.user
    cog = interaction.client.cogs.get("ScasetStore")

    for ch_id, t in cog.active_tickets.items():
        if t["user_id"] == member.id:
            existing = guild.get_channel(ch_id)
            if existing:
                await interaction.response.edit_message(
                    content=f"Kamu masih punya tiket aktif di {existing.mention}!",
                    embed=None, view=None
                )
                return

    await interaction.response.edit_message(content="Membuat tiket...", embed=None, view=None)

    cat_channel = guild.get_channel(TICKET_CATEGORY_ID)
    admin_role = guild.get_role(ADMIN_ROLE_ID)
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
    }
    if admin_role:
        overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

    channel = await guild.create_text_channel(
        name=f"scaset-{member.name}", category=cat_channel, overwrites=overwrites)

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    ticket = {
        "channel_id": channel.id, "user_id": member.id,
        "payment_method": None, "items": [], "admin_id": None,
        "embed_message_id": None, "opened_at": now, "last_activity": now,
        "warned": 0, "warn_message_id": None,
    }
    cog.active_tickets[channel.id] = ticket
    save_scaset_ticket(ticket)

    embed = build_ticket_embed(ticket, member)
    admin_mention = admin_role.mention if admin_role else ""
    msg = await channel.send(
        content=f"{member.mention} {admin_mention}",
        embed=embed
    )
    ticket["embed_message_id"] = msg.id
    save_scaset_ticket(ticket)
    await channel.send(embed=build_admin_guide_embed())
    await interaction.followup.send(f"Tiket kamu dibuat di {channel.mention}!", ephemeral=True)


class ScasetOrderButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="SC TB / ASET GAME",
            style=discord.ButtonStyle.success,
            emoji="🎮",
            custom_id="scaset_order_btn"
        )

    async def callback(self, interaction: discord.Interaction):
        from utils.service_info import get_service_info, build_info_embed
        info = get_service_info("scaset")
        has_info = any([info["description"], info["terms"], info["payment_info"]])
        if has_info:
            embed = build_info_embed("SC TB / Aset Game", info, COLOR_SCASET)
            await interaction.response.send_message(embed=embed, view=ScasetInfoView(), ephemeral=True)
        else:
            guild = interaction.guild
            member = interaction.user
            cog = interaction.client.cogs.get("ScasetStore")

            for ch_id, t in cog.active_tickets.items():
                if t["user_id"] == member.id:
                    existing = guild.get_channel(ch_id)
                    if existing:
                        await interaction.response.send_message(
                            f"Kamu masih punya tiket aktif di {existing.mention}!", ephemeral=True)
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

            channel = await guild.create_text_channel(
                name=f"scaset-{member.name}", category=cat_channel, overwrites=overwrites)

            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            ticket = {
                "channel_id": channel.id, "user_id": member.id,
                "payment_method": None, "items": [], "admin_id": None,
                "embed_message_id": None, "opened_at": now, "last_activity": now,
                "warned": 0, "warn_message_id": None,
            }
            cog.active_tickets[channel.id] = ticket
            save_scaset_ticket(ticket)

            embed = build_ticket_embed(ticket, member)
            admin_mention = admin_role.mention if admin_role else ""
            msg = await channel.send(
                content=f"{member.mention} {admin_mention}",
                embed=embed
            )
            ticket["embed_message_id"] = msg.id
            save_scaset_ticket(ticket)
            await channel.send(embed=build_admin_guide_embed())
            await interaction.followup.send(f"Tiket kamu dibuat di {channel.mention}!", ephemeral=True)


class ScasetCatalogView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ScasetOrderButton())


# ── COG ────────────────────────────────────────────────────────────────────────
class ScasetStore(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_tickets = {}
        self.catalog_message_id = None
        _init_db()
        self.auto_close_loop.start()

    def cog_unload(self):
        self.auto_close_loop.cancel()

    async def cog_load(self):
        self.bot.loop.create_task(self._restore())

    async def _restore(self):
        await self.bot.wait_until_ready()
        self.active_tickets = load_scaset_tickets()
        self.catalog_message_id = _get_catalog_msg_id()
        print(f"[ScasetStore] Restored {len(self.active_tickets)} tiket, catalog_msg={self.catalog_message_id}")

    async def refresh_catalog(self):
        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            return
        ch = guild.get_channel(CATALOG_CHANNEL_ID)
        if not ch:
            return
        embed = discord.Embed(
            title=f"SC TB / ASET GAME — {STORE_NAME}",
            description=(
                "Jual beli item, aset game, SC TB, dan kebutuhan quest/misi/experience.\n\n"
                "**Harga:** Rp 300 – Rp 700 / item *(tergantung jenis item)*\n\n"
                "Klik tombol di bawah untuk membuka tiket order."
            ),
            color=COLOR_SCASET
        )
        embed.add_field(name="Pembayaran", value="QRIS • DANA • Bank Transfer", inline=False)
        embed.set_footer(text=f"{STORE_NAME} • Stock terbatas")
        view = ScasetCatalogView()
        if self.catalog_message_id:
            try:
                msg = await ch.fetch_message(self.catalog_message_id)
                await msg.edit(embed=embed, view=view)
                return
            except Exception:
                pass
        # Hanya hapus embed milik cog ini, bukan semua pesan bot
        if self.catalog_message_id:
            try:
                old_msg = await ch.fetch_message(self.catalog_message_id)
                await old_msg.delete()
            except Exception:
                pass
        sent = await ch.send(embed=embed, view=view)
        self.catalog_message_id = sent.id
        _set_catalog_msg_id(sent.id)

    @tasks.loop(minutes=30)
    async def auto_close_loop(self):
        await self.bot.wait_until_ready()
        now = datetime.datetime.now(datetime.timezone.utc)
        to_close = []
        for ch_id, ticket in list(self.active_tickets.items()):
            last = datetime.datetime.fromisoformat(ticket["last_activity"])
            if last.tzinfo is None:
                last = last.replace(tzinfo=datetime.timezone.utc)
            diff = (now - last).total_seconds()
            if diff >= 7200:
                to_close.append(ch_id)
            elif diff >= 3600 and not ticket.get("warned"):
                guild = self.bot.get_guild(GUILD_ID)
                if guild:
                    ch = guild.get_channel(ch_id)
                    if ch:
                        try:
                            user = guild.get_member(ticket["user_id"])
                            warn_embed = discord.Embed(title="PERINGATAN TIKET", color=0xFFA500)
                            warn_embed.add_field(name="\u200b", value=(
                                "Tiket tidak ada aktivitas selama **1 jam**.\n\n"
                                "Segera selesaikan atau hubungi admin.\n\n"
                                "Tiket akan otomatis ditutup dalam **1 jam lagi** (<t:" + str(int(time.time()) + 3600) + ":R>)."
                            ), inline=False)
                            warn_embed.set_footer(text=STORE_NAME)
                            msg = await ch.send(content=user.mention if user else "", embed=warn_embed)
                            ticket["warned"] = 1
                            ticket["warn_message_id"] = msg.id
                            save_scaset_ticket(ticket)
                        except Exception:
                            pass
        for ch_id in to_close:
            ticket = self.active_tickets.pop(ch_id, None)
            if not ticket:
                continue
            guild = self.bot.get_guild(GUILD_ID)
            if guild:
                ch = guild.get_channel(ch_id)
                delete_scaset_ticket(ch_id)
                if ch:
                    try:
                        await ch.send("🔒 Tiket ditutup otomatis karena tidak ada aktivitas selama 2 jam.")
                        await asyncio.sleep(3)
                        await ch.delete()
                    except Exception:
                        pass

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        ch_id = message.channel.id
        if ch_id not in self.active_tickets:
            return
        ticket = self.active_tickets[ch_id]
        ticket["last_activity"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save_scaset_ticket(ticket)
        if ticket.get("payment_method") is None and message.content.strip() in ["1", "2", "3"]:
            methods = {"1": "QRIS", "2": "DANA", "3": "Bank Transfer"}
            ticket["payment_method"] = methods[message.content.strip()]
            save_scaset_ticket(ticket)
            await self._update_embed(message.channel, ticket)
            await message.channel.send(
                f"✅ Metode pembayaran: **{ticket['payment_method']}**\n"
                f"Beritahu admin item apa yang ingin kamu beli."
            )

    async def _update_embed(self, channel, ticket):
        try:
            guild = channel.guild
            member = guild.get_member(ticket["user_id"])
            admin = guild.get_member(ticket["admin_id"]) if ticket.get("admin_id") else None
            embed = build_ticket_embed(ticket, member, admin)
            if ticket.get("embed_message_id"):
                msg = await channel.fetch_message(ticket["embed_message_id"])
                await msg.edit(embed=embed)
        except Exception as e:
            print(f"[ScasetStore] Update embed error: {e}")

    @commands.command(name="additem")
    async def add_item(self, ctx, *, args: str = None):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        ch_id = ctx.channel.id
        if ch_id not in self.active_tickets:
            return
        # Format: !additem <nama multi kata> <qty> <harga>
        # Parse 2 angka terakhir sebagai qty dan harga, sisanya adalah nama
        if not args:
            await ctx.send(
                "Format: `!additem <nama> <qty> <harga_total>`\nContoh: `!additem Batu Evo 3 15000`",
                delete_after=8
            )
            return
        parts = args.strip().split()
        if len(parts) < 3:
            await ctx.send(
                "Format: `!additem <nama> <qty> <harga_total>`\nContoh: `!additem Batu Evo 3 15000`",
                delete_after=8
            )
            return
        try:
            harga = int(parts[-1])
            qty = int(parts[-2])
            nama = " ".join(parts[:-2])
        except ValueError:
            await ctx.send(
                "Qty dan harga harus berupa angka.\nContoh: `!additem Batu Evo 3 15000`",
                delete_after=8
            )
            return
        if not nama:
            await ctx.send("Nama item tidak boleh kosong!", delete_after=8)
            return
        ticket = self.active_tickets[ch_id]
        ticket["admin_id"] = ctx.author.id
        ticket["items"].append({"nama": nama, "qty": qty, "harga": harga})
        ticket["last_activity"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save_scaset_ticket(ticket)
        await ctx.message.delete()
        await self._update_embed(ctx.channel, ticket)

    @commands.command(name="delitem")
    async def del_item(self, ctx, nomor: int = None):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        ch_id = ctx.channel.id
        if ch_id not in self.active_tickets:
            return
        ticket = self.active_tickets[ch_id]
        if not nomor or nomor < 1 or nomor > len(ticket["items"]):
            await ctx.send(
                f"Nomor tidak valid. Gunakan `!delitem <nomor>` (1–{len(ticket['items'])})",
                delete_after=8
            )
            return
        removed = ticket["items"].pop(nomor - 1)
        ticket["last_activity"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save_scaset_ticket(ticket)
        await ctx.message.delete()
        await self._update_embed(ctx.channel, ticket)
        await ctx.channel.send(f"🗑️ Item **{removed['nama']}** dihapus.", delete_after=5)

    @commands.command(name="aset")
    async def kirim_katalog(self, ctx):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        await ctx.message.delete()
        await self.refresh_catalog()
        await ctx.send("✅ Katalog SC/Aset berhasil dikirim!", delete_after=5)


async def setup(bot: commands.Bot):
    await bot.add_cog(ScasetStore(bot))
    bot.add_view(ScasetCatalogView())
    print("Cog ScasetStore siap.")
