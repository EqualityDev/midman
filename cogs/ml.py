import discord
import datetime
import asyncio
from discord.ext import commands
from utils.config import ADMIN_ROLE_ID, LOG_CHANNEL_ID, STORE_NAME, TICKET_CATEGORY_ID, TRANSCRIPT_CHANNEL_ID
from utils.counter import next_ticket_number
from utils.transcript import generate as generate_transcript

ML_PRODUCTS = [
    {"dm": 3,   "harga": 1500},
    {"dm": 5,   "harga": 2000},
    {"dm": 10,  "harga": 3000},
    {"dm": 12,  "harga": 4000},
    {"dm": 14,  "harga": 4500},
    {"dm": 17,  "harga": 5000},
    {"dm": 19,  "harga": 5500},
    {"dm": 28,  "harga": 7500},
    {"dm": 33,  "harga": 9500},
    {"dm": 36,  "harga": 10000},
    {"dm": 44,  "harga": 11000},
    {"dm": 50,  "harga": 15500},
    {"dm": 56,  "harga": 15500},
    {"dm": 59,  "harga": 16000},
    {"dm": 74,  "harga": 18000},
    {"dm": 85,  "harga": 22000},
    {"dm": 100, "harga": 25000},
    {"dm": 110, "harga": 29000},
    {"dm": 112, "harga": 29500},
    {"dm": 140, "harga": 37000},
    {"dm": 144, "harga": 38000},
    {"dm": 170, "harga": 44000},
    {"dm": 172, "harga": 44500},
    {"dm": 185, "harga": 47000},
    {"dm": 222, "harga": 57000},
    {"dm": 229, "harga": 60000},
    {"dm": 240, "harga": 62000},
    {"dm": 257, "harga": 66000},
    {"dm": 270, "harga": 74000},
    {"dm": 284, "harga": 75000},
    {"dm": 296, "harga": 76000},
    {"dm": 301, "harga": 81000},
    {"dm": 346, "harga": 86000},
]

THUMBNAIL = "https://i.imgur.com/CWtUCzj.png"
ML_KECIL = [p for p in ML_PRODUCTS if p["dm"] <= 100]
ML_BESAR = [p for p in ML_PRODUCTS if p["dm"] > 100]


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

    def __init__(self, dm: int, harga: int):
        super().__init__()
        self.dm = dm
        self.harga = harga

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
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

        cog = interaction.client.cogs.get("MLStore")
        ticket = {
            "channel_id": channel.id,
            "user_id": user.id,
            "id_ml": self.id_ml.value.strip(),
            "server_id": self.server_id.value.strip(),
            "dm": self.dm,
            "harga": self.harga,
            "opened_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        cog.active_tickets[channel.id] = ticket

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
            f"**!mlbatal [alasan]** — batalkan tiket"
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
    def __init__(self):
        options = [
            discord.SelectOption(
                label=f"{p['dm']} Diamond",
                description=f"Rp {p['harga']:,}",
                value=str(p['dm'])
            ) for p in ML_KECIL
        ]
        super().__init__(
            placeholder="Pilih jumlah diamond (3–100 DM)...",
            options=options,
            custom_id="ml_select_kecil"
        )

    async def callback(self, interaction: discord.Interaction):
        dm = int(self.values[0])
        harga = next(p["harga"] for p in ML_PRODUCTS if p["dm"] == dm)
        await interaction.response.send_modal(MLFormModal(dm=dm, harga=harga))


class MLSelectBesar(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label=f"{p['dm']} Diamond",
                description=f"Rp {p['harga']:,}",
                value=str(p['dm'])
            ) for p in ML_BESAR
        ]
        super().__init__(
            placeholder="Pilih jumlah diamond (110–346 DM)...",
            options=options,
            custom_id="ml_select_besar"
        )

    async def callback(self, interaction: discord.Interaction):
        dm = int(self.values[0])
        harga = next(p["harga"] for p in ML_PRODUCTS if p["dm"] == dm)
        await interaction.response.send_modal(MLFormModal(dm=dm, harga=harga))


class MLBuyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(MLSelectKecil())
        self.add_item(MLSelectBesar())


class MLStore(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_tickets = {}
        self.catalog_message_id = None

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
            title=f"💎 TOPUP MOBILE LEGENDS",
            description=(
                f"Sekarang tersedia di **{STORE_NAME}**\n"
                f"Topup diamond dengan harga terjangkau, proses cepat amanah dan transparan!\n\n"
                f"**Cara Order:**\n"
                f"1. Klik dropdown **KECIL** atau **BESAR** sesuai jumlah diamond\n"
                f"2. Pilih jumlah diamond dari dropdown\n"
                f"3. Isi form ID ML dan Server ID\n"
                f"4. Tunggu admin memproses topup kamu\n\n"
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

        await ctx.send("Topup berhasil diproses. Tiket ditutup dalam 5 detik.")
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
            log_embed.add_field(name="ID ML", value=f"`{ticket['id_ml']}` (Server: `{ticket['server_id']}`)", inline=False)
            log_embed.add_field(name="Item", value=f"{ticket['dm']} Diamond", inline=False)
            log_embed.add_field(name="Total", value=f"Rp {ticket['harga']:,}", inline=False)
            log_embed.add_field(name="Metode Pembayaran", value="QRIS", inline=False)
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
