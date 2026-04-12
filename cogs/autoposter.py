import asyncio
import aiohttp
import discord
from discord.ext import commands, tasks
from utils.autoposter_settings import (
    get_autopost_tasks,
    update_autopost_counter,
    update_autopost_last_post,
    log_autopost_history,
    init_autopost_tables
)
from utils.config import ADMIN_ROLE_ID

LOOP_INTERVAL = 60

class AutoPosterCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        init_autopost_tables()
        print("Cog AutoPoster siap.")
        self.autopost_loop.start()

    def cog_unload(self):
        self.autopost_loop.cancel()

    @tasks.loop(seconds=LOOP_INTERVAL)
    async def autopost_loop(self):
        tasks = get_autopost_tasks()
        for task in tasks:
            if not task.get("is_active"):
                continue

            channel_id = int(task["channel_id"])
            channel = self.bot.get_channel(channel_id)
            if not channel:
                continue

            new_counter = task.get("loop_counter", 0) + LOOP_INTERVAL
            threshold = task["interval_minutes"] * 60

            if new_counter >= threshold:
                success = await self._post_message(channel, task["message"], task.get("user_token", ""))
                log_autopost_history(task["id"], task["message"], "success" if success else "failed")
                if success:
                    update_autopost_last_post(task["id"])
                else:
                    update_autopost_counter(task["id"], 0)
            else:
                update_autopost_counter(task["id"], new_counter)

    async def _post_message(self, channel, message, user_token):
        try:
            headers = {
                "Authorization": user_token,
                "Content-Type": "application/json"
            }
            payload = {"content": message}
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"https://discord.com/api/v9/channels/{channel.id}/messages",
                    json=payload,
                    headers=headers
                ) as resp:
                    text = await resp.text()
                    print(f"[AUTOPOST] Status: {resp.status}, Response: {text[:200]}")
                    return resp.status in (200, 201)
        except Exception as e:
            print(f"[AUTOPOST] Error: {e}")
            return False

    @commands.group(name="autopost", invoke_without_command=True)
    async def autopost(self, ctx):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        await ctx.send_help(self.autopost)
        await asyncio.sleep(30)
        try:
            await ctx.message.delete()
        except Exception:
            pass

    @autopost.command(name="add")
    async def autopost_add(self, ctx, channel: discord.TextChannel, interval: int, *, message: str):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        from utils.autoposter_settings import add_autopost_task
        from utils.config import AUTOPOSTER_TOKEN
        token = AUTOPOSTER_TOKEN or ""
        task_id = add_autopost_task(str(channel.id), message, interval, token)
        embed = discord.Embed(
            title="AutoPost Ditambahkan",
            color=0x00FF00
        )
        embed.add_field(name="ID", value=task_id, inline=True)
        embed.add_field(name="Channel", value=channel.mention, inline=True)
        embed.add_field(name="Interval", value=f"{interval} menit", inline=True)
        embed.add_field(name="Message", value=message[:100], inline=False)
        await ctx.send(embed=embed, delete_after=30)
        await ctx.message.delete()

    @autopost.command(name="list")
    async def autopost_list(self, ctx):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        tasks = get_autopost_tasks()
        if not tasks:
            await ctx.send("Tidak ada autopost task.", delete_after=10)
            await ctx.message.delete()
            return
        embed = discord.Embed(
            title="AutoPost Tasks",
            color=0x5865F2
        )
        for t in tasks[:10]:
            status = "🟢" if t.get("is_active") else "🔴"
            embed.add_field(
                name=f"{status} #{t['id']}",
                value=f"Channel: <#{t['channel_id']}>\nInterval: {t['interval_minutes']}m\nPesan: {t['message'][:50]}...",
                inline=False
            )
        await ctx.send(embed=embed, delete_after=30)
        await ctx.message.delete()

    @autopost.command(name="toggle")
    async def autopost_toggle(self, ctx, task_id: int):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        from utils.autoposter_settings import toggle_autopost_task
        toggle_autopost_task(task_id)
        await ctx.message.delete()
        await ctx.send(f"AutoPost #{task_id} toggled.", delete_after=10)

    @autopost.command(name="delete")
    async def autopost_delete(self, ctx, task_id: int):
        if not any(r.id == ADMIN_ROLE_ID for r in ctx.author.roles):
            return
        from utils.autoposter_settings import delete_autopost_task
        delete_autopost_task(task_id)
        await ctx.send(f"AutoPost #{task_id} dihapus.", delete_after=10)
        await ctx.message.delete()

async def setup(bot):
    await bot.add_cog(AutoPosterCog(bot))
