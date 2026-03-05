content = open('cogs/midman.py').read()
old = '    GUILD_ID, MIDMAN_CHANNEL_ID, ADMIN_ROLE_ID,\n    TRANSCRIPT_CHANNEL_ID, LOG_CHANNEL_ID, STORE_NAME, BACKUP_CHANNEL_ID'
new = '    GUILD_ID, MIDMAN_CHANNEL_ID, ADMIN_ROLE_ID,\n    TRANSCRIPT_CHANNEL_ID, LOG_CHANNEL_ID, STORE_NAME, BACKUP_CHANNEL_ID, ERROR_LOG_CHANNEL_ID'
content = content.replace(old, new)

old = '    @commands.Cog.listener()\n    async def on_command_error(self, ctx, error):\n        if isinstance(error, commands.MissingRole):\n            return\n        log_ch = ctx.guild.get_channel(LOG_CHANNEL_ID)\n        if log_ch:\n            await log_ch.send(\n                f"ERROR LOG\\n"\n                f"Error pada command `{ctx.command}` oleh {ctx.author.mention}:\\n"\n                f"`{error}`"\n            )\n        print(f"[ERROR] {ctx.command}: {error}")'
new = '    @commands.Cog.listener()\n    async def on_command_error(self, ctx, error):\n        if isinstance(error, commands.MissingRole):\n            return\n        if isinstance(error, commands.CommandNotFound):\n            return\n        err_ch = ctx.guild.get_channel(ERROR_LOG_CHANNEL_ID)\n        if err_ch:\n            await err_ch.send(\n                f"ERROR LOG\\n"\n                f"Error pada command `{ctx.command}` oleh {ctx.author.mention}:\\n"\n                f"`{error}`"\n            )\n        print(f"[ERROR] {ctx.command}: {error}")'
content = content.replace(old, new)
open('cogs/midman.py', 'w').write(content)
print("Done!")
