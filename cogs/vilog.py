import discord
import datetime
import asyncio
from discord.ext import commands, tasks
from utils.config import (
    ADMIN_ROLE_ID, VILOG_CHANNEL_ID, LOG_CHANNEL_ID,
    TICKET_CATEGORY_ID, STORE_NAME, ERROR_LOG_CHANNEL_ID, GUILD_ID
)
from utils.db import get_conn
from utils.vilog_db import load_vilog_tickets, save_vilog_ticket, delete_vilog_ticket
from utils.counter import next_ticket_number
from utils.robux_db import save_bot_state, load_bot_state
from utils.transcript import generate as generate_transcript
from utils.config import TRANSCRIPT_CHANNEL_ID

THUMBNAIL = "https://i.imgur.com/CWtUCzj.png"

def load_boost_options():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, nama, robux FROM vilog_boosts WHERE active = 1 ORDER BY id")
    rows = c.fetchall()
    conn.close()
    return {str(i+1): {"nama": r["nama"], "robux": r["robux"]} for i, r in enumerate(rows)}

BOOST_OPTIONS = load_boost_options()

class VilogFormModal(discord.ui.Modal, title="Form Boost Via Login"):
    username = discord.ui.TextInput(label="Username Roblox", placeholder="Masukkan username Roblox kamu")
    password = discord.ui.TextInput(label="Password", placeholder="Masukkan password akun kamu")
    pilihan = discord.ui.TextInput(
        label="Pilihan Boost (ketik nomor)",
        placeholder="Ketik nomor pilihan boost"
    )
    metode = discord.ui.TextInput(
        label="Metode Bayar (QRIS/DANA/BANK)",
        placeholder="Ketik QRIS, DANA, atau BANK"
    )

    async def on_submit(self, interaction: discord.Interaction):
        pilihan_val = self.pilihan.value.strip()
        if pilihan_val not in BOOST_OPTIONS:
            await interaction.response.send_message("Pilihan boost tidak valid! Ketik 1, 2, atau 3.", ephemeral=True)
            return

        boost = BOOST_OPTIONS[pilihan_val]
        metode_val = self.metode.value.strip().upper()
        if metode_val not in ["QRIS", "DANA", "BANK"]:
            await interaction.response.send_message("Metode bayar tidak valid! Ketik QRIS, DANA, atau BANK.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        user = interaction.user

        # Cek tiket aktif
        cog = interaction.client.cogs.get("Vilog")
        for ch_id, t in cog.active_vilog.items():
            if t["user_id"] == user.id:
                existing = guild.get_channel(ch_id)
                if existing:
                    await interaction.followup.send(
                        f"Kamu masih punya tiket aktif di {existing.mention}!",
                        ephemeral=True
                    )
                    return

        category = guild.get_channel(TICKET_CATEGORY_ID)
        staff_role = guild.get_role(ADMIN_ROLE_ID)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel = await guild.create_text_channel(
            name=f"vilog-{user.name}",
            category=category,
            overwrites=overwrites
        )

        from cogs.robux import get_rate as _get_rate
        _rate = _get_rate()

        ticket = {
            "channel_id": channel.id,
            "user_id": user.id,
            "username_roblox": self.username.value,
            "password": self.password.value,
            "boost": boost,
            "metode": metode_val,
            "payment_method": metode_val,
            "rate": _rate,
            "nominal": None,
            "admin_id": None,
            "opened_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "last_activity": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }

        cog = interaction.client.cogs.get("Vilog")
        cog.active_vilog[channel.id] = ticket
        save_vilog_ticket(ticket)

        embed = discord.Embed(
            title=f"BOOST VIA LOGIN — {STORE_NAME}",
            color=0xE67E22,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        usn = self.username.value
        pwd = self.password.value
        _total = boost['robux'] * _rate if _rate else 0
        _total_str = f"Rp {_total:,}" if _rate else "Rate belum diset"
        _rate_str = f"Rp {_rate:,}/Robux" if _rate else "Belum diset"
        embed.add_field(name="\u200b", value=(
            f"Hallo, Selamat datang\n"
            f"Member   : {user.mention}\n"
            f"Username : ||{usn}||\n"
            f"Password : ||{pwd}||\n"
            f"──────────────────────────────\n"
            f"Item     : {boost['nama']} ({boost['robux']} Robux)\n"
            f"Rate     : {_rate_str}\n"
            f"Total    : {_total_str}\n"
            f"Metode   : {metode_val}\n"
            f"Status   : Sesi berlangsung\n"
            f"──────────────────────────────\n"
            f"**!batalin** untuk cancel tiket.\n"
            f"**!selesai** (**masukan angka total pembayaran**) di akhir sesi jika **transaksi sudah selesai**.\n"
            f"──────────────────────────────\n"
            f"Tiket yang tidak aktif selama 2 jam akan otomatis ditutup dan transaksi dianggap batal."
        ), inline=False)
        embed.set_thumbnail(url=THUMBNAIL)
        embed.set_footer(text=STORE_NAME)

        if staff_role:
            await channel.send(content=staff_role.mention, embed=embed)
        else:
            await channel.send(embed=embed)

        await interaction.followup.send(f"Tiket berhasil dibuat di {channel.mention}!", ephemeral=True)


class VilogInfoView(discord.ui.View):
    """Info layanan Vilog + tombol Lanjutkan/Batal."""
    def __init__(self):
        super().__init__(timeout=120)

    @discord.ui.button(label="✅ Lanjutkan", style=discord.ButtonStyle.success, custom_id="vilog_info_lanjut")
    async def lanjutkan(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(VilogFormModal())

    @discord.ui.button(label="❌ Batal", style=discord.ButtonStyle.danger, custom_id="vilog_info_batal")
    async def batal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Dibatalkan.", embed=None, view=None)


class VilogMainView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="BELI", style=discord.ButtonStyle.primary, custom_id="open_vilog")
    async def open_vilog(self, interaction: discord.Interaction, button: discord.ui.Button):
        from utils.service_info import get_service_info, build_info_embed
        info = get_service_info("vilog")
        has_info = any([info["description"], info["terms"], info["payment_info"]])
        if has_info:
            embed = build_info_embed("Boost Via Login", info, 0xE67E22)
            await interaction.response.send_message(embed=embed, view=VilogInfoView(), ephemeral=True)
        else:
            await interaction.response.send_modal(VilogFormModal())


class Vilog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_vilog = load_vilog_tickets()
        _id = load_bot_state("vilog_embed_message_id")
        self.embed_message_id = int(_id) if _id else None
        self.auto_close_task.start()

    def cog_unload(self):
        self.auto_close_task.cancel()

    @tasks.loop(minutes=10)
    async def auto_close_task(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            return
        for ch_id, ticket in list(self.active_vilog.items()):
            last = ticket.get("last_activity") or ticket.get("opened_at")
            if not last:
                continue
            last_dt = datetime.datetime.fromisoformat(last)
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=datetime.timezone.utc)
            elapsed = (now - last_dt).total_seconds()
            channel = guild.get_channel(ch_id)
            if elapsed >= 7200:
                delete_vilog_ticket(ch_id)
                if ch_id in self.active_vilog:
                    del self.active_vilog[ch_id]
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
                            "Segera ketik `!selesai` jika selesai, atau `!batalin` jika dibatalkan.\n\n"
                            "Tiket akan otomatis ditutup dalam **1 jam lagi** (<t:" + str(int(__import__("time").time()) + 3600) + ":R>)."
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
                save_vilog_ticket(ticket)

    @auto_close_task.before_loop
    async def before_auto_close(self):
        await self.bot.wait_until_ready()

    async def refresh_embed(self, guild):
        ch = guild.get_channel(VILOG_CHANNEL_ID)
        if not ch:
            return
        from cogs.robux import get_rate
        rate = get_rate()
        rate_str = f"Rp {rate:,}/Robux" if rate > 0 else "Belum diset"

        def harga_boost(robux):
            if rate == 0:
                return "Belum diset"
            return f"Rp {robux * rate:,}"

        embed = discord.Embed(
            title=f"Boost Server Via Login — {STORE_NAME}",
            description=(
                f"**Pilihan Boost:**\n"
                f"1. X8 6 JAM — 1300 Robux — **{harga_boost(1300)}**\n"
                f"2. X8 12 JAM — 1890 Robux — **{harga_boost(1890)}**\n"
                f"3. X8 24 JAM — 3100 Robux — **{harga_boost(3100)}**\n\n"
                f"Rate saat ini: **{rate_str}**\n\n"
                "**Cara pakai:**\n"
                "1. Klik tombol BELI\n"
                "2. Isi form dengan data akun dan pilihan boost\n"
                "3. Tunggu admin menghubungi kamu di tiket\n"
                "4. Ikuti instruksi Admin didalam tiket\n\n"
                "**Note :**\n"
                "• Admin login ke akun anda untuk proses Boost.\n"
                "• Pastikan email & password benar agar proses cepat\n"
                "• Harga dapat berubah sewaktu-waktu\n"
                "• Semua pembayaran diterima (QRIS/DANA/BCA)\n"
                "──────────────────────────────\n"
                "!vilog untuk refresh."
            ),
            color=0xE67E22
        )
        embed.set_thumbnail(url=THUMBNAIL)
        embed.set_footer(text=STORE_NAME)

        if self.embed_message_id:
            try:
                msg = await ch.fetch_message(self.embed_message_id)
                await msg.edit(embed=embed)
                return
            except Exception:
                pass
        async for msg in ch.history(limit=20):
            if msg.author == guild.me:
                try:
                    await msg.delete()
                except Exception:
                    pass
        sent = await ch.send(embed=embed, view=VilogMainView())
        self.embed_message_id = sent.id
        save_bot_state("vilog_embed_message_id", str(sent.id))

    @commands.command(name="vilog")
    async def vilog_cmd(self, ctx):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        await ctx.message.delete()
        ch = ctx.guild.get_channel(VILOG_CHANNEL_ID)
        if not ch:
            await ctx.send("Channel vilog tidak ditemukan!", delete_after=5)
            return
        _id = load_bot_state("vilog_embed_message_id")
        self.embed_message_id = int(_id) if _id else None
        await self.refresh_embed(ctx.guild)
        await ctx.send(f"Embed vilog dikirim ke {ch.mention}", delete_after=5)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        if message.channel.id in self.active_vilog:
            self.active_vilog[message.channel.id]["last_activity"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            save_vilog_ticket(self.active_vilog[message.channel.id])

    @commands.command(name="selesai")
    async def selesai(self, ctx, *, nominal: str = None):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        await ctx.message.delete()
        ticket = self.active_vilog.get(ctx.channel.id)
        if not ticket:
            await ctx.send("Channel ini bukan tiket vilog aktif.", delete_after=5)
            return
        if not nominal:
            await ctx.send("Gunakan: `!selesai <nominal>` contoh: `!selesai 125000`", delete_after=5)
            return

        try:
            nominal_int = int(nominal.replace(".", "").replace(",", ""))
        except ValueError:
            await ctx.send("Nominal tidak valid!", delete_after=5)
            return

        ticket["nominal"] = nominal_int
        ticket["admin_id"] = ctx.author.id
        save_vilog_ticket(ticket)

        guild = ctx.guild
        member = guild.get_member(ticket["user_id"])
        boost = ticket["boost"]
        opened_at = datetime.datetime.fromisoformat(ticket["opened_at"])
        closed_at = datetime.datetime.now(datetime.timezone.utc)
        tanggal = closed_at.strftime("%d %b %Y, %H:%M UTC")

        nomor_vilog = next_ticket_number()
        rate_vilog = ticket.get("rate") or ticket.get("rate_vilog")
        metode_vilog = ticket.get("payment_method") or ticket.get("metode", "-")
        log_embed = discord.Embed(
            title=f"BOOST VILOG SUKSES — #{nomor_vilog:04d}",
            description="Boost berhasil diaktifkan. Segera ganti password akun setelah sesi selesai.",
            color=0xE67E22,
            timestamp=closed_at
        )
        log_embed.add_field(name="Admin", value=f"{ctx.author.mention}\n`{ctx.author.id}`", inline=False)
        log_embed.add_field(name="Member", value=f"{member.mention if member else ticket['user_id']}\n`{ticket['user_id']}`", inline=False)
        log_embed.add_field(name="Item", value=f"{boost['nama']} ({boost['robux']} Robux)", inline=False)
        log_embed.add_field(name="Rate", value=f"Rp {rate_vilog:,}/Robux" if isinstance(rate_vilog, int) else str(rate_vilog), inline=False)
        log_embed.add_field(name="Nominal", value=f"Rp {nominal_int:,}", inline=False)
        log_embed.add_field(name="Metode Pembayaran", value=metode_vilog, inline=False)
        log_embed.set_thumbnail(url="https://i.imgur.com/CWtUCzj.png")
        log_embed.set_footer(text=f"{STORE_NAME}")

        await ctx.send(
            "Boost berhasil diaktifkan. Tiket ditutup dalam 5 detik.\n"
            "Mohon segera ganti password akun kamu untuk keamanan."
        )
        await asyncio.sleep(5)

        log_ch = ctx.guild.get_channel(LOG_CHANNEL_ID)
        if log_ch:
            await log_ch.send(embed=log_embed)

        transcript_ch = ctx.guild.get_channel(TRANSCRIPT_CHANNEL_ID)
        if transcript_ch:
            try:
                transcript_file = await generate_transcript(ctx.channel, STORE_NAME)
                await transcript_ch.send(
                    content=f"📄 Transcript Vilog — {ctx.channel.name}",
                    file=transcript_file
                )
            except Exception as e:
                print(f"[WARNING] Gagal kirim transcript vilog: {e}")

        # Log transaksi
        try:
            from utils.db import log_transaction
            opened_at_dt = datetime.datetime.fromisoformat(ticket["opened_at"]) if ticket.get("opened_at") else None
            durasi = int((closed_at - opened_at_dt).total_seconds()) if opened_at_dt else 0
            log_transaction(
                layanan="vilog",
                nominal=nominal_int,
                item=ticket.get("boost", {}).get("nama", "-"),
                admin_id=ctx.author.id,
                user_id=ticket.get("user_id"),
                closed_at=closed_at,
                durasi_detik=durasi
            )
        except Exception as e:
            print(f"[LOG] Gagal log transaksi vilog: {e}")
        # Assign Royal Customer
        try:
            royal_role = discord.utils.get(ctx.guild.roles, name="Royal Customer")
            if royal_role:
                for uid in [ticket.get("user_id")]:
                    if uid:
                        member = ctx.guild.get_member(uid)
                        if member and royal_role not in member.roles:
                            await member.add_roles(royal_role)
        except Exception as e:
            print(f"[ROLE] Gagal assign Royal Customer: {e}")
        delete_vilog_ticket(ctx.channel.id)
        del self.active_vilog[ctx.channel.id]
        await ctx.channel.delete()

    @commands.command(name="gagal")
    async def gagal(self, ctx, *, alasan: str = "Tidak ada alasan diberikan."):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        await ctx.message.delete()
        ticket = self.active_vilog.get(ctx.channel.id)
        if not ticket:
            await ctx.send("Channel ini bukan tiket vilog aktif.", delete_after=5)
            return

        guild = ctx.guild
        member = guild.get_member(ticket["user_id"])

        embed = discord.Embed(title="BOOST GAGAL", color=0xE67E22)
        embed.add_field(name="Dibatalkan oleh", value=ctx.author.mention, inline=True)
        embed.add_field(name="Alasan", value=alasan, inline=False)
        embed.add_field(name="", value="Tiket akan ditutup dalam 5 detik.", inline=False)
        embed.set_thumbnail(url=THUMBNAIL)
        embed.set_footer(text=STORE_NAME)

        mentions = member.mention if member else ""
        await ctx.send(content=mentions if mentions else None, embed=embed)
        await asyncio.sleep(5)

        transcript_ch = ctx.guild.get_channel(TRANSCRIPT_CHANNEL_ID)
        if transcript_ch:
            try:
                transcript_file = await generate_transcript(ctx.channel, STORE_NAME)
                await transcript_ch.send(
                    content=f"📄 Transcript Vilog — {ctx.channel.name}",
                    file=transcript_file
                )
            except Exception as e:
                print(f"[WARNING] Gagal kirim transcript vilog: {e}")

        delete_vilog_ticket(ctx.channel.id)
        del self.active_vilog[ctx.channel.id]
        await ctx.channel.delete()


    @commands.command(name="batalin")
    async def batalin(self, ctx, *, alasan: str = "Tidak ada alasan diberikan."):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        await ctx.message.delete()
        ticket = self.active_vilog.get(ctx.channel.id)
        if not ticket:
            await ctx.send("Channel ini bukan tiket vilog aktif.", delete_after=5)
            return
        guild = ctx.guild
        member = guild.get_member(ticket["user_id"])
        embed = discord.Embed(title="BOOST DIBATALKAN", color=0xE67E22)
        embed.add_field(name="Dibatalkan oleh", value=ctx.author.mention, inline=True)
        embed.add_field(name="Alasan", value=alasan, inline=False)
        embed.add_field(name="", value="Tiket akan ditutup dalam 5 detik.", inline=False)
        embed.set_thumbnail(url=THUMBNAIL)
        embed.set_footer(text=STORE_NAME)
        mentions = member.mention if member else ""
        await ctx.send(content=mentions if mentions else None, embed=embed)
        await asyncio.sleep(5)
        delete_vilog_ticket(ctx.channel.id)
        del self.active_vilog[ctx.channel.id]
        await ctx.channel.delete()

async def setup(bot):
    await bot.add_cog(Vilog(bot))
    bot.add_view(VilogMainView())
    print("Cog Vilog siap.")
