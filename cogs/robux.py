import asyncio
import discord
import datetime
from discord.ext import commands, tasks
from utils.config import ADMIN_ROLE_ID, ROBUX_CATALOG_CHANNEL_ID, LOG_CHANNEL_ID, STORE_NAME, TICKET_CATEGORY_ID
from utils.db import get_conn
from utils.robux_db import load_robux_tickets, save_robux_ticket, delete_robux_ticket

THUMBNAIL = "https://i.imgur.com/CWtUCzj.png"

def load_robux_products():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, category, name, robux FROM robux_products WHERE active = 1 ORDER BY category, id")
    rows = c.fetchall()
    conn.close()
    return [{"id": r["id"], "category": r["category"], "name": r["name"], "robux": r["robux"]} for r in rows]

PRODUCTS = load_robux_products()

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

class CategoryView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(CategoryButton("GAMEPASS", 0x5865F2))
        self.add_item(CategoryButton("CRATE", 0x2ECC71))
        self.add_item(CategoryButton("BOOST", 0xE91E63))
        self.add_item(CategoryButton("LIMITED", 0xF1C40F))

class CategoryButton(discord.ui.Button):
    def __init__(self, category, color):
        super().__init__(
            label=category,
            style=discord.ButtonStyle.secondary,
            custom_id=f"robux_cat_{category}"
        )
        self.category = category

    async def callback(self, interaction: discord.Interaction):
        items = [p for p in PRODUCTS if p["category"] == self.category]
        rate = get_rate()
        options = []
        for item in items:
            harga_str = harga(item["robux"], rate)
            options.append(discord.SelectOption(
                label=f"{item['name']}",
                description=f"{item['robux']} Robux — {harga_str}",
                value=str(item["id"]),
            ))
        view = discord.ui.View(timeout=60)
        select = ItemSelect(options, self.category)
        view.add_item(select)
        await interaction.response.send_message(
            f"Pilih item **{self.category}**:",
            view=view,
            ephemeral=True
        )

class ItemSelect(discord.ui.Select):
    def __init__(self, options, category):
        super().__init__(
            placeholder=f"Pilih item {category}...",
            options=options,
            custom_id=f"robux_select_{category}"
        )

    async def callback(self, interaction: discord.Interaction):
        item_id = int(self.values[0])
        item = next((p for p in PRODUCTS if p["id"] == item_id), None)
        if not item:
            await interaction.response.send_message("Item tidak ditemukan!", ephemeral=True)
            return

        rate = get_rate()
        if rate == 0:
            await interaction.response.send_message("Rate belum diset oleh admin!", ephemeral=True)
            return

        total = item["robux"] * rate
        guild = interaction.guild
        member = interaction.user

        # Cek tiket aktif
        cog = interaction.client.cogs.get("RobuxStore")
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

        category = guild.get_channel(TICKET_CATEGORY_ID)
        admin_role = guild.get_role(ADMIN_ROLE_ID)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        if admin_role:
            overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel = await guild.create_text_channel(
            name=f"robux-{member.name}",
            category=category,
            overwrites=overwrites,
        )

        ticket = {
            "user_id": member.id,
            "item_id": item["id"],
            "item_name": item["name"],
            "robux": item["robux"],
            "rate": rate,
            "total": total,
            "channel_id": channel.id,
            "opened_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        ticket["last_activity"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        cog.active_tickets[channel.id] = ticket
        save_robux_ticket(ticket)

        embed = discord.Embed(
            title=f"ROBUX STORE — {STORE_NAME}",
            color=0xE91E63,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.add_field(name="Member", value=member.mention, inline=True)
        embed.add_field(name="Item", value=item["name"], inline=True)
        embed.add_field(name="Jumlah Robux", value=f"{item['robux']} Robux", inline=True)
        embed.add_field(name="Rate", value=f"Rp {rate:,}/Robux", inline=True)
        embed.add_field(name="Total Tagihan", value=f"Rp {total:,}", inline=True)
        embed.add_field(
            name="Cara Bayar",
            value="Ketik **1** — QRIS  |  **2** — DANA  |  **3** — BCA",
            inline=False
        )
        embed.add_field(
            name="Catatan",
            value="Setelah pembayaran dikonfirmasi, admin dan member masuk game untuk proses gift item.",
            inline=False
        )
        embed.add_field(
            name="Peringatan",
            value="Tiket yang tidak aktif selama 2 jam akan otomatis ditutup dan transaksi dianggap batal. Jangan biarkan tiket menggantung.",
            inline=False
        )
        embed.set_thumbnail(url=THUMBNAIL)
        embed.set_footer(text=f"{STORE_NAME} • Rate dapat berubah sewaktu-waktu")

        await channel.send(
            content=f"Halo {member.mention}! Tiket pembelian item Robux telah dibuat.{' ' + admin_role.mention if admin_role else ''}",
            embed=embed
        )
        await interaction.followup.send(f"Tiket dibuat! {channel.mention}", ephemeral=True)

class RobuxStore(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.catalog_message_id = None
        self.active_tickets = load_robux_tickets()
        self.auto_close_task.start()

    def cog_unload(self):
        self.auto_close_task.cancel()

    @tasks.loop(minutes=10)
    async def auto_close_task(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        for ch_id, ticket in list(self.active_tickets.items()):
            if ticket.get("paid"):
                continue
            last = ticket.get("last_activity") or ticket.get("opened_at")
            if not last:
                continue
            last_dt = datetime.datetime.fromisoformat(last)
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=datetime.timezone.utc)
            elapsed = (now - last_dt).total_seconds()
            guild = self.bot.guilds[0] if self.bot.guilds else None
            if not guild:
                continue
            channel = guild.get_channel(ch_id)
            if elapsed >= 7200:
                if channel:
                    try:
                        await channel.send(
                            "Tiket ini otomatis ditutup karena tidak ada aktivitas selama 2 jam. "
                            "Transaksi dianggap batal. Channel akan dihapus dalam 10 detik."
                        )
                        import asyncio
                        await asyncio.sleep(10)
                        await channel.delete()
                    except Exception:
                        pass
                delete_robux_ticket(ch_id)
                self.active_tickets.pop(ch_id, None)
            elif elapsed >= 3600 and not ticket.get("warned"):
                if channel:
                    try:
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
                            "Segera selesaikan pembayaran atau hubungi admin.\n\n"
                            "Tiket akan otomatis ditutup dalam **1 jam lagi**."
                        ), inline=False)
                        warn_embed.set_thumbnail(url=THUMBNAIL)
                        warn_embed.set_footer(text=STORE_NAME)
                        _user = guild.get_member(ticket["user_id"])
                        _mn = _user.mention if _user else ""
                        warn_msg = await channel.send(content=_mn, embed=warn_embed)
                        ticket["warn_message_id"] = warn_msg.id
                    except Exception:
                        pass
                ticket["warned"] = True
                save_robux_ticket(ticket)

    @auto_close_task.before_loop
    async def before_auto_close(self):
        await self.bot.wait_until_ready()

    async def reload_products(self):
        global PRODUCTS
        PRODUCTS = load_robux_products()

    async def refresh_catalog(self):
        await self.reload_products()
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
                await msg.edit(embed=embed, view=CategoryView())
                return
            except Exception:
                pass
        async for msg in ch.history(limit=20):
            if msg.author == self.bot.user:
                try:
                    await msg.delete()
                except Exception:
                    pass
        sent = await ch.send(embed=embed, view=CategoryView())
        self.catalog_message_id = sent.id

    async def refresh_active_tickets(self, guild, rate):
        for ch_id, ticket in list(self.active_tickets.items()):
            channel = guild.get_channel(ch_id)
            if not channel:
                self.active_tickets.pop(ch_id, None)
                continue
            if ticket.get("paid"):
                continue
            ticket["rate"] = rate
            ticket["total"] = ticket["robux"] * rate
            # Update embed payment jika sudah dipilih
            payment_msg_id = ticket.get("payment_embed_msg_id")
            method = ticket.get("payment_embed_method")
            if payment_msg_id and method:
                try:
                    from utils.config import DANA_NUMBER, BCA_NUMBER
                    pmsg = await channel.fetch_message(payment_msg_id)
                    if method == "QRIS":
                        desc = (
                            f"Scan QR Code di bawah untuk membayar.\n\n"
                            f"Item: **{ticket['item_name']}**\n"
                            f"Rate: **Rp {rate:,}/Robux**\n"
                            f"Total: **Rp {ticket['total']:,}**\n\n"
                            f"Setelah transfer, kirim bukti pembayaran lalu klik tombol PAID."
                        )
                    elif method == "DANA":
                        desc = (
                            f"Transfer ke nomor DANA berikut:\n\n"
                            f"**`{DANA_NUMBER}`**\n\n"
                            f"Item: **{ticket['item_name']}**\n"
                            f"Rate: **Rp {rate:,}/Robux**\n"
                            f"Total: **Rp {ticket['total']:,}**\n\n"
                            f"Setelah transfer, kirim bukti pembayaran lalu klik tombol PAID."
                        )
                    elif method == "BCA":
                        desc = (
                            f"Transfer ke rekening BCA berikut:\n\n"
                            f"**`{BCA_NUMBER}`**\n\n"
                            f"Item: **{ticket['item_name']}**\n"
                            f"Rate: **Rp {rate:,}/Robux**\n"
                            f"Total: **Rp {ticket['total']:,}**\n\n"
                            f"Setelah transfer, kirim bukti pembayaran lalu klik tombol PAID."
                        )
                    new_embed = discord.Embed(title=f"{method} PAYMENT", description=desc, color=0xE91E63)
                    new_embed.set_footer(text=f"{STORE_NAME} • Pastikan nominal sesuai")
                    await pmsg.edit(embed=new_embed)
                except Exception as e:
                    print(f"[WARNING] Gagal update embed payment: {e}")
            # Update embed di tiket
            try:
                async for msg in channel.history(limit=10, oldest_first=True):
                    if msg.author == guild.me and msg.embeds:
                        embed = msg.embeds[0]
                        new_embed = discord.Embed(
                            title=embed.title,
                            color=embed.color,
                            timestamp=embed.timestamp
                        )
                        for field in embed.fields:
                            if field.name == "Rate":
                                new_embed.add_field(name="Rate", value=f"Rp {rate:,}/Robux", inline=True)
                            elif field.name == "Total Tagihan":
                                new_embed.add_field(name="Total Tagihan", value=f"Rp {ticket['total']:,}", inline=True)
                            else:
                                new_embed.add_field(name=field.name, value=field.value, inline=field.inline)
                        if embed.thumbnail:
                            new_embed.set_thumbnail(url=embed.thumbnail.url)
                        if embed.footer:
                            new_embed.set_footer(text=embed.footer.text)
                        await msg.edit(embed=new_embed)
                        break
            except Exception as e:
                print(f"[WARNING] Gagal update embed tiket robux: {e}")

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
        guild = ctx.guild
        await self.refresh_active_tickets(guild, rate)
        # Refresh embed vilog
        vilog_cog = self.bot.cogs.get("Vilog")
        if vilog_cog and hasattr(vilog_cog, "refresh_embed"):
            await vilog_cog.refresh_embed(guild)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if message.guild is None:
            return

        channel_id = message.channel.id
        if channel_id not in self.active_tickets:
            return

        ticket = self.active_tickets[channel_id]
        if ticket.get("paid"):
            return
        if ticket.get("payment_method"):
            return

        ticket["last_activity"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

        if message.content.strip() not in ["1", "2", "3"]:
            return

        from utils.config import DANA_NUMBER, BCA_NUMBER
        methods = ["QRIS", "DANA", "BCA"]
        method = methods[int(message.content.strip()) - 1]
        ticket["payment_method"] = method
        rate = ticket["rate"]
        total = ticket["total"]

        if method == "QRIS":
            qris_url = None
            try:
                conn = get_conn()
                c = conn.cursor()
                c.execute("SELECT value FROM settings WHERE key = 'qris_url'")
                row = c.fetchone()
                conn.close()
                if row:
                    qris_url = row["value"]
            except Exception:
                pass
            embed = discord.Embed(
                title="QRIS PAYMENT",
                description=(
                    f"Scan QR Code di bawah untuk membayar.\n\n"
                    f"Item: **{ticket['item_name']}**\n"
                    f"Rate: **Rp {rate:,}/Robux**\n"
                    f"Total: **Rp {total:,}**\n\n"
                    f"Setelah transfer, kirim bukti pembayaran lalu klik tombol PAID."
                ),
                color=0xE91E63,
            )
            if qris_url:
                embed.set_image(url=qris_url)
            embed.set_footer(text=f"{STORE_NAME} • Pastikan nominal sesuai")
            payment_embed_msg = await message.channel.send(embed=embed)
            ticket["payment_embed_msg_id"] = payment_embed_msg.id

        elif method == "DANA":
            embed = discord.Embed(
                title="DANA PAYMENT",
                description=(
                    f"Transfer ke nomor DANA berikut:\n\n"
                    f"**`{DANA_NUMBER}`**\n\n"
                    f"Item: **{ticket['item_name']}**\n"
                    f"Rate: **Rp {rate:,}/Robux**\n"
                    f"Total: **Rp {total:,}**\n\n"
                    f"Setelah transfer, kirim bukti pembayaran lalu klik tombol PAID."
                ),
                color=0xE91E63,
            )
            embed.set_footer(text=f"{STORE_NAME} • Pastikan nominal sesuai")
            payment_embed_msg = await message.channel.send(embed=embed)
            ticket["payment_embed_msg_id"] = payment_embed_msg.id

        elif method == "BCA":
            embed = discord.Embed(
                title="BCA PAYMENT",
                description=(
                    f"Transfer ke rekening BCA berikut:\n\n"
                    f"**`{BCA_NUMBER}`**\n\n"
                    f"Item: **{ticket['item_name']}**\n"
                    f"Rate: **Rp {rate:,}/Robux**\n"
                    f"Total: **Rp {total:,}**\n\n"
                    f"Setelah transfer, kirim bukti pembayaran lalu klik tombol PAID."
                ),
                color=0xE91E63,
            )
            embed.set_footer(text=f"{STORE_NAME} • Pastikan nominal sesuai")
            payment_embed_msg = await message.channel.send(embed=embed)
            ticket["payment_embed_msg_id"] = payment_embed_msg.id

        paid_view = discord.ui.View(timeout=None)
        paid_view.add_item(discord.ui.Button(
            label="PAID",
            style=discord.ButtonStyle.success,
            custom_id=f"robux_paid_{channel_id}"
        ))
        payment_msg = await message.channel.send(
            content="Sudah transfer? Kirim bukti pembayaran lalu klik tombol di bawah:",
            view=paid_view
        )
        ticket["payment_embed_method"] = method
        ticket["payment_msg_id"] = payment_msg.id
        save_robux_ticket(ticket)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        custom_id = interaction.data.get("custom_id", "")

        # ─── PAID button ─────────────────────────────────────────
        if custom_id.startswith("robux_paid_"):
            channel_id = int(custom_id.replace("robux_paid_", ""))
            if channel_id not in self.active_tickets:
                await interaction.response.send_message("Tiket tidak ditemukan!", ephemeral=True)
                return

            ticket = self.active_tickets[channel_id]
            if interaction.user.id != ticket["user_id"]:
                await interaction.response.send_message("Bukan tiket kamu!", ephemeral=True)
                return
            if ticket.get("paid"):
                await interaction.response.send_message("Pembayaran sudah diproses.", ephemeral=True)
                return

            await interaction.response.defer()

            admin_role = interaction.guild.get_role(ADMIN_ROLE_ID)
            verify_view = discord.ui.View(timeout=None)
            verify_view.add_item(discord.ui.Button(
                label="Verifikasi Pembayaran",
                style=discord.ButtonStyle.success,
                custom_id=f"robux_verify_{channel_id}"
            ))
            ping = admin_role.mention if admin_role else ""
            await interaction.channel.send(
                content=f"{ping} **{interaction.user.display_name}** mengklaim sudah bayar!\n"
                        f"Item: **{ticket['item_name']}** | Total: **Rp {ticket['total']:,}** | Metode: **{ticket.get('payment_method', '-')}**",
                view=verify_view
            )
            await interaction.followup.send(
                "Pembayaran kamu sedang diverifikasi oleh admin. Estimasi 1-5 menit.",
                ephemeral=True
            )

        # ─── VERIFY button ────────────────────────────────────────
        elif custom_id.startswith("robux_verify_"):
            channel_id = int(custom_id.replace("robux_verify_", ""))
            if channel_id not in self.active_tickets:
                await interaction.response.send_message("Tiket tidak ditemukan!", ephemeral=True)
                return

            admin_role = interaction.guild.get_role(ADMIN_ROLE_ID)
            if admin_role not in interaction.user.roles:
                await interaction.response.send_message("Admin only!", ephemeral=True)
                return

            ticket = self.active_tickets[channel_id]
            ticket["paid"] = True
            ticket["admin_id"] = interaction.user.id
            save_robux_ticket(ticket)

            await interaction.response.send_message(
                f"Pembayaran dikonfirmasi oleh {interaction.user.mention}.\n"
                f"Silakan masuk game dan proses gift item ke member."
            )

    @commands.command(name="gift")
    async def gift_cmd(self, ctx):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        await ctx.message.delete()
        channel_id = ctx.channel.id
        if channel_id not in self.active_tickets:
            await ctx.send("Channel ini bukan tiket robux aktif.", delete_after=5)
            return
        ticket = self.active_tickets[channel_id]
        if not ticket.get("paid"):
            await ctx.send("Pembayaran belum dikonfirmasi!", delete_after=5)
            return

        member = ctx.guild.get_member(ticket["user_id"])
        now = datetime.datetime.now(datetime.timezone.utc)
        tanggal = now.strftime("%d %b %Y, %H:%M UTC")
        opened_at = datetime.datetime.fromisoformat(ticket["opened_at"])
        durasi_secs = int((now - opened_at).total_seconds())
        durasi_str = f"{durasi_secs // 3600}j {(durasi_secs % 3600) // 60}m {durasi_secs % 60}d"

        from utils.counter import next_ticket_number
        nomor = next_ticket_number()

        # Transcript
        from utils.transcript import generate as generate_transcript
        from utils.config import TRANSCRIPT_CHANNEL_ID
        transcript_ch = ctx.guild.get_channel(TRANSCRIPT_CHANNEL_ID)
        if transcript_ch:
            try:
                transcript_file = await generate_transcript(ctx.channel, STORE_NAME)
                await transcript_ch.send(
                    content=f"Transcript Robux Store — {ctx.channel.name}",
                    file=transcript_file
                )
            except Exception as e:
                print(f"[WARNING] Gagal kirim transcript robux: {e}")

        # Log transaksi
        log_ch = ctx.guild.get_channel(LOG_CHANNEL_ID)
        if log_ch:
            log_embed = discord.Embed(
                title=f"ROBUX STORE SUKSES — #{nomor:04d}",
                description=f"Item berhasil diberikan. Terima kasih telah berbelanja di Cellyn Store!",
                color=0xE91E63,
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )
            log_embed.add_field(name="Admin", value=f"{ctx.author.mention}\n`{ctx.author.id}`", inline=False)
            log_embed.add_field(name="Member", value=f"{member.mention if member else ticket['user_id']}\n`{ticket['user_id']}`", inline=False)
            log_embed.add_field(name="Item", value=f"{ticket['item_name']} ({ticket['robux']} Robux)", inline=False)
            log_embed.add_field(name="Rate", value=f"Rp {ticket['rate']:,}/Robux", inline=False)
            log_embed.add_field(name="Total", value=f"Rp {ticket['total']:,}", inline=False)
            log_embed.add_field(name="Metode Pembayaran", value=ticket.get("payment_method", "-"), inline=False)
            log_embed.set_thumbnail(url="https://i.imgur.com/CWtUCzj.png")
            log_embed.set_footer(text=f"{STORE_NAME}")
            await log_ch.send(embed=log_embed)

        await ctx.channel.send(
            f"Item berhasil diberikan. Terima kasih telah berbelanja di {STORE_NAME}!\n"
            f"Tiket ditutup dalam 5 detik."
        )
        # Log transaksi
        try:
            from utils.db import log_transaction
            log_transaction(
                layanan="robux",
                nominal=ticket.get("total", 0) or 0,
                item=f"{ticket.get('item_name','-')} ({ticket.get('robux',0)} Robux)",
                admin_id=ctx.author.id,
                user_id=ticket.get("user_id"),
                closed_at=now,
                durasi_detik=durasi_secs
            )
        except Exception as e:
            print(f"[LOG] Gagal log transaksi robux: {e}")
        delete_robux_ticket(channel_id)
        del self.active_tickets[channel_id]
        import asyncio
        await asyncio.sleep(5)
        await ctx.channel.delete()

    @commands.command(name="tolak")
    async def tolak_cmd(self, ctx, *, alasan: str = None):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        await ctx.message.delete()
        channel_id = ctx.channel.id
        if channel_id not in self.active_tickets:
            await ctx.send("Channel ini bukan tiket robux aktif.", delete_after=5)
            return
        ticket = self.active_tickets[channel_id]
        member = ctx.guild.get_member(ticket["user_id"])
        alasan_str = alasan if alasan else "Tidak ada alasan"
        await ctx.channel.send(
            f"Tiket dibatalkan oleh {ctx.author.mention}.\n"
            f"Alasan: {alasan_str}\n"
            f"Channel akan dihapus dalam 5 detik."
        )
        delete_robux_ticket(channel_id)
        del self.active_tickets[channel_id]
        import asyncio
        await asyncio.sleep(5)
        await ctx.channel.delete()

    @commands.command(name="catalog")
    async def catalog_cmd(self, ctx):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        await ctx.message.delete()
        await self.refresh_catalog()
        await ctx.send("Catalog dikirim!", delete_after=5)

async def setup(bot):
    await bot.add_cog(RobuxStore(bot))
    bot.add_view(CategoryView())
    print("Cog RobuxStore siap.")
