import discord
import datetime
import asyncio
from discord.ext import commands
from utils.config import (
    ADMIN_ROLE_ID, STORE_NAME, TICKET_CATEGORY_ID,
    GUILD_ID, LOG_CHANNEL_ID
)
from utils.db import get_conn

THUMBNAIL = "https://i.imgur.com/CWtUCzj.png"
ROBUX_PER_INVITE = 5
INVITE_REWARD_CHANNEL_ID = 1482464579085799435

TUTORIAL_GAMEPASS = """
**Cara Membuat Gamepass di Roblox:**

**PC:**
1. Buka [roblox.com](https://www.roblox.com) → **Create**
2. Pilih game kamu → klik **⋯** → **Create Game Pass**
3. Upload gambar, isi nama, set harga sesuai saldo Robux kamu
4. Klik **Save** → copy link gamepass

**Mobile:**
1. Buka Roblox app → tap profil → **Create**
2. Pilih game → **Game Passes** → **+**
3. Isi detail & harga → **Save**
4. Copy link gamepass

> ⚠️ Pastikan harga gamepass **sama persis** dengan saldo Robux kamu!
> Contoh: saldo 15 Robux → buat gamepass seharga **15 Robux**
"""


# ── DATABASE ──────────────────────────────────────────────────────────────────

def _init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS invite_tracking (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            inviter_id  INTEGER NOT NULL,
            invitee_id  INTEGER NOT NULL,
            invite_code TEXT,
            joined_at   TEXT NOT NULL,
            valid       INTEGER DEFAULT 1
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS invite_balance (
            user_id     INTEGER PRIMARY KEY,
            total_invites INTEGER DEFAULT 0,
            robux_balance INTEGER DEFAULT 0,
            total_claimed INTEGER DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS invite_claims (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id      INTEGER,
            user_id         INTEGER,
            robux_amount    INTEGER,
            gamepass_link   TEXT,
            admin_id        INTEGER,
            status          TEXT DEFAULT 'pending',
            opened_at       TEXT,
            closed_at       TEXT
        )
    """)
    conn.commit()
    conn.close()


def get_balance(user_id: int) -> dict:
    conn = get_conn()
    row = conn.execute(
        "SELECT total_invites, robux_balance, total_claimed FROM invite_balance WHERE user_id=?",
        (user_id,)
    ).fetchone()
    conn.close()
    if row:
        return {"total_invites": row[0], "robux_balance": row[1], "total_claimed": row[2]}
    return {"total_invites": 0, "robux_balance": 0, "total_claimed": 0}


def add_invite(inviter_id: int, invitee_id: int, invite_code: str):
    conn = get_conn()
    c = conn.cursor()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    c.execute(
        "INSERT INTO invite_tracking (inviter_id, invitee_id, invite_code, joined_at) VALUES (?,?,?,?)",
        (inviter_id, invitee_id, invite_code, now)
    )
    c.execute("""
        INSERT INTO invite_balance (user_id, total_invites, robux_balance, total_claimed)
        VALUES (?, 1, ?, 0)
        ON CONFLICT(user_id) DO UPDATE SET
            total_invites = total_invites + 1,
            robux_balance = robux_balance + ?
    """, (inviter_id, ROBUX_PER_INVITE, ROBUX_PER_INVITE))
    conn.commit()
    conn.close()


def remove_invite(invitee_id: int):
    """Kurangi balance inviter kalau invitee keluar server."""
    conn = get_conn()
    c = conn.cursor()
    row = c.execute(
        "SELECT inviter_id FROM invite_tracking WHERE invitee_id=? AND valid=1 ORDER BY id DESC LIMIT 1",
        (invitee_id,)
    ).fetchone()
    if row:
        inviter_id = row[0]
        c.execute(
            "UPDATE invite_tracking SET valid=0 WHERE invitee_id=? AND valid=1",
            (invitee_id,)
        )
        c.execute("""
            UPDATE invite_balance SET
                total_invites = MAX(0, total_invites - 1),
                robux_balance = MAX(0, robux_balance - ?)
            WHERE user_id=?
        """, (ROBUX_PER_INVITE, inviter_id))
        conn.commit()
    conn.close()
    return row[0] if row else None


def deduct_balance(user_id: int, amount: int):
    conn = get_conn()
    conn.execute("""
        UPDATE invite_balance SET
            robux_balance = MAX(0, robux_balance - ?),
            total_claimed = total_claimed + ?
        WHERE user_id=?
    """, (amount, amount, user_id))
    conn.commit()
    conn.close()


def save_claim(ticket: dict):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO invite_claims
        (channel_id, user_id, robux_amount, gamepass_link, admin_id, status, opened_at, closed_at)
        VALUES (?,?,?,?,?,?,?,?)
    """, (
        ticket.get("channel_id"), ticket.get("user_id"),
        ticket.get("robux_amount"), ticket.get("gamepass_link"),
        ticket.get("admin_id"), ticket.get("status", "pending"),
        ticket.get("opened_at"), ticket.get("closed_at")
    ))
    conn.commit()
    conn.close()


def delete_claim(channel_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM invite_claims WHERE channel_id=?", (channel_id,))
    conn.commit()
    conn.close()


def load_claims():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM invite_claims WHERE status='pending'").fetchall()
    conn.close()
    return {row["channel_id"]: dict(row) for row in rows}


# ── VIEWS ─────────────────────────────────────────────────────────────────────

class InviteRewardView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔗 Dapatkan Invite Link", style=discord.ButtonStyle.primary, custom_id="invite_get_link", row=0)
    async def get_invite_link(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        member = interaction.user
        try:
            invites = await guild.invites()
            existing = next((inv for inv in invites if inv.inviter and inv.inviter.id == member.id), None)
            if existing:
                invite_url = existing.url
            else:
                ch = guild.get_channel(INVITE_REWARD_CHANNEL_ID)
                if not ch:
                    await interaction.response.send_message("Channel tidak ditemukan!", ephemeral=True)
                    return
                new_invite = await ch.create_invite(max_age=0, max_uses=0, unique=True, reason=f"Invite Reward - {member}")
                invite_url = new_invite.url
            embed = discord.Embed(title="🔗 Invite Link Kamu", color=0xF1C40F)
            embed.add_field(name="Link", value=f"**{invite_url}**", inline=False)
            embed.add_field(
                name="⚠️ Penting",
                value="Gunakan link **ini** untuk mengajak teman.\n"
                "Jangan gunakan link server umum karena tidak akan tercatat!",
                inline=False
            )
            embed.set_footer(text=STORE_NAME)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Gagal membuat invite link: {e}", ephemeral=True)

    @discord.ui.button(label="🏆 Check Balance", style=discord.ButtonStyle.secondary, custom_id="invite_check_balance", row=1)
    async def check_balance(self, interaction: discord.Interaction, button: discord.ui.Button):
        bal = get_balance(interaction.user.id)
        embed = discord.Embed(
            title="🏆 Invite Balance",
            color=0xF1C40F,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.add_field(name="Total Invite Valid", value=f"**{bal['total_invites']}** orang", inline=True)
        embed.add_field(name="Saldo Robux", value=f"**{bal['robux_balance']}** Robux", inline=True)
        embed.add_field(name="Total Dicairkan", value=f"**{bal['total_claimed']}** Robux", inline=True)
        embed.add_field(
            name="ℹ️ Info",
            value=f"Setiap 1 invite valid = **{ROBUX_PER_INVITE} Robux**\nInvite dihitung tidak valid jika member keluar server.",
            inline=False
        )
        embed.set_thumbnail(url=THUMBNAIL)
        embed.set_footer(text=STORE_NAME)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="🔄 Convert Invite", style=discord.ButtonStyle.primary, custom_id="invite_convert", row=1)
    async def convert(self, interaction: discord.Interaction, button: discord.ui.Button):
        bal = get_balance(interaction.user.id)
        embed = discord.Embed(
            title="🔄 Convert Invite",
            color=0x3498DB,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.add_field(name="Invite Valid", value=f"**{bal['total_invites']}** orang", inline=True)
        embed.add_field(name="Saldo Robux", value=f"**{bal['robux_balance']}** Robux", inline=True)
        embed.add_field(
            name="ℹ️ Info",
            value=(
                f"Invite kamu sudah otomatis dikonversi ke Robux.\n"
                f"**1 invite = {ROBUX_PER_INVITE} Robux**\n\n"
                f"Untuk mencairkan, klik tombol **Pencairan Balance**."
            ),
            inline=False
        )
        embed.set_thumbnail(url=THUMBNAIL)
        embed.set_footer(text=STORE_NAME)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="💰 Pencairan Balance", style=discord.ButtonStyle.success, custom_id="invite_pencairan", row=1)
    async def pencairan(self, interaction: discord.Interaction, button: discord.ui.Button):
        bal = get_balance(interaction.user.id)
        if bal["robux_balance"] < ROBUX_PER_INVITE:
            await interaction.response.send_message(
                f"Saldo Robux kamu tidak cukup! Minimal **{ROBUX_PER_INVITE} Robux** untuk mencairkan.",
                ephemeral=True
            )
            return
        await interaction.response.send_modal(PencairanModal(bal["robux_balance"]))


class PencairanModal(discord.ui.Modal, title="Pencairan Invite Reward"):
    gamepass_link = discord.ui.TextInput(
        label="Link Gamepass Roblox",
        placeholder="https://www.roblox.com/game-pass/...",
        required=True,
        max_length=200
    )

    def __init__(self, robux_balance: int):
        super().__init__()
        self.robux_balance = robux_balance
        self.gamepass_link.placeholder = f"Buat gamepass seharga {robux_balance} Robux, lalu paste link-nya"

    async def on_submit(self, interaction: discord.Interaction):
        link = self.gamepass_link.value.strip()
        if "roblox.com" not in link:
            await interaction.response.send_message(
                "Link gamepass tidak valid! Harus berupa link Roblox gamepass.",
                ephemeral=True
            )
            return

        guild = interaction.guild
        member = interaction.user
        cog = interaction.client.cogs.get("InviteReward")

        # Cek tiket aktif
        for ch_id, t in cog.active_claims.items():
            if t["user_id"] == member.id:
                existing = guild.get_channel(ch_id)
                if existing:
                    await interaction.response.send_message(
                        f"Kamu masih punya request pencairan aktif di {existing.mention}!",
                        ephemeral=True
                    )
                    return

        await interaction.response.defer(ephemeral=True)

        admin_role = guild.get_role(ADMIN_ROLE_ID)
        cat_channel = guild.get_channel(TICKET_CATEGORY_ID)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        if admin_role:
            overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel = await guild.create_text_channel(
            name=f"cairkan-{member.name}", category=cat_channel, overwrites=overwrites
        )

        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        ticket = {
            "channel_id": channel.id,
            "user_id": member.id,
            "robux_amount": self.robux_balance,
            "gamepass_link": link,
            "admin_id": None,
            "status": "pending",
            "opened_at": now,
            "closed_at": None,
        }
        cog.active_claims[channel.id] = ticket
        save_claim(ticket)

        embed = discord.Embed(
            title=f"💰 PENCAIRAN INVITE REWARD — {STORE_NAME}",
            color=0xF1C40F,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.add_field(name="Member", value=member.mention, inline=True)
        embed.add_field(name="Jumlah Robux", value=f"**{self.robux_balance} Robux**", inline=True)
        embed.add_field(name="Link Gamepass", value=link, inline=False)
        embed.add_field(
            name="Instruksi Admin",
            value=(
                f"1. Buka link gamepass di atas\n"
                f"2. Pastikan harganya **{self.robux_balance} Robux**\n"
                f"3. Beli gamepass tersebut\n"
                f"4. Ketik `!claimeselesai` setelah selesai\n"
                f"5. Ketik `!claimbatal [alasan]` jika ada masalah"
            ),
            inline=False
        )
        embed.set_thumbnail(url=THUMBNAIL)
        embed.set_footer(text=STORE_NAME)

        admin_mention = admin_role.mention if admin_role else ""
        await channel.send(content=f"{member.mention} {admin_mention}", embed=embed)
        await interaction.followup.send(f"Request pencairan dibuat di {channel.mention}!", ephemeral=True)


# ── COG ───────────────────────────────────────────────────────────────────────

class InviteReward(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        _init_db()
        self.invite_cache = {}
        self.active_claims = load_claims()
        self.catalog_message_id = None

    async def cog_load(self):
        self.bot.loop.create_task(self._wait_and_cache())

    async def _wait_and_cache(self):
        await self.bot.wait_until_ready()
        await self._cache_invites()

    async def _cache_invites(self):
        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            return
        try:
            invites = await guild.invites()
            self.invite_cache = {inv.code: inv.uses for inv in invites}
        except Exception as e:
            print(f"[InviteReward] Gagal cache invites: {e}")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        print(f"[DEBUG] on_member_join: {member} guild={member.guild.id} expected={GUILD_ID}")
        if member.guild.id != GUILD_ID:
            print("[DEBUG] guild mismatch, skip")
            return
        try:
            invites_after = await member.guild.invites()
            for invite in invites_after:
                uses_before = self.invite_cache.get(invite.code, 0)
                if invite.uses > uses_before:
                    inviter = invite.inviter
                    if inviter and inviter.id != member.id:
                        add_invite(inviter.id, member.id, invite.code)
                        print(f"[InviteReward] {member} diinvite oleh {inviter} (+{ROBUX_PER_INVITE} Robux)")
                    break
            self.invite_cache = {inv.code: inv.uses for inv in invites_after}
        except Exception as e:
            print(f"[InviteReward] Error on_member_join: {e}")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if member.guild.id != GUILD_ID:
            return
        try:
            inviter_id = remove_invite(member.id)
            if inviter_id:
                print(f"[InviteReward] {member} keluar, invite {inviter_id} dikurangi")
            await self._cache_invites()
        except Exception as e:
            print(f"[InviteReward] Error on_member_remove: {e}")

    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        self.invite_cache[invite.code] = invite.uses

    @commands.Cog.listener()
    async def on_invite_delete(self, invite):
        self.invite_cache.pop(invite.code, None)

    @discord.app_commands.command(name="invites", description="Cek jumlah invite dan saldo Robux kamu")
    async def invites_cmd(self, interaction: discord.Interaction):
        bal = get_balance(interaction.user.id)
        embed = discord.Embed(
            title="🏆 Invite Stats",
            color=0xF1C40F,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.add_field(name="Total Invite Valid", value=f"**{bal['total_invites']}** orang", inline=True)
        embed.add_field(name="Saldo Robux", value=f"**{bal['robux_balance']}** Robux", inline=True)
        embed.add_field(name="Total Dicairkan", value=f"**{bal['total_claimed']}** Robux", inline=True)
        embed.set_thumbnail(url=THUMBNAIL)
        embed.set_footer(text=STORE_NAME)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @commands.command(name="invitereward")
    async def send_embed(self, ctx):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        await ctx.message.delete()
        ch = ctx.guild.get_channel(INVITE_REWARD_CHANNEL_ID)
        if not ch:
            await ctx.send("Channel invite reward tidak ditemukan!", delete_after=5)
            return

        embed = discord.Embed(
            title="🎉 Invite Reward — Cellyn Store",
            description=(
                f"Ajak teman ke server dan dapatkan **Robux gratis!**\n\n"
                f"💎 **{ROBUX_PER_INVITE} Robux** per 1 invite yang valid\n"
                f"✅ Invite dihitung valid jika member tetap di server\n"
                f"❌ Invite hangus jika member keluar server\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=0xF1C40F
        )
        embed.add_field(
            name="📋 Tutorial Membuat Gamepass",
            value=TUTORIAL_GAMEPASS,
            inline=False
        )
        embed.add_field(
            name="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            value=(
                "Klik tombol di bawah untuk:\n"
                "🏆 **Check Balance** — lihat saldo Robux kamu\n"
                "🔄 **Convert** — info konversi invite ke Robux\n"
                "💰 **Pencairan** — cairkan Robux ke akun kamu"
            ),
            inline=False
        )
        embed.set_thumbnail(url=THUMBNAIL)
        embed.set_footer(text=f"{STORE_NAME} • Invite sekarang dan kumpulkan Robux!")

        if self.catalog_message_id:
            try:
                msg = await ch.fetch_message(self.catalog_message_id)
                await msg.edit(embed=embed, view=InviteRewardView())
                await ctx.send(f"Embed invite reward diperbarui di {ch.mention}", delete_after=5)
                return
            except Exception:
                pass

        async for msg in ch.history(limit=10):
            if msg.author == ctx.guild.me:
                try:
                    await msg.delete()
                except Exception:
                    pass

        sent = await ch.send(embed=embed, view=InviteRewardView())
        self.catalog_message_id = sent.id
        await ctx.send(f"Embed invite reward dikirim ke {ch.mention}", delete_after=5)

    @commands.command(name="claimeselesai")
    async def claim_selesai(self, ctx):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        await ctx.message.delete()
        channel_id = ctx.channel.id
        if channel_id not in self.active_claims:
            await ctx.send("Channel ini bukan tiket pencairan aktif.", delete_after=5)
            return
        ticket = self.active_claims[channel_id]
        member = ctx.guild.get_member(ticket["user_id"])

        deduct_balance(ticket["user_id"], ticket["robux_amount"])

        now = datetime.datetime.now(datetime.timezone.utc)
        ticket["status"] = "selesai"
        ticket["admin_id"] = ctx.author.id
        ticket["closed_at"] = now.isoformat()
        save_claim(ticket)

        log_ch = ctx.guild.get_channel(LOG_CHANNEL_ID)
        if log_ch:
            log_embed = discord.Embed(
                title="💰 PENCAIRAN INVITE REWARD SUKSES",
                color=0xF1C40F,
                timestamp=now
            )
            log_embed.add_field(name="Admin", value=f"{ctx.author.mention}\n`{ctx.author.id}`", inline=False)
            log_embed.add_field(name="Member", value=f"{member.mention if member else ticket['user_id']}", inline=False)
            log_embed.add_field(name="Jumlah", value=f"**{ticket['robux_amount']} Robux**", inline=False)
            log_embed.add_field(name="Gamepass", value=ticket["gamepass_link"], inline=False)
            log_embed.set_thumbnail(url=THUMBNAIL)
            log_embed.set_footer(text=STORE_NAME)
            await log_ch.send(embed=log_embed)

        await ctx.send(
            f"{member.mention if member else ''} Pencairan **{ticket['robux_amount']} Robux** berhasil diproses! "
            f"Terima kasih telah mengundang teman ke {STORE_NAME}! Tiket ditutup dalam 5 detik."
        )
        await asyncio.sleep(5)
        delete_claim(channel_id)
        del self.active_claims[channel_id]
        await ctx.channel.delete()

    @commands.command(name="claimbatal")
    async def claim_batal(self, ctx, *, alasan: str = "Tidak ada alasan."):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        await ctx.message.delete()
        channel_id = ctx.channel.id
        if channel_id not in self.active_claims:
            await ctx.send("Channel ini bukan tiket pencairan aktif.", delete_after=5)
            return
        ticket = self.active_claims[channel_id]
        member = ctx.guild.get_member(ticket["user_id"])

        embed = discord.Embed(title="❌ PENCAIRAN DIBATALKAN", color=0xE74C3C)
        embed.add_field(name="Dibatalkan oleh", value=ctx.author.mention, inline=True)
        embed.add_field(name="Alasan", value=alasan, inline=False)
        embed.add_field(name="", value="Tiket ditutup dalam 5 detik.", inline=False)
        embed.set_footer(text=STORE_NAME)

        mentions = member.mention if member else ""
        await ctx.send(content=mentions if mentions else None, embed=embed)
        await asyncio.sleep(5)

        ticket["status"] = "batal"
        ticket["closed_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save_claim(ticket)
        delete_claim(channel_id)
        del self.active_claims[channel_id]
        await ctx.channel.delete()


async def setup(bot):
    await bot.add_cog(InviteReward(bot))
    bot.add_view(InviteRewardView())
    print("Cog InviteReward siap.")
