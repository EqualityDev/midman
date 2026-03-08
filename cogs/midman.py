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

    @tasks.loop(minutes=10)
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
            if isinstance(check_time, str):
                check_time = datetime.datetime.fromisoformat(check_time)
            if check_time.tzinfo is None:
                check_time = check_time.replace(tzinfo=datetime.timezone.utc)
            delta = (now - check_time).total_seconds()
            if delta >= 7200:
                try:
                    await channel.send(
                        "Tiket ini otomatis ditutup karena tidak ada aktivitas selama 2 jam. "
                        "Transaksi dianggap batal. Channel akan dihapus dalam 10 detik."
                    )
                    await asyncio.sleep(10)
                    await channel.delete()
                except Exception:
                    pass
                del self.active_tickets[ch_id]
                save_tickets(self.active_tickets)
            elif delta >= 3600 and not ticket.get("warned"):
                try:
                    warn_embed = discord.Embed(title="PERINGATAN TIKET", color=0xFFA500)
                    warn_embed.add_field(name="\u200b", value=(
                        "Tiket tidak ada aktivitas selama **1 jam**.\n\n"
                        "Segera ketik `!acc` jika selesai, atau `!batal` jika dibatalkan.\n\n"
                        "Tiket akan otomatis ditutup dalam **1 jam lagi**."
                    ), inline=False)
                    warn_embed.set_footer(text=STORE_NAME)
                    _p1 = ticket.get("pihak1")
                    _p2 = ticket.get("pihak2")
                    _adm = ticket.get("admin")
                    _mn = " ".join(filter(None, [
                        _p1.mention if _p1 else None,
                        _p2.mention if _p2 else None,
                        _adm.mention if _adm else None,
                    ]))
                    await channel.send(content=_mn, embed=warn_embed)
                except Exception:
                    pass
                ticket["warned"] = True
                save_tickets(self.active_tickets)

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
        self.bot.start_time = datetime.datetime.now(datetime.timezone.utc)
        print("Cog Midman siap.")
        import os
        if os.path.exists(".update_channel"):
            with open(".update_channel") as f:
                data = f.read().strip().split("|")
            os.remove(".update_channel")
            ch_id = int(data[0])
            ts = float(data[1]) if len(data) == 2 else datetime.datetime.now().timestamp()
            elapsed = datetime.datetime.now().timestamp() - ts
            if elapsed <= 120:
                await self.bot.wait_until_ready()
                await asyncio.sleep(3)
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
                "Transaksi item game kamu dengan aman dan terpercaya bersama Cellyn Store.\n"
                "Admin kami siap memastikan kedua pihak menukar item sesuai kesepakatan.\n\n"
                "**Cara pakai:**\n"
                "1. Klik tombol di bawah untuk membuka tiket\n"
                "2. Isi form — item kamu dan item yang kamu minta\n"
                "3. Tunggu admin bergabung dan menambahkan pihak 2\n"
                "4. Fee dibayar oleh pihak yang disepakati — admin akan konfirmasi\n"
                "5. Ikuti instruksi admin di dalam tiket"
            ),
            color=0x2ECC71
        )
        embed.add_field(
            name="📋 Daftar Fee Midman",
            value=(
                "```"
                "Nominal Trade        Fee\n"
                "─────────────────────────\n"
                "< Rp 10.000          Rp 1.500\n"
                "Rp 10.000 – 49.000   Rp 2.500\n"
                "Rp 50.000 – 99.000   Rp 4.500\n"
                "Rp 100.000 – 199.000 Rp 6.500\n"
                "Rp 200.000 – 499.000 Rp 10.000\n"
                "Rp 500.000 – 1 jt    Rp 15.000\n"
                "> Rp 1.000.000       Rp 20.000"
                "```"
            ),
            inline=False
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
        verified_by = ticket.get("verified_by")
        log_embed = discord.Embed(
            title=f"MIDMAN TRADE SUKSES — #{ticket_num}",
            description="Transaksi telah selesai dan aman. Kedua pihak telah menerima item masing-masing.",
            color=0x2ECC71,
            timestamp=closed_at
        )
        log_embed.add_field(name="Midman", value=f"{adm.mention}\n`{adm.id}`", inline=False)
        log_embed.add_field(name="Pihak 1", value=f"{p1.mention}\n`{p1.id}`", inline=False)
        log_embed.add_field(name="Pihak 2", value=f"{p2.mention if p2 else '-'}\n`{p2.id if p2 else '-'}`", inline=False)
        log_embed.add_field(name="Fee", value=fee_str_log, inline=False)
        log_embed.set_thumbnail(url="https://i.imgur.com/CWtUCzj.png")
        log_embed.set_footer(text=f"{STORE_NAME}")
        await ctx.send("Admin telah mengkonfirmasi bahwa trade selesai dan kedua pihak telah menerima item masing-masing. Tiket ditutup dalam 5 detik.")
        await asyncio.sleep(5)
        transcript_file = await generate_transcript(ctx.channel, STORE_NAME)
        log_ch = ctx.guild.get_channel(LOG_CHANNEL_ID)
        if log_ch:
            await log_ch.send(embed=log_embed)
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
        await ctx.message.delete()
        ticket = self.active_tickets.get(ctx.channel.id)
        if not ticket:
            await ctx.send("Channel ini bukan tiket aktif.", delete_after=5)
            return
        embed = discord.Embed(
            title="❌ TRANSAKSI DIBATALKAN",
            color=0xFF0000
        )
        embed.add_field(name="Dibatalkan oleh", value=ctx.author.mention, inline=True)
        embed.add_field(name="Alasan", value=alasan, inline=False)
        embed.add_field(name="", value="Tiket akan ditutup dalam 5 detik.", inline=False)
        embed.set_thumbnail(url="https://i.imgur.com/CWtUCzj.png")
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
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def update(self, ctx):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        await ctx.message.delete()
        active_count = len(self.active_tickets)
        if active_count > 0:
            confirm_msg = await ctx.send(
                f"Ada **{active_count} tiket aktif** saat ini. Update sekarang akan interrupt tiket yang sedang berjalan.\n"
                f"Ketik `!update confirm` untuk tetap update, atau biarkan saja untuk batal."
            )
            def check_confirm(m):
                return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() == '!update confirm'
            try:
                import asyncio as _asyncio
                await ctx.bot.wait_for('message', check=check_confirm, timeout=30)
                await confirm_msg.delete()
            except _asyncio.TimeoutError:
                await confirm_msg.edit(content="Update dibatalkan.")
                return

        await ctx.send("Mengunduh update dari GitHub...")
        # Simpan commit hash sebelum pull
        hash_proc = await asyncio.create_subprocess_shell(
            "git rev-parse HEAD",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        hash_out, _ = await hash_proc.communicate()
        old_hash = hash_out.decode().strip()
        proc = await asyncio.create_subprocess_shell(
            "git stash && git pull origin main",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        output = stdout.decode() or stderr.decode()
        await ctx.send(f"```\n{output[:1900]}\n```")
        if proc.returncode == 0:
            log_proc = await asyncio.create_subprocess_shell(
                f"git log {old_hash}..HEAD --oneline --no-merges",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            log_out, _ = await log_proc.communicate()
            changelog = log_out.decode().strip()
            if changelog:
                await ctx.send(f"**Changelog:**\n```\n{changelog[:1500]}\n```")
            else:
                await ctx.send("Tidak ada commit baru.")
            await ctx.send("Update selesai! Bot akan restart dalam 3 detik...")
            with open(".update_channel", "w") as f:
                f.write(str(ctx.channel.id))
            await asyncio.sleep(3)
            await self.bot.close()
        else:
            await ctx.send("Update gagal! Cek log di atas.")

    @commands.command(name="info")
    async def info(self, ctx):
        await ctx.message.delete()
        proc = await asyncio.create_subprocess_shell(
            "git rev-parse --short HEAD",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        out, _ = await proc.communicate()
        version = out.decode().strip()
        uptime = datetime.datetime.now(datetime.timezone.utc) - self.bot.start_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        msg = f"**Versi:** `{version}`\n**Uptime:** {hours} jam {minutes} menit {seconds} detik"
        await ctx.send(msg)

    @commands.command(name="ping")
    async def ping(self, ctx):
        await ctx.message.delete()
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
        embed = discord.Embed(title="Kalkulator Fee Midman", color=0x2ECC71)
        embed.add_field(name="Nominal", value=format_nominal(angka), inline=True)
        embed.add_field(name="Fee", value=format_nominal(result), inline=True)
        embed.add_field(name="Total Bayar", value=format_nominal(angka + result), inline=True)
        embed.set_thumbnail(url="https://i.imgur.com/CWtUCzj.png")
        embed.set_footer(text=STORE_NAME)
        await ctx.send(embed=embed)

    @commands.command(name="cmd")
    async def cmd(self, ctx):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        await ctx.message.delete()
        embed = discord.Embed(
            title=f"PREFIX GUIDE — {STORE_NAME}",
            color=0x2ECC71
        )
        embed.add_field(
            name="MIDMAN TRADE",
            value=(
                "`!open` — kirim embed catalog\n"
                "`!acc` — konfirmasi trade selesai\n"
                "`!batal` — batalkan tiket\n"
                "`!fee <nominal>` — hitung fee midman"
            ),
            inline=False
        )
        embed.add_field(
            name="BOOST VIA LOGIN",
            value=(
                "`!vilog` — kirim embed pricelist boost\n"
                "`!selesai <nominal>` — tutup tiket vilog\n"
                "`!batalin` — batalkan tiket vilog"
            ),
            inline=False
        )
        embed.add_field(
            name="ROBUX STORE",
            value=(
                "`!catalog` — kirim embed catalog robux\n"
                "`!rate <angka>` — set rate Robux\n"
                "`!gift` — konfirmasi gift item selesai\n"
                "`!tolak [alasan]` — batalkan tiket robux"
            ),
            inline=False
        )
        embed.add_field(
            name="TOPUP MOBILE LEGENDS",
            value=(
                "`!mlcatalog` — kirim embed catalog ML\n"
                "`!mlselesai` — konfirmasi topup selesai\n"
                "`!mlbatal [alasan]` — batalkan tiket ML"
            ),
            inline=False
        )
        embed.add_field(
            name="LAINNYA",
            value=(
                "`!selfroles` — kirim embed self roles\n"
                "`!update` — update bot dari GitHub\n"
                "`!info` — info bot\n"
                "`!ping` — cek latency"
            ),
            inline=False
        )
        embed.set_footer(text=f"{STORE_NAME} • Pesan ini akan hilang dalam 10 detik")
        await ctx.send(embed=embed, delete_after=10)

async def setup(bot):
    await bot.add_cog(Midman(bot))
