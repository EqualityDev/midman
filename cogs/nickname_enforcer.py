import os
import discord
from discord.ext import commands

SUFFIX = "| Cellyn Team"
TEAM_ROLE_ID = int(os.getenv("CELLYN_TEAM_ROLE_ID", 0))


def build_nick(member: discord.Member) -> str:
    base = member.nick if member.nick else member.name
    base = base.replace(f" {SUFFIX}", "").replace(SUFFIX, "").strip()
    return f"{base} {SUFFIX}"


def has_team_role(member: discord.Member) -> bool:
    return any(r.id == TEAM_ROLE_ID for r in member.roles)


class NicknameEnforcer(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._processing: set[int] = set()

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if after.id in self._processing:
            return

        should_enforce = has_team_role(after)
        current_nick = after.nick if after.nick else after.name

        if should_enforce and not current_nick.endswith(SUFFIX):
            new_nick = build_nick(after)
            if len(new_nick) > 32:
                new_nick = new_nick[:32]
            self._processing.add(after.id)
            try:
                await after.edit(nick=new_nick, reason="Auto-enforce Cellyn Team suffix")
            except discord.Forbidden:
                pass
            finally:
                self._processing.discard(after.id)

        elif not should_enforce and after.nick and after.nick.endswith(SUFFIX):
            cleaned = after.nick.replace(f" {SUFFIX}", "").replace(SUFFIX, "").strip()
            self._processing.add(after.id)
            try:
                await after.edit(
                    nick=cleaned if cleaned != after.name else None,
                    reason="Role Cellyn Team dicabut, suffix dihapus"
                )
            except discord.Forbidden:
                pass
            finally:
                self._processing.discard(after.id)

    @commands.command(name="nickcheck")
    @commands.has_permissions(administrator=True)
    async def nickcheck(self, ctx: commands.Context):
        """Force-sync nickname semua member Cellyn Team."""
        role = ctx.guild.get_role(TEAM_ROLE_ID)

        if not role:
            await ctx.send("Role Cellyn Team tidak ditemukan. Cek `CELLYN_TEAM_ROLE_ID` di .env", delete_after=10)
            return

        msg = await ctx.send(f"Memeriksa {len(role.members)} member...")
        updated = 0
        skipped = 0

        for member in role.members:
            current = member.nick if member.nick else member.name
            if not current.endswith(SUFFIX):
                new_nick = build_nick(member)
                if len(new_nick) > 32:
                    new_nick = new_nick[:32]
                try:
                    await member.edit(nick=new_nick, reason="!nickcheck — enforce Cellyn Team suffix")
                    updated += 1
                except discord.Forbidden:
                    skipped += 1
            else:
                skipped += 1

        await msg.edit(content=(
            f"**nickcheck selesai**\n"
            f"Updated: `{updated}` | Skipped/gagal: `{skipped}`"
        ))

    @nickcheck.error
    async def nickcheck_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("Perlu permission Administrator.", delete_after=5)


async def setup(bot: commands.Bot):
    await bot.add_cog(NicknameEnforcer(bot))
