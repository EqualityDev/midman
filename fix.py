code = """import discord
from discord.ext import commands
import asyncio
import datetime
import os
from dotenv import load_dotenv
from utils.fee import hitung_fee, format_nominal
from utils.tickets import save_tickets, load_tickets, next_ticket_number
from utils.transcript import generate as generate_transcript

load_dotenv()

GUILD_ID = int(os.getenv("GUILD_ID"))
MIDMAN_CHANNEL_ID = int(os.getenv("MIDMAN_CHANNEL_ID"))
TICKET_CATEGORY_ID = int(os.getenv("TICKET_CATEGORY_ID"))
ADMIN_ROLE_ID = int(os.getenv("ADMIN_ROLE_ID"))
TRANSCRIPT_CHANNEL_ID = int(os.getenv("TRANSCRIPT_CHANNEL_ID"))
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID"))
STORE_NAME = os.getenv("STORE_NAME", "Cellyn Store")


class MidmanMainView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Buka Tiket Midman Trade", style=discord.ButtonStyle.primary, custom_id="open_midman_trade")
    async def open_ticket(self, interaction, button):
        await interaction.response.send_modal(MidmanTradeModal())


class MidmanTradeModal(discord.ui.Modal, title="Buka Tiket Midman Trade"):
    item_p1 = discord.ui.TextInput(label="Item kamu (Pihak 1)", placeholder="contoh: ruby gemstone")
    item_p2 = discord.ui.TextInput(label="Item yang kamu minta (Pihak 2)", placeholder="contoh: maja")

    async def on_submit(self, interaction):
        cog = interaction.client.cogs.get("Midman")
        guild = interaction.guild
        category = guild.get_channel(TICKET_CATEGORY_ID)
        admin_role = guild.get_role(ADMIN_ROLE_ID)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            admin_role: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }
        channel = await guild.create_text_channel(
            f"trade-{interaction.user.name[:15]}",
            category=category,
            overwrites=overwrites
        )

        cog.active_tickets[channel.id] = {
            "pihak1": interaction.user,
            "pihak2": None,
            "item_p1": self.item_p1.value,
            "item_p2": self.item_p2.value,
            "fee": None,
            "link_server": None,
            "admin": None,
            "embed_message_id": None,
            "ticket_number": next_ticket_number(),
            "opened_at": datetime.datetime.now(datetime.timezone.utc),
        }

        await interaction.response.send_message(f"Tiket dibuat: {channel.mention}", ephemeral=True)

        embed = discord.Embed(
            title=f"MIDMAN TRADE \u2014 {STORE_NAME}",
            color=0x5865F2,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.add_field(
            name="\u200b",
            value=(
                f"Pihak 1 : {interaction.user.mention}  (item : {self.item_p1.value})\\n"
                f"Pihak 2 : -      (item : {self.item_p2.value})\\n"
                f"Admin   : -\\n\\n"
                f"Status  : Menunggu konfirmasi admin"
            ),
            inline=False
        )
        embed.set_footer(text=STORE_NAME)

        msg = await channel.send(
            content=f"{admin_role.mention} \u2014 Tiket midman trade baru dari {interaction.user.mention}.",
            embed=embed,
            view=AdminSetupView()
        )
        cog.active_tickets[channel.id]["embed_message_id"] = msg.id
        save_tickets(cog.active_tickets)


class AdminSetupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Setup Trade (Admin)", style=discord.ButtonStyle.primary, custom_id="admin_setup_trade")
    async def setup_trade(self, interaction, button):
        if interaction.guild.get_role(ADMIN_ROLE_ID) not in interaction.user.roles:
            await interaction.response.send_message("Hanya admin.", ephemeral=True)
            return

        cog = interaction.client.cogs.get("Midman")
        ticket = cog.active_tickets.get(interaction.channel.id)
        if not ticket:
            await interaction.response.send_message("Data tiket tidak ditemukan.", ephemeral=True)
            return

        ticket["admin"] = interaction.user
        await interaction.response.send_modal(AdminSetupModal())


class AdminSetupModal(discord.ui.Modal, title="Setup Data Trade"):
    pihak2_id = discord.ui.TextInput(label="ID Pihak 2", placeholder="Paste user ID pihak 2")
    fee_input = discord.ui.TextInput(label="Fee (Rp)", placeholder="contoh: 2500")
    link_server = discord.ui.TextInput(label="Link Private Server", placeholder="https://roblox.com/...")

    async def on_submit(self, interaction):
        cog = interaction.client.cogs.get("Midman")
        ticket = cog.active_tickets.get(interaction.channel.id)
        guild = interaction.guild

        try:
            user2 = await guild.fetch_member(int(self.pihak2_id.value.strip()))
        except Exception:
            await interaction.response.send_message("User tidak ditemukan. Pastikan ID benar. Tekan Setup Trade lagi.", ephemeral=True)
            return

        fee_raw = self.fee_input.value.replace(".", "").replace(",", "").replace("k", "000").replace("K", "000")
        try:
            fee_int = int(fee_raw)
        except ValueError:
            await interaction.response.send_message("Format fee salah. Tekan Setup Trade lagi.", ephemeral=True)
            return

        fee_str = format_nominal(fee_int)

        ticket["pihak2"] = user2
        ticket["fee_final"] = fee_int
        ticket["link_server"] = self.link_server.value or "-"
        save_tickets(cog.active_tickets)

        await interaction.channel.set_permissions(user2, view_channel=True, send_messages=True)

        try:
            orig_msg = await interaction.channel.fetch_message(ticket["embed_message_id"])
            await orig_msg.delete()
        except Exception as e:
            print(f"Gagal hapus embed: {e}")

        embed = discord.Embed(
            title=f"MIDMAN TRADE \u2014 {STORE_NAME}",
            color=0xFFA500,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.add_field(
            name="\u200b",
            value=(
                f"Pihak 1 : {ticket['pihak1'].mention}  (item : {ticket['item_p1']})\\n"
                f"Pihak 2 : {user2.mention}  (item : {ticket['item_p2']})\\n"
                f"Admin   : {ticket['admin'].mention}\\n"
                f"Fee     : {fee_str}\\n"
                f"Link    : {ticket['link_server']}\\n\\n"
                f"Status  : Menunggu pembayaran fee\\n"
                f"\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\\n"
                f"Silakan bayar fee ke admin sebelum memulai trade\\n"
                f"Setelah fee diterima, admin akan mengkonfirmasi dan trade dimulai"
            ),
            inline=False
        )
        embed.set_footer(text=STORE_NAME)

        await interaction.response.send_message(
            content=f"{user2.mention} \u2014 kamu ditambahkan ke tiket ini sebagai Pihak 2.",
            embed=embed,
            view=TradeFinishView()
        )


class TradeFinishView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Fee Diterima (Admin)", style=discord.ButtonStyle.primary, custom_id="fee_diterima_v2")
    async def fee_diterima(self, interaction, button):
        if interaction.guild.get_role(ADMIN_ROLE_ID) not in interaction.user.roles:
            await interaction.response.send_message("Hanya admin.", ephemeral=True)
            return

        cog = interaction.client.cogs.get("Midman")
        ticket = cog.active_tickets.get(interaction.channel.id)
        if not ticket:
            await interaction.response.send_message("Data tiket tidak ditemukan.", ephemeral=True)
            return

        ticket["fee_paid"] = True
        save_tickets(cog.active_tickets)

        button.disabled = True

        p1 = ticket["pihak1"]
        p2 = ticket["pihak2"]
        fee_str = format_nominal(ticket["fee_final"]) if ticket.get("fee_final") else "-"

        embed = discord.Embed(
            title=f"MIDMAN TRADE \u2014 {STORE_NAME}",
            color=0x57F287,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.add_field(
            name="\u200b",
            value=(
                f"Pihak 1 : {p1.mention}  (item : {ticket['item_p1']})\\n"
                f"Pihak 2 : {p2.mention if p2 else '-'}  (item : {ticket['item_p2']})\\n"
                f"Admin   : {ticket['admin'].mention}\\n"
                f"Fee     : {fee_str}\\n"
                f"Link    : {ticket['link_server']}\\n\\n"
                f"Status  : Transaksi berlangsung\\n"
                f"Notif   : Pembayaran dikonfirmasi oleh {interaction.user.mention}\\n"
                f"\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\\n"
                f"Pihak 1 \u2014 berikan item kamu ke admin di private server\\n"
                f"Pihak 2 \u2014 berikan item kamu ke pihak 1\\n"
                f"Setelah semua selesai, admin ketik !acc untuk menutup tiket"
            ),
            inline=False
        )
        embed.set_footer(text=STORE_NAME)
        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message(
            content=f"Pembayaran dikonfirmasi oleh {interaction.user.mention}."
        )


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
        ch = ctx.guild.get_channel(MIDMAN_CHANNEL_ID)
        embed = discord.Embed(
            title=f"MIDMAN TRADE \u2014 {STORE_NAME}",
            description=(
                "Gunakan layanan middleman kami untuk memastikan\\n"
                "transaksi item game kamu berjalan aman dan terpercaya.\\n\\n"
                "**Cara pakai:**\\n"
                "1. Klik tombol di bawah untuk membuka tiket\\n"
                "2. Isi form \u2014 item kamu dan item yang kamu minta\\n"
                "3. Tunggu admin bergabung dan menambahkan pihak 2\\n"
                "4. Fee dibayar oleh pihak yang disepakati \u2014 admin akan konfirmasi di dalam tiket\\n"
                "5. Ikuti instruksi admin di dalam tiket\\n\\n"
                "Klik tombol di bawah untuk memulai."
            ),
            color=0x5865F2
        )
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

        fee_int = ticket.get("fee_final", 0)
        fee_str_log = format_nominal(fee_int) if fee_int else "-"

        p1 = ticket["pihak1"]
        p2 = ticket["pihak2"]
        adm = ticket["admin"]

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
            f"<a:bell:1456430498757873797> **MIDMAN TRADE SUKSES \u2014 #{ticket_num}**\\n"
            f"\\u200b\\n"
            f"| Midman  : {adm.mention}\\n"
            f"| Pihak 1 : {p1.mention} | {p1.id} ({ticket['item_p1']})\\n"
            f"| Pihak 2 : {p2.mention if p2 else '-'} | {p2.id if p2 else '-'} ({ticket['item_p2']})\\n"
            f"| Fee     : {fee_str_log}\\n"
            f"\\u200b\\n"
            f"| Dibuka  : {dibuka_str}\\n"
            f"| Ditutup : {ditutup_str}\\n"
            f"| Durasi  : {durasi}\\n"
            f"\\u200b\\n"
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
                content=f"Transcript #{ticket_num} \u2014 {ctx.channel.name}",
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
            return

        try:
            await ctx.message.delete()
        except:
            pass

        await ctx.send("Transaksi dibatalkan oleh admin \u2014 tiket akan ditutup dalam 5 detik.")
        await asyncio.sleep(5)

        if ctx.channel.id in self.active_tickets:
            del self.active_tickets[ctx.channel.id]
            save_tickets(self.active_tickets)
        await ctx.channel.delete()

    @commands.command(name="fee")
    async def fee(self, ctx, nominal: str):
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
"""

with open("/data/data/com.termux/files/home/midman_bot/cogs/midman.py", "w") as f:
    f.write(code)

print("Berhasil.")
