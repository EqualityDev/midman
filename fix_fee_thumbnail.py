content = open('cogs/midman.py').read()
old = '        embed.set_footer(text=STORE_NAME)\n        await ctx.send(embed=embed)'
new = '        embed.set_thumbnail(url="https://i.imgur.com/z4nrBHl.png")\n        embed.set_footer(text=STORE_NAME)\n        await ctx.send(embed=embed)'
content = content.replace(old, new)
open('cogs/midman.py', 'w').write(content)
print("Done!")
