import discord
import datetime
import asyncio
from discord.ext import commands
from discord.ext import tasks
from utils.config import (
    ADMIN_ROLE_ID, STORE_NAME, TICKET_CATEGORY_ID,
    GUILD_ID, LOG_CHANNEL_ID
)
from utils.db import get_conn

THUMBNAIL = "https://i.imgur.com/CWtUCzj.png"
ROBUX_PER_INVITE = 5
INVITE_REWARD_CHANNEL_ID = 1482464579085799435
INVITES_CHANNEL_ID = 1482498306692223138
MAX_CLAIM_PER_DAY = 500
MIN_STAY_DAYS = 3
MIN_ACCOUNT_AGE_DAYS = 30
LEADERBOARD_CHANNEL_ID = 1482754603920396473
LEADERBOARD_TOP = 15

TUTORIAL_GAMEPASS = """
📹 **Tutorial Video:** https://vt.tiktok.com/ZSua68EBn/

**PC:**
1. Buka [roblox.com](https://www.roblox.com) → **Create**
2. Pilih game kamu → klik **⋯** → **Create Game Pass**
3. Upload gambar, isi nama gamepass
4. Set harga sesuai tabel → **Save** → copy link gamepass

**Mobile:**
1. Buka Roblox app → tap profil → **Create**
2. Pilih game → **Game Passes** → **+**
3. Isi detail, set harga sesuai tabel → **Save** → copy link
"""

SKK = f"""
**1.** Setiap 1 invite valid = **{ROBUX_PER_INVITE} Robux**
**2.** Invite valid setelah member stay **{MIN_STAY_DAYS} hari** di server
**3.** Invite hangus jika member keluar sebelum {MIN_STAY_DAYS} hari
**4.** Akun Discord yang diundang harus berumur minimal **{MIN_ACCOUNT_AGE_DAYS} hari**
**5.** Dilarang mengundang akun sendiri / akun palsu / bot
**6.** Maksimal klaim **{MAX_CLAIM_PER_DAY} Robux** per hari
**7.** Kecurangan & manipulasi = **diskualifikasi permanen**
**8.** Keputusan admin bersifat **final**
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
            valid       INTEGER DEFAULT 0,
            pending     INTEGER DEFAULT 1
        )
    """)
    for col, defval in [("valid", "INTEGER DEFAULT 0"), ("pending", "INTEGER DEFAULT 1")]:
        try:
            c.execute(f"ALTER TABLE invite_tracking ADD COLUMN {col} {defval}")
        except Exception as e:
            if "duplicate column" not in str(e).lower():
                print(f"[InviteReward] Migration {col}: {e}")
    c.execute("""
        CREATE TABLE IF NOT EXISTS invite_balance (
            user_id         INTEGER PRIMARY KEY,
            total_invites   INTEGER DEFAULT 0,
            robux_balance   INTEGER DEFAULT 0,
            total_claimed   INTEGER DEFAULT 0,
            pending_invites INTEGER DEFAULT 0
        )
    """)
    for col, defval in [("pending_invites", "INTEGER DEFAULT 0")]:
        try:
            c.execute(f"ALTER TABLE invite_balance ADD COLUMN {col} {defval}")
        except Exception as e:
            if "duplicate column" not in str(e).lower():
                print(f"[InviteReward] Migration balance {col}: {e}")
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
    c.execute("""
        CREATE TABLE IF NOT EXISTS invite_settings (
            key   TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    conn.commit()
    conn.close()


def get_balance(user_id: int) -> dict:
    conn = get_conn()
    row = conn.execute(
        "SELECT total_invites, robux_balance, total_claimed, pending_invites FROM invite_balance WHERE user_id=?",
        (user_id,)
    ).fetchone()
    conn.close()
    if row:
        return {
            "total_invites": row[0] or 0,
            "robux_balance": row[1] or 0,
            "total_claimed": row[2] or 0,
            "pending_invites": row[3] or 0,
        }
    return {"total_invites": 0, "robux_balance": 0, "total_claimed": 0, "pending_invites": 0}


def add_pending_invite(inviter_id: int, invitee_id: int, invite_code: str):
    conn = get_conn()
    c = conn.cursor()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    c.execute(
        "INSERT INTO invite_tracking (inviter_id, invitee_id, invite_code, joined_at, valid, pending) VALUES (?,?,?,?,0,1)",
        (inviter_id, invitee_id, invite_code, now)
    )
    c.execute("""
        INSERT INTO invite_balance (user_id, total_invites, robux_balance, total_claimed, pending_invites)
        VALUES (?, 0, 0, 0, 1)
        ON CONFLICT(user_id) DO UPDATE SET pending_invites = pending_invites + 1
    """, (inviter_id,))
    conn.commit()
    conn.close()


def validate_invite(invitee_id: int):
    conn = get_conn()
    c = conn.cursor()
    row = c.execute(
        "SELECT id, inviter_id FROM invite_tracking WHERE invitee_id=? AND pending=1 ORDER BY id DESC LIMIT 1",
        (invitee_id,)
    ).fetchone()
    if row:
        c.execute("UPDATE invite_tracking SET valid=1, pending=0 WHERE id=?", (row[0],))
        c.execute("""
            UPDATE invite_balance SET
                total_invites = total_invites + 1,
                robux_balance = robux_balance + ?,
                pending_invites = MAX(0, pending_invites - 1)
            WHERE user_id=?
        """, (ROBUX_PER_INVITE, row[1]))
        conn.commit()
        conn.close()
        return row[1]
    conn.close()
    return None


def cancel_pending_invite(invitee_id: int):
    conn = get_conn()
    c = conn.cursor()
    row = c.execute(
        "SELECT inviter_id FROM invite_tracking WHERE invitee_id=? AND pending=1 ORDER BY id DESC LIMIT 1",
        (invitee_id,)
    ).fetchone()
    if row:
        c.execute(
            "UPDATE invite_tracking SET valid=0, pending=0 WHERE invitee_id=? AND pending=1",
            (invitee_id,)
        )
        c.execute("""
            UPDATE invite_balance SET
                pending_invites = MAX(0, pending_invites - 1)
            WHERE user_id=?
        """, (row[0],))
        conn.commit()
    conn.close()
    return row[0] if row else None


def remove_valid_invite(invitee_id: int):
    conn = get_conn()
    c = conn.cursor()
    row = c.execute(
        "SELECT inviter_id FROM invite_tracking WHERE invitee_id=? AND valid=1 ORDER BY id DESC LIMIT 1",
        (invitee_id,)
    ).fetchone()
    if row:
        c.execute(
            "UPDATE invite_tracking SET valid=0 WHERE invitee_id=? AND valid=1",
            (invitee_id,)
        )
        c.execute("""
            UPDATE invite_balance SET
                total_invites = MAX(0, total_invites - 1),
                robux_balance = MAX(0, robux_balance - ?)
            WHERE user_id=?
        """, (ROBUX_PER_INVITE, row[0]))
        conn.commit()
    conn.close()
    return row[0] if row else None


def get_claimed_today(user_id: int) -> int:
    """Hitung total Robux yang sudah diklaim hari ini."""
    conn = get_conn()
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    row = conn.execute(
        "SELECT COALESCE(SUM(robux_amount), 0) FROM invite_claims WHERE user_id=? AND status='selesai' AND closed_at LIKE ?",
        (user_id, f"{today}%")
    ).fetchone()
    conn.close()
    return row[0] if row else 0


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


def get_setting(key: str, default: str = "") -> str:
    conn = get_conn()
    row = conn.execute(
        "SELECT value FROM invite_settings WHERE key=?",
        (key,)
    ).fetchone()
    conn.close()
    if row and row[0] is not None:
        return str(row[0])
    return default


def set_setting(key: str, value: str):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO invite_settings (key, value) VALUES (?, ?)",
        (key, str(value))
    )
    conn.commit()
    conn.close()


def get_leaderboard(limit: int = 15) -> list:
    """Ambil top member berdasarkan total invite valid."""
    conn = get_conn()
    rows = conn.execute(
        """SELECT user_id, total_invites, robux_balance, total_claimed
        FROM invite_balance
        WHERE total_invites > 0
        ORDER BY total_invites DESC, robux_balance DESC
        LIMIT ?""",
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_pending_invites():
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, inviter_id, invitee_id, joined_at FROM invite_tracking WHERE pending=1"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


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
                value=(
                    "Gunakan link **ini** untuk mengajak teman.\n"
                    "Jangan gunakan link server umum karena tidak akan tercatat!"
                ),
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
        embed.add_field(name="Invite Valid", value=f"**{bal['total_invites']}** orang", inline=True)
        embed.add_field(name="Saldo Robux", value=f"**{bal['robux_balance']}** Robux", inline=True)
        embed.add_field(name="Total Dicairkan", value=f"**{bal['total_claimed']}** Robux", inline=True)
        embed.add_field(name="Pending (belum 3 hari)", value=f"**{bal['pending_invites']}** orang", inline=True)
        embed.add_field(
            name="ℹ️ Info",
            value=(
                f"Setiap 1 invite valid = **{ROBUX_PER_INVITE} Robux**\n"
                f"Invite pending valid setelah **{MIN_STAY_DAYS} hari**\n"
                f"Invite hangus jika member keluar sebelum {MIN_STAY_DAYS} hari"
            ),
            inline=False
        )
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
        embed.add_field(name="Pending", value=f"**{bal['pending_invites']}** orang", inline=True)
        embed.add_field(name="Saldo Robux", value=f"**{bal['robux_balance']}** Robux", inline=True)
        embed.add_field(
            name="ℹ️ Info",
            value=(
                f"Invite otomatis dikonversi ke Robux setelah **{MIN_STAY_DAYS} hari**.\n"
                f"**1 invite valid = {ROBUX_PER_INVITE} Robux**\n\n"
                f"Untuk mencairkan, klik tombol **Pencairan Balance**."
            ),
            inline=False
        )
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
                "Link tidak valid! Harus berupa link dari roblox.com.",
                ephemeral=True
            )
            return

        guild = interaction.guild
        member = interaction.user
        cog = interaction.client.cogs.get("InviteReward")

        # Cek limit harian
        claimed_today = get_claimed_today(member.id)
        if claimed_today + self.robux_balance > MAX_CLAIM_PER_DAY:
            sisa = MAX_CLAIM_PER_DAY - claimed_today
            if sisa <= 0:
                await interaction.response.send_message(
                    f"Kamu sudah mencapai batas klaim harian **{MAX_CLAIM_PER_DAY} Robux**. Coba lagi besok!",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"Kamu hanya bisa klaim **{sisa} Robux** lagi hari ini (batas harian {MAX_CLAIM_PER_DAY} Robux).",
                    ephemeral=True
                )
            return

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
            name="📋 Instruksi Admin",
            value=(
                "1. Buka link gamepass di atas\n"
                "2. Pastikan harganya sesuai saldo member\n"
                "3. Beli gamepass tersebut\n"
                "4. Ketik `!claimeselesai` setelah selesai\n"
                "5. Ketik `!claimbatal [alasan]` jika ada masalah"
            ),
            inline=False
        )
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
        raw = get_setting("leaderboard_message_id", "")
        self.leaderboard_message_id = int(raw) if str(raw).isdigit() else None
        self.validate_pending_task.start()
        self.leaderboard_task.start()

    def cog_unload(self):
        self.validate_pending_task.cancel()
        self.leaderboard_task.cancel()

    async def cog_load(self):
        self.bot.loop.create_task(self._wait_and_cache())

    async def _wait_and_cache(self):
        await self.bot.wait_until_ready()
        await self._cache_invites()
        await self._run_startup_validation()

    async def _run_startup_validation(self):
        """Validasi invite pending saat bot startup."""
        now = datetime.datetime.now(datetime.timezone.utc)
        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            return
        pending = get_pending_invites()
        count = 0
        for inv in pending:
            joined_at = datetime.datetime.fromisoformat(inv["joined_at"])
            if joined_at.tzinfo is None:
                joined_at = joined_at.replace(tzinfo=datetime.timezone.utc)
            days_stayed = (now - joined_at).total_seconds() / 86400
            if days_stayed >= MIN_STAY_DAYS:
                member = guild.get_member(inv["invitee_id"])
                if member:
                    inviter_id = validate_invite(inv["invitee_id"])
                    if inviter_id:
                        count += 1
                else:
                    cancel_pending_invite(inv["invitee_id"])
        if count > 0:
            print(f"[InviteReward] Startup validation: {count} invite divalidasi")

    async def _cache_invites(self):
        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            return
        try:
            invites = await guild.invites()
            self.invite_cache = {inv.code: inv.uses for inv in invites}
        except Exception as e:
            print(f"[InviteReward] Gagal cache invites: {e}")

    @tasks.loop(hours=6)
    async def validate_pending_task(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            return
        pending = get_pending_invites()
        for inv in pending:
            joined_at = datetime.datetime.fromisoformat(inv["joined_at"])
            if joined_at.tzinfo is None:
                joined_at = joined_at.replace(tzinfo=datetime.timezone.utc)
            days_stayed = (now - joined_at).total_seconds() / 86400
            if days_stayed >= MIN_STAY_DAYS:
                member = guild.get_member(inv["invitee_id"])
                if member:
                    inviter_id = validate_invite(inv["invitee_id"])
                    if inviter_id:
                        print(f"[InviteReward] Invite valid: {inv['invitee_id']} diinvite oleh {inviter_id} (+{ROBUX_PER_INVITE} Robux)")
                else:
                    cancel_pending_invite(inv["invitee_id"])

    @validate_pending_task.before_loop
    async def before_validate(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.guild.id != GUILD_ID:
            return
        try:
            account_age = (datetime.datetime.now(datetime.timezone.utc) - member.created_at).days
            if account_age < MIN_ACCOUNT_AGE_DAYS:
                print(f"[InviteReward] {member} akun terlalu baru ({account_age} hari), skip")
                await self._cache_invites()
                return

            invites_after = await member.guild.invites()
            for invite in invites_after:
                uses_before = self.invite_cache.get(invite.code, 0)
                if invite.uses > uses_before:
                    inviter = invite.inviter
                    if inviter and inviter.id != member.id:
                        add_pending_invite(inviter.id, member.id, invite.code)
                        print(f"[InviteReward] {member} diinvite oleh {inviter} (pending {MIN_STAY_DAYS} hari)")
                    break
            self.invite_cache = {inv.code: inv.uses for inv in invites_after}
        except Exception as e:
            print(f"[InviteReward] Error on_member_join: {e}")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if member.guild.id != GUILD_ID:
            return
        try:
            cancel_pending_invite(member.id)
            inviter_id = remove_valid_invite(member.id)
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
        if interaction.channel_id != INVITES_CHANNEL_ID:
            ch = interaction.guild.get_channel(INVITES_CHANNEL_ID)
            mention = ch.mention if ch else "channel invite"
            await interaction.response.send_message(
                f"Gunakan command ini di {mention}!", ephemeral=True
            )
            return
        bal = get_balance(interaction.user.id)
        embed = discord.Embed(
            title=f"🏆 Invite Stats — {interaction.user.display_name}",
            color=0xF1C40F,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.add_field(name="Invite Valid", value=f"**{bal['total_invites']}** orang", inline=True)
        embed.add_field(name="Saldo Robux", value=f"**{bal['robux_balance']}** Robux", inline=True)
        embed.add_field(name="Total Dicairkan", value=f"**{bal['total_claimed']}** Robux", inline=True)
        embed.add_field(name="Pending (belum 3 hari)", value=f"**{bal['pending_invites']}** orang", inline=True)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        embed.set_footer(text=STORE_NAME)
        await interaction.response.send_message(embed=embed)

    @commands.command(name="invitereward")
    async def send_embed(self, ctx):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        await ctx.message.delete()
        ch = ctx.guild.get_channel(INVITE_REWARD_CHANNEL_ID)
        if not ch:
            await ctx.send("Channel invite reward tidak ditemukan!", delete_after=5)
            return

        invites_ch = ctx.guild.get_channel(INVITES_CHANNEL_ID)
        invites_mention = invites_ch.mention if invites_ch else "#invite-stats"

        embed1 = discord.Embed(
            title="🎉 Invite Reward — Cellyn Store",
            description=(
                f"Ajak teman ke server dan dapatkan **Robux gratis!**\n\n"
                f"💎 **{ROBUX_PER_INVITE} Robux** per 1 invite yang valid\n"
                f"✅ Invite valid setelah member stay **{MIN_STAY_DAYS} hari**\n"
                f"❌ Invite hangus jika member keluar sebelum {MIN_STAY_DAYS} hari\n"
                f"🔞 Akun Discord harus berumur minimal **{MIN_ACCOUNT_AGE_DAYS} hari**\n"
                f"📊 Maksimal klaim **{MAX_CLAIM_PER_DAY} Robux** per hari\n\n"
                f"⚠️ **PENTING:** Gunakan link dari tombol **🔗 Dapatkan Invite Link** di bawah.\n"
                f"Link `discord.gg/cellynstore` atau link server umum **TIDAK akan tercatat!**"
            ),
            color=0xF1C40F
        )
        embed1.add_field(name="📋 Tutorial Membuat Gamepass", value=TUTORIAL_GAMEPASS, inline=False)
        embed1.set_footer(text=STORE_NAME)

        embed2 = discord.Embed(color=0xF1C40F)
        embed2.add_field(
            name="💸 Tabel Harga Gamepass (Potongan 30% Roblox)",
            value=(
                "```\n"
                "Ingin Terima  | Set Harga GP\n"
                "5 Robux       | 8 Robux\n"
                "10 Robux      | 15 Robux\n"
                "15 Robux      | 22 Robux\n"
                "20 Robux      | 29 Robux\n"
                "25 Robux      | 36 Robux\n"
                "50 Robux      | 72 Robux\n"
                "100 Robux     | 143 Robux\n"
                "```\n"
                "Rumus: **Harga GP = Robux ÷ 0.7** (bulatkan ke atas)"
            ),
            inline=False
        )
        embed2.add_field(
            name="💰 Cara Klaim Robux",
            value=(
                "1. Klik **🔗 Dapatkan Invite Link** → share ke teman\n"
                "2. Tunggu **3 hari** setelah teman join → invite otomatis valid\n"
                "3. Buat gamepass dengan harga sesuai tabel di atas\n"
                "4. Klik **💰 Pencairan Balance** → paste link gamepass\n"
                "5. Admin beli gamepass → Robux masuk ke akunmu! 🎉"
            ),
            inline=False
        )
        embed2.add_field(
            name="📊 Cek Invite Kamu",
            value=f"Ketik `/invites` di {invites_mention} untuk lihat jumlah invite & saldo Robuxmu!",
            inline=False
        )
        embed2.add_field(name="📜 Syarat & Ketentuan", value=SKK, inline=False)
        embed2.add_field(
            name="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            value=(
                "🔗 **Dapatkan Invite Link** — link unik untuk undang teman\n"
                "🏆 **Check Balance** — lihat saldo Robux kamu\n"
                "🔄 **Convert** — info konversi invite ke Robux\n"
                "💰 **Pencairan** — cairkan Robux ke akun kamu"
            ),
            inline=False
        )
        embed2.set_footer(text=f"{STORE_NAME} • Invite sekarang dan kumpulkan Robux!")

        async for msg in ch.history(limit=10):
            if msg.author == ctx.guild.me:
                try:
                    await msg.delete()
                except Exception:
                    pass

        await ch.send(embed=embed1)
        sent = await ch.send(embed=embed2, view=InviteRewardView())
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
            log_embed = discord.Embed(title="💰 PENCAIRAN INVITE REWARD SUKSES", color=0xF1C40F, timestamp=now)
            log_embed.add_field(name="Admin", value=f"{ctx.author.mention}\n`{ctx.author.id}`", inline=False)
            log_embed.add_field(name="Member", value=f"{member.mention if member else ticket['user_id']}", inline=False)
            log_embed.add_field(name="Jumlah", value=f"**{ticket['robux_amount']} Robux**", inline=False)
            log_embed.add_field(name="Gamepass", value=ticket["gamepass_link"], inline=False)
            log_embed.set_footer(text=STORE_NAME)
            await log_ch.send(embed=log_embed)

        await ctx.send(
            f"{member.mention if member else ''} Pencairan **{ticket['robux_amount']} Robux** berhasil! "
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


    @tasks.loop(hours=1)
    async def leaderboard_task(self):
        """Update leaderboard setiap 1 jam."""
        await self._update_leaderboard()

    @leaderboard_task.before_loop
    async def before_leaderboard(self):
        await self.bot.wait_until_ready()

    async def _update_leaderboard(self):
        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            return
        ch = guild.get_channel(LEADERBOARD_CHANNEL_ID)
        if not ch:
            return

        data = get_leaderboard(LEADERBOARD_TOP)
        now = datetime.datetime.now(datetime.timezone.utc)

        medals = ["🥇", "🥈", "🥉"]
        rank_icons = ["4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟","1️⃣1️⃣","1️⃣2️⃣","1️⃣3️⃣","1️⃣4️⃣","1️⃣5️⃣"]

        if not data:
            board = "*Belum ada yang masuk leaderboard. Mulai invite sekarang!*"
        else:
            lines = []
            for i, row in enumerate(data):
                member = guild.get_member(row["user_id"])
                name = member.display_name if member else f"User#{row['user_id']}"
                icon = medals[i] if i < 3 else rank_icons[i - 3]
                line = f"{icon} **{name}**\n┗ `{row['total_invites']} invite` • `{row['robux_balance']} Robux saldo`"
                lines.append(line)
            board = "\n\n".join(lines)

        desc = (
            f"**Top {LEADERBOARD_TOP} Inviter Terbaik Cellyn Store**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{board}\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        embed = discord.Embed(
            title="🏆  INVITE REWARD LEADERBOARD",
            description=desc,
            color=0xF1C40F,
            timestamp=now
        )
        info_val = (
            "Invite **1 orang** = **5 Robux** 💎\n"
            "Leaderboard update setiap **1 jam** sekali\n"
            "Invite harus stay **3 hari** untuk dihitung valid"
        )
        embed.add_field(
            name="📊 Info",
            value=info_val,
            inline=False
        )
        embed.set_footer(text=f"{STORE_NAME} • Last update")

        # Edit pesan lama kalau ada, kalau tidak kirim baru
        if self.leaderboard_message_id:
            try:
                msg = await ch.fetch_message(self.leaderboard_message_id)
                await msg.edit(embed=embed)
                return
            except Exception:
                pass

        # Hapus pesan lama bot di channel
        async for msg in ch.history(limit=10):
            if msg.author == guild.me:
                try:
                    await msg.delete()
                except Exception:
                    pass

        sent = await ch.send(embed=embed)
        self.leaderboard_message_id = sent.id
        set_setting("leaderboard_message_id", str(sent.id))

    @commands.command(name="leaderboard")
    async def leaderboard_cmd(self, ctx):
        """Admin: kirim/refresh leaderboard manual."""
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        await ctx.message.delete()
        await self._update_leaderboard()
        await ctx.send("Leaderboard diperbarui!", delete_after=5)

async def setup(bot):
    await bot.add_cog(InviteReward(bot))
    bot.add_view(InviteRewardView())
    print("Cog InviteReward siap.")
