import discord
from discord.ext import commands
import asyncio
import datetime
from utils.fee import hitung_fee, format_nominal
from utils.tickets import save_tickets, load_tickets
from utils.transcript import generate as generate_transcript
from utils.config import (
    GUILD_ID, MIDMAN_CHANNEL_ID, ADMIN_ROLE_ID,
    TRANSCRIPT_CHANNEL_ID, LOG_CHANNEL_ID, STORE_NAME, BACKUP_CHANNEL_ID, ERROR_LOG_CHANNEL_ID
)
from cogs.views import MidmanMainView, AdminSetupView, TradeFinishView
from utils.backup import do_backup, do_restore
from discord.ext import tasks

class Midman(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_tickets = {}
        self.restored = False

    def cog_unload(self):
        self.ticket_timeout_check.cancel()
        self.auto_backup.cancel()

    @tasks.loop(hours=6)
    async def auto_backup(self):
        await do_backup(self.bot, BACKUP_CHANNEL_ID)

    @auto_backup.before_loop
    async def before_auto_backup(self):
        await self.bot.wait_until_ready()

    @tasks.loop(hours=6)
    async def ticket_timeout_check(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        for ch_id, ticket in list(self.active_tickets.items()):
            guild = self.bot.get_guild(GUILD_ID)
            if not guild:
                continue
            channel = guild.get_channel(ch_id)
            if not channel:
                continue
            last_msg_time = None
            async for msg in channel.history(limit=1):
                last_msg_time = msg.created_at
            check_time = last_msg_time or ticket.get("opened_at")
            if not check_time:
                continue
            if check_time.tzinfo is None:
                check_time = check_time.replace(tzinfo=datetime.timezone.utc)
            delta = (now - check_time).total_seconds() / 3600
            if delta >= 6:
                embed = discord.Embed(
                    title="⏰ PENGINGAT TIKET",
                    description=(
                        f"Tiket ini tidak ada aktivitas selama **{int(delta)} jam**.\n\n"
                        f"Segera selesaikan proses trade atau hubungi admin.\n"
                        f"Tiket akan terus mendapat pengingat setiap 6 jam."
                    ),
                    color=0xFFA500
                )
                embed.set_footer(text=STORE_NAME)
                adm = ticket.get("admin")
                p1 = ticket.get("pihak1")
                p2 = ticket.get("pihak2")
                mentions = " ".join(filter(None, [
                    adm.mention if adm else None,
                    p1.mention if p1 else None,
                    p2.mention if p2 else None
                ]))
                await channel.send(content=mentions, embed=embed)

    @ticket_timeout_check.before_loop
    async def before_timeout_check(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.MissingRole):
            return
        if isinstance(error, commands.CommandNotFound):
            return
        err_ch = ctx.guild.get_channel(ERROR_LOG_CHANNEL_ID)
        if err_ch:
            await err_ch.send(
                f"ERROR LOG\n"
                f"Error pada command `{ctx.command}` oleh {ctx.author.mention}:\n"
                f"`{error}`"
            )
        print(f"[ERROR] {ctx.command}: {error}")

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.restored:
            await do_restore(self.bot, BACKUP_CHANNEL_ID)
            from utils.db import init_db
            init_db()
            self.restored = True

        guild = self.bot.get_guild(GUILD_ID)
        if guild:
            await load_tickets(guild, self.active_tickets)
        self.bot.add_view(MidmanMainView())
        self.bot.add_view(AdminSetupView())
        self.bot.add_view(TradeFinishView())
        print("Cog Midman siap.")
        import os
        if os.path.exists(".update_channel"):
            with open(".update_channel") as f:
                ch_id = int(f.read().strip())
            os.remove(".update_channel")
            ch = self.bot.get_channel(ch_id)
            if ch:
                await ch.send("Bot berhasil restart dan online kembali!")

    @commands.command(name="open")
    async def open_cmd(self, ctx):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        try:
            await ctx.message.delete()
        except Exception as e:
            print(f"[WARNING] cogs/midman.py: {e}")
            pass
        ch = ctx.guild.get_channel(MIDMAN_CHANNEL_ID)

        # Hapus semua pesan bot lama di channel
        async for msg in ch.history(limit=50):
            if msg.author == self.bot.user:
                try:
                    await msg.delete()
                except Exception as e:
                    print(f"[WARNING] cogs/midman.py: {e}")
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
        embed.set_thumbnail(url="https://i.imgur.com/CWtUCzj.png")
        embed.set_footer(text=STORE_NAME)
        await ch.send(embed=embed, view=MidmanMainView())
        await ctx.send(f"Embed dikirim ke {ch.mention}", delete_after=5)

    @commands.command(name="acc")
    async def acc(self, ctx):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        ticket = self.active_tickets.get(ctx.channel.id)
        if not ticket:
            await ctx.message.delete()
            return
        try:
            await ctx.message.delete()
        except Exception as e:
            print(f"[WARNING] cogs/midman.py: {e}")
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
            f"| Diverifikasi oleh : {ticket.get('verified_by').mention if ticket.get('verified_by') else adm.mention}\n"
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

    @commands.command(name="batal")
    async def cancel(self, ctx, *, alasan: str = "Tidak ada alasan diberikan."):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        ticket = self.active_tickets.get(ctx.channel.id)
        if not ticket:
            await ctx.message.delete()
            await ctx.send("Channel ini bukan tiket aktif.", delete_after=5)
            return
        try:
            await ctx.message.delete()
        except Exception as e:
            print(f"[WARNING] cogs/midman.py: {e}")
            pass
        embed = discord.Embed(
            title="❌ TRANSAKSI DIBATALKAN",
            color=0xFF0000
        )
        embed.add_field(name="Dibatalkan oleh", value=ctx.author.mention, inline=True)
        embed.add_field(name="Alasan", value=alasan, inline=False)
        embed.add_field(name="", value="Tiket akan ditutup dalam 5 detik.", inline=False)
        embed.set_footer(text=STORE_NAME)
        p1 = ticket.get("pihak1")
        p2 = ticket.get("pihak2")
        mentions = " ".join(filter(None, [
            p1.mention if p1 else None,
            p2.mention if p2 else None
        ]))
        await ctx.send(content=mentions if mentions else None, embed=embed)
        await asyncio.sleep(5)
        if ctx.channel.id in self.active_tickets:
            del self.active_tickets[ctx.channel.id]
            save_tickets(self.active_tickets)
        await ctx.channel.delete()

    @commands.command(name="update")
    async def update(self, ctx):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        await ctx.send("Bot akan restart dan mengunduh update terbaru dari GitHub...")
        with open(".update_channel", "w") as f:
            f.write(str(ctx.channel.id))
        await asyncio.sleep(2)
        import sys
        sys.exit(0)

    @commands.command(name="ping")
    async def ping(self, ctx):
        latency = round(self.bot.latency * 1000)
        await ctx.send(f"Pong! Latency: {latency}ms")

    @commands.command(name="fee")
    async def fee(self, ctx, nominal: str):
        try:
            await ctx.message.delete()
        except Exception as e:
            print(f"[WARNING] cogs/midman.py: {e}")
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
        embed.set_thumbnail(url="https://i.imgur.com/CWtUCzj.png")
        embed.set_footer(text=STORE_NAME)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Midman(bot))
