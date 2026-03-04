import discord
from discord.ext import commands
import asyncio
import datetime
from utils.fee import hitung_fee, format_nominal
from utils.tickets import save_tickets, load_tickets
from utils.transcript import generate as generate_transcript
from utils.config import (
    GUILD_ID, MIDMAN_CHANNEL_ID, ADMIN_ROLE_ID,
    TRANSCRIPT_CHANNEL_ID, LOG_CHANNEL_ID, STORE_NAME
)
from cogs.views import MidmanMainView, AdminSetupView, TradeFinishView

class Midman(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_tickets = {}

    @commands.Cog.listener()
    async def on_ready(self):
        guild = self.bot.get_guild(GUILD_ID)
        if guild:
            await load_tickets(guild, self.active_tickets)
        self.bot.add_view(MidmanMainView())
        self.bot.add_view(AdminSetupView())
        self.bot.add_view(TradeFinishView())
        print("Cog Midman siap.")

    @commands.command(name="open")
    @commands.has_role(ADMIN_ROLE_ID)
    async def open_cmd(self, ctx):
        try:
            await ctx.message.delete()
        except:
            pass
        ch = ctx.guild.get_channel(MIDMAN_CHANNEL_ID)

        # Hapus semua pesan bot lama di channel
        async for msg in ch.history(limit=50):
            if msg.author == self.bot.user:
                try:
                    await msg.delete()
                except:
                    pass

        embed = discord.Embed(
            title=f"MIDMAN TRADE — {STORE_NAME}",
            description=(
                "Gunakan layanan middleman kami untuk memastikan\n"
                "transaksi item game kamu berjalan aman dan terpercaya.\n\n"
                "**Cara pakai:**\n"
                "1. Klik tombol di bawah untuk membuka tiket\n"
                "2. Isi form — item kamu dan item yang kamu minta\n"
                "3. Tunggu admin bergabung dan menambahkan pihak 2\n"
                "4. Fee dibayar oleh pihak yang disepakati — admin akan konfirmasi\n"
                "5. Ikuti instruksi admin di dalam tiket\n\n"
                "Klik tombol di bawah untuk memulai."
            ),
            color=0x5865F2
        )
        embed.set_thumbnail(url="https://i.imgur.com/z4nrBHl.png")
        embed.set_footer(text=STORE_NAME)
        await ch.send(embed=embed, view=MidmanMainView())
        await ctx.send(f"Embed dikirim ke {ch.mention}", delete_after=5)

    @commands.command(name="acc")
    @commands.has_role(ADMIN_ROLE_ID)
    async def acc(self, ctx):
        ticket = self.active_tickets.get(ctx.channel.id)
        if not ticket:
            await ctx.message.delete()
            return
        try:
            await ctx.message.delete()
        except:
            pass
        ticket["closed_at"] = datetime.datetime.now(datetime.timezone.utc)
        p1 = ticket.get("pihak1")
        p2 = ticket.get("pihak2")
        adm = ticket.get("admin")
        if not p2 or not adm:
            await ctx.send("Tiket belum di-setup penuh oleh admin. Tidak bisa dikonfirmasi.", ephemeral=False)
            return
        fee_int = ticket.get("fee_final", 0)
        fee_str_log = format_nominal(fee_int) if fee_int else "-"
        ticket_num = str(ticket.get("ticket_number", 0)).zfill(4)
        opened_at = ticket.get("opened_at")
        closed_at = ticket.get("closed_at")
        durasi = "-"
        if opened_at and closed_at:
            delta = closed_at - opened_at
            total = int(delta.total_seconds())
            jam = total // 3600
            menit = (total % 3600) // 60
            detik = total % 60
            if jam > 0:
                durasi = f"{jam} jam {menit} menit"
            elif menit > 0:
                durasi = f"{menit} menit {detik} detik"
            else:
                durasi = f"{detik} detik"
        dibuka_str = opened_at.strftime("%d %b %Y, %H:%M UTC") if opened_at else "-"
        ditutup_str = closed_at.strftime("%d %b %Y, %H:%M UTC") if closed_at else "-"
        log_text = (
            f"<a:bell:1456430498757873797> **MIDMAN TRADE SUKSES — #{ticket_num}**\n"
            f"\u200b\n"
            f"| Midman  : {adm.mention}\n"
            f"| Pihak 1 : {p1.mention} | {p1.id} ({ticket['item_p1']})\n"
            f"| Pihak 2 : {p2.mention if p2 else '-'} | {p2.id if p2 else '-'} ({ticket['item_p2']})\n"
            f"| Fee     : {fee_str_log}\n"
            f"\u200b\n"
            f"| Dibuka  : {dibuka_str}\n"
            f"| Ditutup : {ditutup_str}\n"
            f"| Durasi  : {durasi}\n"
            f"\u200b\n"
            f"Transaksi telah selesai dan aman. Terima kasih telah menggunakan jasa midman {STORE_NAME}."
        )
        await ctx.send("Admin telah mengkonfirmasi bahwa trade selesai dan kedua pihak telah menerima item masing-masing. Tiket ditutup dalam 5 detik.")
        await asyncio.sleep(5)
        transcript_file = await generate_transcript(ctx.channel, STORE_NAME)
        log_ch = ctx.guild.get_channel(LOG_CHANNEL_ID)
        if log_ch:
            await log_ch.send(content=log_text)
        transcript_ch = ctx.guild.get_channel(TRANSCRIPT_CHANNEL_ID)
        if transcript_ch:
            await transcript_ch.send(
                content=f"Transcript #{ticket_num} — {ctx.channel.name}",
                file=transcript_file
            )
        del self.active_tickets[ctx.channel.id]
        save_tickets(self.active_tickets)
        await ctx.channel.delete()

    @commands.command(name="cancel")
    @commands.has_role(ADMIN_ROLE_ID)
    async def cancel(self, ctx):
        ticket = self.active_tickets.get(ctx.channel.id)
        if not ticket:
            await ctx.message.delete()
            await ctx.send("Channel ini bukan tiket aktif.", delete_after=5)
            return
        try:
            await ctx.message.delete()
        except:
            pass
        await ctx.send("Transaksi dibatalkan oleh admin — tiket akan ditutup dalam 5 detik.")
        await asyncio.sleep(5)
        if ctx.channel.id in self.active_tickets:
            del self.active_tickets[ctx.channel.id]
            save_tickets(self.active_tickets)
        await ctx.channel.delete()

    @commands.command(name="fee")
    async def fee(self, ctx, nominal: str):
        try:
            await ctx.message.delete()
        except:
            pass
        try:
            angka = int(nominal.replace(".", "").replace(",", "").replace("k", "000").replace("K", "000"))
        except ValueError:
            await ctx.send("Format salah. Contoh: !fee 50000 atau !fee 50k")
            return
        result = hitung_fee(angka)
        if result is None:
            await ctx.send("Nominal terlalu kecil. Minimal Rp 1.000.")
            return
        embed = discord.Embed(title="Kalkulator Fee Midman", color=0x5865F2)
        embed.add_field(name="Nominal", value=format_nominal(angka), inline=True)
        embed.add_field(name="Fee", value=format_nominal(result), inline=True)
        embed.add_field(name="Total Bayar", value=format_nominal(angka + result), inline=True)
        embed.set_footer(text=STORE_NAME)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Midman(bot))
