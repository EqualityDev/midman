content = open('cogs/midman.py').read()
old = "    @commands.command(name='ping')"
new = """    @commands.command(name='update')
    @commands.has_role(ADMIN_ROLE_ID)
    async def update(self, ctx):
        await ctx.send("Mengunduh update dari GitHub...")
        proc = await asyncio.create_subprocess_shell(
            'git pull origin main',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        output = stdout.decode() or stderr.decode()
        await ctx.send(f"```\\n{output[:1900]}\\n```")
        if proc.returncode == 0:
            await ctx.send("Update selesai! Bot akan restart dalam 3 detik...")
            await asyncio.sleep(3)
            import os, sys
            os.execv(sys.executable, [sys.executable] + sys.argv)
        else:
            await ctx.send("Update gagal! Cek log di atas.")

    @commands.command(name='ping')"""
content = content.replace(old, new)
open('cogs/midman.py', 'w').write(content)
print("Done!")
