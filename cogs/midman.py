import discord
from discord.ext import commands
import asyncio
import datetime
import os
from dotenv import load_dotenv
from utils.fee import hitung_fee, format_nominal
from utils.tickets import save_tickets, load_tickets
from utils.transcript import generate as generate_transcript

load_dotenv()

GUILD_ID = int(os.getenv("GUILD_ID"))
MIDMAN_CHANNEL_ID = int(os.getenv("MIDMAN_CHANNEL_ID"))
TICKET_CATEGORY_ID = int(os.getenv("TICKET_CATEGORY_ID"))
ADMIN_ROLE_ID = int(os.getenv("ADMIN_ROLE_ID"))
TRANSCRIPT_CHANNEL_ID = int(os.getenv("TRANSCRIPT_CHANNEL_ID"))


class MidmanMainView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Buka Tiket Midman Trade", style=discord.ButtonStyle.primary, custom_id="open_midman_trade")
    async def open_ticket(self, interaction, button):
        await interaction.response.send_modal(MidmanTradeModal())


class MidmanTradeModal(discord.ui.Modal, title="Buka Tiket Midman Trade"):
    item_p1 = discord.ui.TextInput(label="Item kamu (Pihak 1)", placeholder="contoh: ruby gemstone")
    item_p2 = discord.ui.TextInput(label="Item yang kamu minta (Pihak 2)", placeholder="contoh: maja")
    fee = discord.ui.TextInput(label="Fee", placeholder="contoh: 5000 / split / ditanggung pihak 1")
    link_server = discord.ui.TextInput(label="Link Private Server", required=False)

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
            "fee": self.fee.value,
            "link_server": self.link_server.value or "-",
            "admin": None,
            "nominal": None,
            "embed_message_id": None,
            "opened_at": datetime.datetime.now(datetime.timezone.utc),
        }

        await interaction.response.send_message(f"Tiket dibuat: {channel.mention}", ephemeral=True)

        embed = discord.Embed(
            title="OPEN TIKET MIDMAN TRADE",
            color=0x5865F2,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.add_field(
            name="ISI FORMAT TRADE",
            value=(
                f"Pihak 1 : {interaction.user.mention}  (item : {self.item_p1.value})\n"
                f"Pihak 2 : -  (item : {self.item_p2.value})\n"
                f"Fee : {self.fee.value}\n"
                f"Admin MM : -\n"
                f"Link Server : {self.link_server.value or chr(45)}"
            ),
            inline=False
        )
        embed.add_field(
            name="HARAP DI ISI AGAR LANCARNYA TRANSAKSI INI",
            value=(
                "1. Pihak pertama memberikan item ke admin\n"
                "2. Pihak kedua memberikan item ke pihak pertama\n"
                "3. Pihak pertama konfirmasi item diterima\n"
                "4. Admin memberikan item pihak pertama ke pihak kedua\n"
                "5. Admin klik tombol Trade Selesai"
            ),
            inline=False
        )
        embed.set_footer(text="Cellyn Store Midman System")

        msg = await channel.send(
            content=f"{admin_role.mention} — Tiket midman trade baru dari {interaction.user.mention}.",
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
    nominal = discord.ui.TextInput(label="Nominal (Rp)", placeholder="contoh: 50000")

    async def on_submit(self, interaction):
        cog = interaction.client.cogs.get("Midman")
        ticket = cog.active_tickets.get(interaction.channel.id)
        guild = interaction.guild

        try:
            user2 = await guild.fetch_member(int(self.pihak2_id.value.strip()))
        except Exception:
            await interaction.response.send_message("User tidak ditemukan. Pastikan ID benar. Tekan Setup Trade lagi.", ephemeral=True)
            return

        nominal_raw = self.nominal.value.replace(".", "").replace(",", "").replace("k", "000").replace("K", "000")
        try:
            nominal_int = int(nominal_raw)
        except ValueError:
            await interaction.response.send_message("Format nominal salah. Tekan Setup Trade lagi.", ephemeral=True)
            return

        fee_result = hitung_fee(nominal_int)
        fee_str = format_nominal(fee_result) if fee_result else "-"

        ticket["pihak2"] = user2
        ticket["nominal"] = nominal_int
        save_tickets(cog.active_tickets)

        await interaction.channel.set_permissions(user2, view_channel=True, send_messages=True)

        try:
            orig_msg = await interaction.channel.fetch_message(ticket["embed_message_id"])
            await orig_msg.delete()
        except Exception as e:
            print(f"Gagal hapus embed: {e}")

        embed = discord.Embed(
            title="OPEN TIKET MIDMAN TRADE",
            color=0x5865F2,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.add_field(
            name="ISI FORMAT TRADE",
            value=(
                f"Pihak 1 : {ticket['pihak1'].mention}  (item : {ticket['item_p1']})\n"
                f"Pihak 2 : {user2.mention}  (item : {ticket['item_p2']})\n"
                f"Fee : {fee_str}\n"
                f"Admin MM : {ticket['admin'].mention}\n"
                f"Link Server : {ticket['link_server']}"
            ),
            inline=False
        )
        embed.add_field(
            name="HARAP DI ISI AGAR LANCARNYA TRANSAKSI INI",
            value=(
                "1. Pihak pertama memberikan item ke admin\n"
                "2. Pihak kedua memberikan item ke pihak pertama\n"
                "3. Pihak pertama konfirmasi item diterima\n"
                "4. Admin memberikan item pihak pertama ke pihak kedua\n"
                "5. Admin klik tombol Trade Selesai"
            ),
            inline=False
        )
        embed.set_footer(text="Cellyn Store Midman System")

        await interaction.response.send_message(
            content=f"{user2.mention} — kamu ditambahkan ke tiket ini sebagai Pihak 2.",
            embed=embed,
            view=TradeFinishView()
        )


class TradeFinishView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Trade Selesai", style=discord.ButtonStyle.success, custom_id="trade_selesai")
    async def trade_selesai(self, interaction, button):
        if interaction.guild.get_role(ADMIN_ROLE_ID) not in interaction.user.roles:
            await interaction.response.send_message("Hanya admin yang bisa menutup tiket.", ephemeral=True)
            return

        cog = interaction.client.cogs.get("Midman")
        ticket = cog.active_tickets.get(interaction.channel.id)
        if not ticket:
            await interaction.response.send_message("Data tiket tidak ditemukan.", ephemeral=True)
            return

        ticket["closed_at"] = datetime.datetime.now(datetime.timezone.utc)

        nominal_int = ticket.get("nominal", 0)
        nominal_str = format_nominal(nominal_int) if nominal_int else "-"

        transcript_file = await generate_transcript(interaction.channel)

        p1 = ticket["pihak1"]
        p2 = ticket["pihak2"]
        adm = ticket["admin"]

        log_text = (
            f"<a:bell:1456430498757873797> **MIDMAN TRADE SUKSES**\n"
            f"\u200b\n"
            f"| Midman: {adm.mention}\n"
            f"| Pihak 1: {p1.mention} | {p1.id} ({ticket['item_p1']})\n"
            f"| Pihak 2: {p2.mention if p2 else chr(45)} | {p2.id if p2 else chr(45)} ({ticket['item_p2']})\n"
            f"| Nominal: {nominal_str}\n"
            f"\u200b\n"
            f"<a:verify:1453822153257652315> Transaksi telah selesai dan aman! Terima kasih telah menggunakan jasa midman kami."
        )

        button.disabled = True
        await interaction.message.edit(view=self)
        await interaction.response.send_message(log_text)

        transcript_ch = interaction.guild.get_channel(TRANSCRIPT_CHANNEL_ID)
        if transcript_ch:
            await transcript_ch.send(content=log_text, file=transcript_file)

        await interaction.channel.send("Menutup tiket dalam 5 detik...")
        await asyncio.sleep(5)
        del cog.active_tickets[interaction.channel.id]
        save_tickets(cog.active_tickets)
        await interaction.channel.delete()


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
            title="Layanan Midman Trade — Cellyn Store",
            description=(
                "Tukar item dengan aman menggunakan middleman terpercaya.\n\n"
                "Klik tombol di bawah untuk membuka tiket."
            ),
            color=0x5865F2
        )
        embed.set_footer(text="Cellyn Store")
        await ch.send(embed=embed, view=MidmanMainView())
        await ctx.send(f"Embed dikirim ke {ch.mention}", delete_after=5)

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
        embed.set_footer(text="Cellyn Store Midman")
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Midman(bot))
