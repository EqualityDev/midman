content = open('cogs/midman.py').read()
old = '    @commands.command(name="fee")'
new = '    @commands.command(name="ping")\n    async def ping(self, ctx):\n        latency = round(self.bot.latency * 1000)\n        await ctx.send(f"Pong! Latency: {latency}ms")\n\n    @commands.command(name="fee")'
content = content.replace(old, new)
open('cogs/midman.py', 'w').write(content)
print("Done!")
