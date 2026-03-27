"""
cogs/embed_builder.py
Diload di main.py seperti cog lainnya.
"""
import discord
from discord.ext import commands
from discord import app_commands
import sqlite3, json, os

DB_PATH = os.getenv("DB_PATH", "midman.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def dict_to_embed(data: dict) -> discord.Embed:
    embed = discord.Embed()

    if data.get("title"):
        embed.title = data["title"]
    if data.get("url"):
        embed.url = data["url"]
    if data.get("description"):
        embed.description = data["description"]
    if data.get("color"):
        try:
            embed.color = int(data["color"].lstrip("#"), 16)
        except Exception:
            pass
    if data.get("timestamp"):
        from datetime import datetime
        try:
            embed.timestamp = datetime.fromisoformat(data["timestamp"])
        except Exception:
            pass

    author = data.get("author", {})
    if author.get("name"):
        embed.set_author(
            name=author["name"],
            url=author.get("url") or discord.Embed.Empty,
            icon_url=author.get("icon_url") or discord.Embed.Empty
        )

    if data.get("thumbnail"):
        embed.set_thumbnail(url=data["thumbnail"])
    if data.get("image"):
        embed.set_image(url=data["image"])

    footer = data.get("footer", {})
    if footer.get("text"):
        embed.set_footer(
            text=footer["text"],
            icon_url=footer.get("icon_url") or discord.Embed.Empty
        )

    for field in data.get("fields", []):
        if field.get("name") and field.get("value"):
            embed.add_field(
                name=field["name"],
                value=field["value"],
                inline=field.get("inline", False)
            )

    return embed


class EmbedBuilder(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── Slash: list embed terkirim ──────────────────────────────
    @app_commands.command(name="embed_list", description="[Admin] List semua embed yang pernah dikirim via builder")
    @app_commands.checks.has_permissions(administrator=True)
    async def embed_list(self, interaction: discord.Interaction):
        conn = get_db()
        rows = conn.execute(
            "SELECT id, label, channel_id, message_id, sent_at FROM embed_messages ORDER BY sent_at DESC LIMIT 20"
        ).fetchall()
        conn.close()

        if not rows:
            return await interaction.response.send_message("Belum ada embed yang dikirim via builder.", ephemeral=True)

        embed = discord.Embed(title="📋 Embed Terkirim", color=0x5865F2)
        for r in rows:
            ch = self.bot.get_channel(int(r["channel_id"]))
            ch_name = f"<#{r['channel_id']}>" if ch else r["channel_id"]
            embed.add_field(
                name=f"#{r['id']} — {r['label']}",
                value=f"Channel: {ch_name}\nMessage ID: `{r['message_id']}`\nDikirim: {r['sent_at'][:16]}",
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── Slash: delete embed terkirim ───────────────────────────
    @app_commands.command(name="embed_delete", description="[Admin] Hapus embed yang dikirim bot (dari Discord & DB)")
    @app_commands.describe(message_id="Message ID embed yang mau dihapus")
    @app_commands.checks.has_permissions(administrator=True)
    async def embed_delete(self, interaction: discord.Interaction, message_id: str):
        conn = get_db()
        row = conn.execute(
            "SELECT * FROM embed_messages WHERE message_id = ?", (message_id,)
        ).fetchone()

        if not row:
            conn.close()
            return await interaction.response.send_message("❌ Message ID tidak ditemukan di DB.", ephemeral=True)

        try:
            ch = self.bot.get_channel(int(row["channel_id"]))
            if ch:
                msg = await ch.fetch_message(int(message_id))
                await msg.delete()
        except Exception:
            pass

        conn.execute("DELETE FROM embed_messages WHERE message_id = ?", (message_id,))
        conn.commit()
        conn.close()

        await interaction.response.send_message(f"✅ Embed `{row['label']}` berhasil dihapus.", ephemeral=True)

    @embed_list.error
    @embed_delete.error
    async def admin_error(self, interaction: discord.Interaction, error):
        await interaction.response.send_message("❌ Kamu tidak punya izin.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(EmbedBuilder(bot))
