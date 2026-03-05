import discord
import datetime
import asyncio
from discord.ext import commands
from utils.config import (
    ADMIN_ROLE_ID, VILOG_CHANNEL_ID, LOG_CHANNEL_ID,
    TICKET_CATEGORY_ID, STORE_NAME, ERROR_LOG_CHANNEL_ID
)
from utils.vilog_db import load_vilog_tickets, save_vilog_ticket, delete_vilog_ticket
from utils.transcript import generate as generate_transcript
from utils.config import TRANSCRIPT_CHANNEL_ID

THUMBNAIL = "https://i.imgur.com/CWtUCzj.png"

BOOST_OPTIONS = {
    "1": {"nama": "X8 6 JAM", "robux": 1300},
    "2": {"nama": "X8 12 JAM", "robux": 1890},
    "3": {"nama": "X8 24 JAM", "robux": 3100},
}

class VilogFormModal(discord.ui.Modal, title="Form Boost Via Login"):
    username = discord.ui.TextInput(label="Username Roblox", placeholder="Masukkan username Roblox kamu")
    password = discord.ui.TextInput(label="Password", placeholder="Masukkan password akun kamu")
    pilihan = discord.ui.TextInput(
        label="Pilihan Boost (ketik 1/2/3)",
        placeholder="1 = X8 6Jam | 2 = X8 12Jam | 3 = X8 24Jam"
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

        ticket = {
            "channel_id": channel.id,
            "user_id": user.id,
            "username_roblox": self.username.value,
            "password": self.password.value,
            "boost": boost,
            "metode": metode_val,
            "nominal": None,
            "admin_id": None,
            "opened_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
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
        embed.add_field(name="\u200b", value=(
            f"Hallo, Selamat datang\n"
            f"Member   : {user.mention}\n"
            f"Username : ||{usn}||\n"
            f"Password : ||{pwd}||\n"
            f"Item     : {boost['nama']} ({boost['robux']} Robux)\n"
            f"Metode   : {metode_val}\n"
            f"Status   : Sesi berlangsung\n"
            f"──────────────────────────────\n"
            f"Admin harap konfirmasi dan tagih harga kepada member berdasarkan jumlah Robux × rate pasar yang berlaku saat transaksi dilakukan.\n"
            f"Contoh : 1200 (Robux) X 90 (Rate) = Total\n"
            f"──────────────────────────────\n"
            f"**!batalin** untuk cancel tiket.\n"
            f"**!selesai** (**masukan angka total pembayaran**) di akhir sesi jika **transaksi sudah selesai**."
        ), inline=False)
        embed.set_thumbnail(url=THUMBNAIL)
        embed.set_footer(text=STORE_NAME)

        if staff_role:
            await channel.send(content=staff_role.mention, embed=embed)
        else:
            await channel.send(embed=embed)

        await interaction.followup.send(f"Tiket berhasil dibuat di {channel.mention}!", ephemeral=True)


class VilogMainView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="BELI", style=discord.ButtonStyle.primary, custom_id="open_vilog")
    async def open_vilog(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(VilogFormModal())


class Vilog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_vilog = load_vilog_tickets()

    @commands.command(name="vilog")
    async def vilog_cmd(self, ctx):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        await ctx.message.delete()
        ch = ctx.guild.get_channel(VILOG_CHANNEL_ID)
        if not ch:
            await ctx.send("Channel vilog tidak ditemukan!", delete_after=5)
            return

        async for msg in ch.history(limit=50):
            if msg.author == self.bot.user:
                try:
                    await msg.delete()
                except Exception:
                    pass

        embed = discord.Embed(
            title=f"Boost Server Via Login — {STORE_NAME}",
            description=(
                "**Pilihan Boost:**\n"
                "1. X8 6 JAM — 1300 Robux\n"
                "2. X8 12 JAM — 1890 Robux\n"
                "3. X8 24 JAM — 3100 Robux\n\n"
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
                "• cek harga dengan cara: Jumlah robux X rate = Total\n"
                "Contoh : 2500 (robux)X (rate) 90= Total.\n"
                "──────────────────────────────\n"
                "!vilog untuk refresh."
            ),
            color=0xE67E22
        )
        embed.set_thumbnail(url=THUMBNAIL)
        embed.set_footer(text=STORE_NAME)
        await ch.send(embed=embed, view=VilogMainView())
        await ctx.send(f"Embed vilog dikirim ke {ch.mention}", delete_after=5)

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

        log_text = (
            f"**PEMBELIAN BOOST VILOG SUKSES**\n"
            f"\u200b\n"
            f"| Admin   : {ctx.author.mention} | {ctx.author.id}\n"
            f"| Member  : {member.mention if member else ticket['user_id']} | {ticket['user_id']}\n"
            f"| Item    : {boost['nama']} ({boost['robux']} Robux)\n"
            f"| Nominal : Rp {nominal_int:,}\n"
            f"| Tanggal : {tanggal}\n"
            f"\u200b\n"
            f"Transaksi selesai dan telah diverifikasi oleh admin. Terima kasih telah berbelanja di Cellyn Store."
        )

        await ctx.send(
            "Boost berhasil diaktifkan. Tiket ditutup dalam 5 detik.\n"
            "Mohon segera ganti password akun kamu untuk keamanan."
        )
        await asyncio.sleep(5)

        log_ch = ctx.guild.get_channel(LOG_CHANNEL_ID)
        if log_ch:
            await log_ch.send(content=log_text)

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

async def setup(bot):
    await bot.add_cog(Vilog(bot))
    print("Cog Vilog siap.")
