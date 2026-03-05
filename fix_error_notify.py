content = open('cogs/midman.py').read()
old = '    @commands.Cog.listener()\n    async def on_ready(self):'
new = '    @commands.Cog.listener()\n    async def on_command_error(self, ctx, error):\n        if isinstance(error, commands.MissingRole):\n            return\n        log_ch = ctx.guild.get_channel(LOG_CHANNEL_ID)\n        if log_ch:\n            await log_ch.send(\n                f"ERROR LOG\\n"\n                f"Error pada command `{ctx.command}` oleh {ctx.author.mention}:\\n"\n                f"`{error}`"\n            )\n        print(f"[ERROR] {ctx.command}: {error}")\n\n    @commands.Cog.listener()\n    async def on_ready(self):'
content = content.replace(old, new)
open('cogs/midman.py', 'w').write(content)
print("Done!")
