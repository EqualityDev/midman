import discord
import datetime
import asyncio
from discord.ext import commands, tasks
from utils.config import ADMIN_ROLE_ID, LOG_CHANNEL_ID, STORE_NAME, TICKET_CATEGORY_ID, TRANSCRIPT_CHANNEL_ID
from utils.counter import next_ticket_number
from utils.transcript import generate as generate_transcript
from utils.db import get_conn

def _load_ml_products():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT dm, harga FROM ml_products ORDER BY dm")
    rows = c.fetchall()
    conn.close()
    return [{"dm": r["dm"], "harga": r["harga"]} for r in rows]

def _load_ff_products():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT dm, harga FROM ff_products ORDER BY dm")
    rows = c.fetchall()
    conn.close()
    return [{"dm": r["dm"], "harga": r["harga"]} for r in rows]

WDP_PRODUCTS = [
    {"qty": 1, "label": "1x Weekly Diamond Pass", "harga": 29000},
    {"qty": 2, "label": "2x Weekly Diamond Pass", "harga": 57000},
    {"qty": 3, "label": "3x Weekly Diamond Pass", "harga": 86000},
]

ML_PRODUCTS = _load_ml_products()

THUMBNAIL = "https://i.imgur.com/CWtUCzj.png"

def load_ml_tickets():
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT * FROM ml_tickets')
    rows = c.fetchall()
    conn.close()
    tickets = {}
    for row in rows:
        tickets[row['channel_id']] = {
            'channel_id': row['channel_id'],
            'user_id': row['user_id'],
            'id_ml': row['id_ml'],
            'server_id': row['server_id'],
            'dm': row['dm'],
            'harga': row['harga'],
            'opened_at': row['opened_at'],
            'last_activity': row['opened_at'],
            'game': row['game'] if row['game'] else 'ML',
            'warned': bool(row['warned']) if row['warned'] is not None else False,
        }
    return tickets

def save_ml_ticket(ticket):
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO ml_tickets
        (channel_id, user_id, id_ml, server_id, dm, harga, opened_at, game, warned)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        ticket['channel_id'],
        ticket['user_id'],
        ticket['id_ml'],
        ticket['server_id'],
        ticket['dm'],
        ticket['harga'],
        ticket['opened_at'],
        ticket.get('game', 'ML'),
        1 if ticket.get('warned') else 0,
    ))
    conn.commit()
    conn.close()

def delete_ml_ticket(channel_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute('DELETE FROM ml_tickets WHERE channel_id = ?', (channel_id,))
    conn.commit()
    conn.close()

ML_KECIL = [p for p in ML_PRODUCTS if p["dm"] <= 100]
ML_BESAR = [p for p in ML_PRODUCTS if p["dm"] > 100]




FF_PRODUCTS = _load_ff_products()
FF_KECIL = FF_PRODUCTS[:20]
FF_BESAR = FF_PRODUCTS[20:]

class MLFormModal(discord.ui.Modal, title="Topup Mobile Legends"):
    id_ml = discord.ui.TextInput(
        label="ID Mobile Legends",
        placeholder="Contoh: 123456789",
        required=True,
        max_length=20
    )
    server_id = discord.ui.TextInput(
        label="Server ID",
        placeholder="Contoh: 1234",
        required=True,
        max_length=10
    )

    def __init__(self, dm: int, harga: int, label: str = None):
        super().__init__()
        self.dm = dm
        self.harga = harga
        self.label = label  # Untuk WDP, label menggantikan "X Diamond"

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user

        # Cek tiket aktif
        cog = interaction.client.cogs.get("MLStore")
        for ch_id, t in cog.active_tickets.items():
            if t["user_id"] == user.id:
                existing = guild.get_channel(ch_id)
                if existing:
                    await interaction.response.send_message(
                        f"Kamu masih punya tiket aktif di {existing.mention}!",
                        ephemeral=True
                    )
                    return

        admin_role = guild.get_role(ADMIN_ROLE_ID)
        category = guild.get_channel(TICKET_CATEGORY_ID)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        if admin_role:
            overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel = await guild.create_text_channel(
            name=f"ml-{user.name}",
            category=category,
            overwrites=overwrites
        )

        ticket = {
            "channel_id": channel.id,
            "user_id": user.id,
            "id_ml": self.id_ml.value.strip(),
            "server_id": self.server_id.value.strip(),
            "dm": self.dm,
            "item_label": self.label if self.label else f"{self.dm} Diamond",
            "harga": self.harga,
            "opened_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "last_activity": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        cog.active_tickets[channel.id] = ticket
        save_ml_ticket(ticket)

        embed = discord.Embed(
            title=f"TOPUP MOBILE LEGENDS — {STORE_NAME}",
            color=0x3498DB,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.add_field(name="\u200b", value=(
            f"Halo, {user.mention}! Tiket topup ML kamu sudah dibuat.\n"
            f"──────────────────────────────\n"
            f"Member   : {user.mention}\n"
            f"ID ML    : `{self.id_ml.value.strip()}`\n"
            f"Server   : `{self.server_id.value.strip()}`\n"
            f"Item     : {self.dm} Diamond\n"
            f"Total    : Rp {self.harga:,}\n"
            f"Metode   : QRIS\n"
            f"Status   : Menunggu proses\n"
            f"──────────────────────────────\n"
            f"**!mlselesai** — konfirmasi topup selesai\n"
            f"**!mlbatal [alasan]** — batalkan tiket\n"
            f"──────────────────────────────\n"
            f"Tiket yang tidak aktif selama 2 jam akan otomatis ditutup dan transaksi dianggap batal."
        ), inline=False)
        embed.set_thumbnail(url=THUMBNAIL)
        embed.set_footer(text=STORE_NAME)

        if admin_role:
            await channel.send(content=admin_role.mention, embed=embed)
        else:
            await channel.send(embed=embed)

        await interaction.response.send_message(
            f"Tiket berhasil dibuat di {channel.mention}!", ephemeral=True
        )



class FFFormModal(discord.ui.Modal, title="Topup Free Fire"):
    player_id = discord.ui.TextInput(
        label="Player ID Free Fire",
        placeholder="Contoh: 123456789",
        required=True,
        max_length=20
    )

    def __init__(self, dm: int, harga: int, label: str = None):
        super().__init__()
        self.dm = dm
        self.harga = harga
        self.label = label  # Untuk WDP, label menggantikan "X Diamond"

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user

        # Cek tiket aktif
        cog = interaction.client.cogs.get("MLStore")
        for ch_id, t in cog.active_tickets.items():
            if t["user_id"] == user.id:
                existing = guild.get_channel(ch_id)
                if existing:
                    await interaction.response.send_message(
                        f"Kamu masih punya tiket aktif di {existing.mention}!",
                        ephemeral=True
                    )
                    return

        admin_role = guild.get_role(ADMIN_ROLE_ID)
        category = guild.get_channel(TICKET_CATEGORY_ID)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        if admin_role:
            overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        ticket_num = next_ticket_number()
        channel = await guild.create_text_channel(
            name=f"topupff-{str(ticket_num).zfill(4)}-{user.name[:10]}",
            category=category,
            overwrites=overwrites
        )

        ticket = {
            "channel_id": channel.id,
            "user_id": user.id,
            "id_ml": self.player_id.value.strip(),
            "server_id": "-",
            "dm": self.dm,
            "harga": self.harga,
            "opened_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "last_activity": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "game": "FF",
        }
        cog.active_tickets[channel.id] = ticket
        save_ml_ticket(ticket)

        embed = discord.Embed(
            title=f"TOPUP FREE FIRE — {STORE_NAME}",
            color=0xFF6B35,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.add_field(name="\u200b", value=(
            f"Halo, {user.mention}! Tiket topup FF kamu sudah dibuat.\n"
            f"──────────────────────────────\n"
            f"Member    : {user.mention}\n"
            f"Player ID : `{self.player_id.value.strip()}`\n"
            f"Item      : {self.dm} Diamond\n"
            f"Total     : Rp {self.harga:,}\n"
            f"Metode    : QRIS\n"
            f"Status    : Menunggu proses\n"
            f"──────────────────────────────\n"
            f"**!mlselesai** — konfirmasi topup selesai\n"
            f"**!mlbatal [alasan]** — batalkan tiket\n"
            f"──────────────────────────────\n"
            f"Tiket yang tidak aktif selama 2 jam akan otomatis ditutup dan transaksi dianggap batal."
        ), inline=False)
        embed.set_thumbnail(url=THUMBNAIL)
        embed.set_footer(text=STORE_NAME)

        if admin_role:
            await channel.send(content=admin_role.mention, embed=embed)
        else:
            await channel.send(embed=embed)

        await interaction.response.send_message(
            f"Tiket berhasil dibuat di {channel.mention}!", ephemeral=True
        )

class MLSelectKecil(discord.ui.Select):
    def __init__(self, products=None):
        if products is None:
            products = _load_ml_products()
        kecil = [p for p in products if p["dm"] <= 100]
        options = [
            discord.SelectOption(
                label=f"{p['dm']} Diamond",
                description=f"Rp {p['harga']:,}",
                value=str(p['dm'])
            ) for p in kecil
        ] or [discord.SelectOption(label="Tidak ada produk", value="none")]
        super().__init__(
            placeholder="[MoLe] Pilih jumlah diamond (3–100 DM)...",
            options=options[:25],
            custom_id="ml_select_kecil"
        )

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            await interaction.response.send_message("Tidak ada produk tersedia.", ephemeral=True)
            return
        dm = int(self.values[0])
        products = _load_ml_products()
        harga = next((p["harga"] for p in products if p["dm"] == dm), 0)
        await interaction.response.send_modal(MLFormModal(dm=dm, harga=harga))


class MLSelectBesar(discord.ui.Select):
    def __init__(self, products=None):
        if products is None:
            products = _load_ml_products()
        besar = [p for p in products if p["dm"] > 100]
        options = [
            discord.SelectOption(
                label=f"{p['dm']} Diamond",
                description=f"Rp {p['harga']:,}",
                value=str(p['dm'])
            ) for p in besar
        ] or [discord.SelectOption(label="Tidak ada produk", value="none")]
        super().__init__(
            placeholder="[MoLe] Pilih jumlah diamond (110–346 DM)...",
            options=options[:25],
            custom_id="ml_select_besar"
        )

    async def callback(self, interaction: discord.Interaction):
        dm = int(self.values[0])
        harga = next(p["harga"] for p in ML_PRODUCTS if p["dm"] == dm)
        await interaction.response.send_modal(MLFormModal(dm=dm, harga=harga))



class FFSelectKecil(discord.ui.Select):
    def __init__(self, products=None):
        if products is None:
            products = _load_ff_products()
        kecil = products[:20]
        options = [
            discord.SelectOption(
                label=f"{p['dm']} Diamond FF",
                description=f"Rp {p['harga']:,}",
                value=str(p['dm'])
            ) for p in kecil
        ] or [discord.SelectOption(label="Tidak ada produk", value="none")]
        super().__init__(
            placeholder="[Free Fire] Pilih diamond (5–170 DM)...",
            options=options[:25],
            custom_id="ff_select_kecil"
        )

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            await interaction.response.send_message("Tidak ada produk tersedia.", ephemeral=True)
            return
        dm = int(self.values[0])
        products = _load_ff_products()
        harga = next((p["harga"] for p in products if p["dm"] == dm), 0)
        await interaction.response.send_modal(FFFormModal(dm=dm, harga=harga))


class FFSelectBesar(discord.ui.Select):
    def __init__(self, products=None):
        if products is None:
            products = _load_ff_products()
        besar = products[20:]
        options = [
            discord.SelectOption(
                label=f"{p['dm']} Diamond FF",
                description=f"Rp {p['harga']:,}",
                value=str(p['dm'])
            ) for p in besar
        ] or [discord.SelectOption(label="Tidak ada produk", value="none")]
        super().__init__(
            placeholder="[Free Fire] Pilih diamond (180–790 DM)...",
            options=options[:25],
            custom_id="ff_select_besar"
        )

    async def callback(self, interaction: discord.Interaction):
        dm = int(self.values[0])
        harga = next(p["harga"] for p in FF_PRODUCTS if p["dm"] == dm)
        await interaction.response.send_modal(FFFormModal(dm=dm, harga=harga))

class WDPSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label=p["label"],
                description=f"Rp {p['harga']:,}",
                value=str(p["qty"])
            ) for p in WDP_PRODUCTS
        ]
        super().__init__(
            placeholder="[MoLe] Pilih Weekly Diamond Pass (WDP)...",
            options=options,
            custom_id="ml_select_wdp"
        )

    async def callback(self, interaction: discord.Interaction):
        qty = int(self.values[0])
        wdp = next(p for p in WDP_PRODUCTS if p["qty"] == qty)
        await interaction.response.send_modal(MLFormModal(dm=wdp["qty"], harga=wdp["harga"], label=wdp["label"]))


class MLBuyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        # Reload produk terbaru dari DB setiap kali view dibuat
        ml = _load_ml_products()
        ff = _load_ff_products()
        self.add_item(MLSelectKecil(ml))
        self.add_item(MLSelectBesar(ml))
        self.add_item(WDPSelect())
        self.add_item(FFSelectKecil(ff))
        self.add_item(FFSelectBesar(ff))


class MLStore(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_tickets = load_ml_tickets()
        self.catalog_message_id = None
        self.auto_close_task.start()

    def cog_unload(self):
        self.auto_close_task.cancel()

    @tasks.loop(minutes=10)
    async def auto_close_task(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        guild = self.bot.guilds[0] if self.bot.guilds else None
        if not guild:
            return
        for ch_id, ticket in list(self.active_tickets.items()):
            last = ticket.get("last_activity") or ticket.get("opened_at")
            if not last:
                continue
            last_dt = datetime.datetime.fromisoformat(last)
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=datetime.timezone.utc)
            elapsed = (now - last_dt).total_seconds()
            channel = guild.get_channel(ch_id)
            if elapsed >= 7200:
                if channel:
                    try:
                        await channel.send(
                            "Tiket ini otomatis ditutup karena tidak ada aktivitas selama 2 jam. "
                            "Transaksi dianggap batal. Channel akan dihapus dalam 10 detik."
                        )
                        import asyncio as _asyncio
                        await _asyncio.sleep(10)
                        await channel.delete()
                    except Exception:
                        pass
                delete_ml_ticket(ch_id)
                self.active_tickets.pop(ch_id, None)
            elif elapsed >= 3600 and not ticket.get("warned"):
                try:
                    # Hapus pesan peringatan lama kalau ada
                    old_warn_id = ticket.get("warn_message_id")
                    if old_warn_id:
                        try:
                            old_msg = await channel.fetch_message(old_warn_id)
                            await old_msg.delete()
                        except Exception:
                            pass
                    warn_embed = discord.Embed(title="PERINGATAN TIKET", color=0xFFA500)
                    warn_embed.add_field(name="\u200b", value=(
                        "Tiket tidak ada aktivitas selama **1 jam**.\n\n"
                        "Segera ketik `!mlselesai` jika selesai, atau `!mlbatal` jika dibatalkan.\n\n"
                        "Tiket akan otomatis ditutup dalam **1 jam lagi**."
                    ), inline=False)
                    warn_embed.set_footer(text=STORE_NAME)
                    _user = guild.get_member(ticket["user_id"])
                    _mn = _user.mention if _user else ""
                    warn_msg = await channel.send(content=_mn, embed=warn_embed)
                    ticket["warn_message_id"] = warn_msg.id
                except Exception:
                    pass
                ticket["warned"] = True
                save_ml_ticket(ticket)

    @auto_close_task.before_loop
    async def before_auto_close(self):
        await self.bot.wait_until_ready()

    @commands.command(name="mlcatalog")
    async def mlcatalog(self, ctx):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        await ctx.message.delete()

        from utils.config import ML_CATALOG_CHANNEL_ID
        ch = ctx.guild.get_channel(ML_CATALOG_CHANNEL_ID)
        if not ch:
            await ctx.send("Channel ML catalog tidak ditemukan!", delete_after=5)
            return

        embed = discord.Embed(
            title=f"TOPUP DIAMOND GAME",
            description=(
                f"Sekarang tersedia di **{STORE_NAME}**\n"
                f"Topup diamond dengan harga terjangkau, proses cepat, amanah dan transparan!\n\n"
                f"**Mobile Legends:**\n"
                f"Dropdown 1 & 2 — Pilih jumlah DM, isi ID ML + Server ID\n\n"
                f"**Weekly Diamond Pass (WDP):**\n"
                f"Dropdown 3 — Pilih paket WDP, isi ID ML + Server ID\n"
                f"1x WDP = 80 DM langsung + 20 DM/hari selama 7 hari (total 220 DM)\n\n"
                f"**Free Fire:**\n"
                f"Dropdown 4 & 5 — Pilih jumlah DM, isi Player ID FF\n\n"
                f"Metode Pembayaran: **QRIS**"
            ),
            color=0x3498DB
        )
        embed.set_thumbnail(url=THUMBNAIL)
        embed.set_footer(text=STORE_NAME)

        if self.catalog_message_id:
            try:
                msg = await ch.fetch_message(self.catalog_message_id)
                await msg.edit(embed=embed, view=MLBuyView())
                await ctx.send(f"Catalog ML diperbarui di {ch.mention}", delete_after=5)
                return
            except Exception:
                pass

        async for msg in ch.history(limit=20):
            if msg.author == ctx.guild.me:
                try:
                    await msg.delete()
                except Exception:
                    pass

        sent = await ch.send(embed=embed, view=MLBuyView())
        self.catalog_message_id = sent.id
        await ctx.send(f"Catalog ML dikirim ke {ch.mention}", delete_after=5)

    @commands.command(name="mlselesai")
    async def mlselesai(self, ctx):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        channel_id = ctx.channel.id
        if channel_id not in self.active_tickets:
            await ctx.send("Channel ini bukan tiket ML aktif.", delete_after=5)
            return

        ticket = self.active_tickets[channel_id]
        member = ctx.guild.get_member(ticket["user_id"])
        nomor = next_ticket_number()
        closed_at = datetime.datetime.now(datetime.timezone.utc)

        await ctx.send(f"{member.mention if member else ""}\nTopup berhasil diproses. Terima kasih telah berbelanja di {STORE_NAME}! Tiket ditutup dalam 5 detik.")
        await asyncio.sleep(5)

        transcript_file = await generate_transcript(ctx.channel, STORE_NAME)
        transcript_ch = ctx.guild.get_channel(TRANSCRIPT_CHANNEL_ID)
        if transcript_ch:
            try:
                await transcript_ch.send(
                    content=f"Transcript ML — {ctx.channel.name}",
                    file=transcript_file
                )
            except Exception as e:
                print(f"[WARNING] Gagal kirim transcript ML: {e}")

        log_ch = ctx.guild.get_channel(LOG_CHANNEL_ID)
        if log_ch:
            log_embed = discord.Embed(
                title=f"TOPUP ML SUKSES — #{nomor:04d}",
                description="Topup berhasil. Terima kasih telah berbelanja di Cellyn Store!",
                color=0x3498DB,
                timestamp=closed_at
            )
            log_embed.add_field(name="Admin", value=f"{ctx.author.mention}\n`{ctx.author.id}`", inline=False)
            log_embed.add_field(name="Member", value=f"{member.mention if member else ticket['user_id']}\n`{ticket['user_id']}`", inline=False)
            if ticket.get("game") == "FF":
                log_embed.add_field(name="Player ID FF", value=f"`{ticket['id_ml']}`", inline=False)
                log_embed.color = 0xFF6B35
            else:
                log_embed.add_field(name="ID ML", value=f"`{ticket['id_ml']}` (Server: `{ticket['server_id']}`)", inline=False)
            log_embed.add_field(name="Item", value=f"{ticket['dm']} Diamond", inline=False)
            log_embed.add_field(name="Total", value=f"Rp {ticket['harga']:,}", inline=False)
            log_embed.add_field(name="Metode Pembayaran", value="QRIS", inline=False)
            log_embed.set_thumbnail(url=THUMBNAIL)
            log_embed.set_footer(text=STORE_NAME)
            await log_ch.send(embed=log_embed)

        del self.active_tickets[channel_id]
        await ctx.channel.delete()

    @commands.command(name="mlbatal")
    async def mlbatal(self, ctx, *, alasan: str = "Tidak ada alasan diberikan."):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        channel_id = ctx.channel.id
        if channel_id not in self.active_tickets:
            await ctx.send("Channel ini bukan tiket ML aktif.", delete_after=5)
            return

        embed = discord.Embed(title="TOPUP DIBATALKAN", color=0x3498DB)
        embed.add_field(name="Dibatalkan oleh", value=ctx.author.mention, inline=True)
        embed.add_field(name="Alasan", value=alasan, inline=False)
        embed.add_field(name="", value="Tiket akan ditutup dalam 5 detik.", inline=False)
        await ctx.send(embed=embed)
        await asyncio.sleep(5)

        del self.active_tickets[channel_id]
        await ctx.channel.delete()


async def setup(bot):
    await bot.add_cog(MLStore(bot))
    bot.add_view(MLBuyView())
    print("Cog MLStore siap.")