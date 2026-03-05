lines = open('cogs/midman.py').readlines()
new_lines = []
skip_until = None
i = 0
while i < len(lines):
    line = lines[i]
    # Temukan awal on_ready
    if '    async def on_ready(self):' in line:
        new_lines.append(line)
        new_lines.append('        if not self.restored:\n')
        new_lines.append('            await do_restore(self.bot, BACKUP_CHANNEL_ID)\n')
        new_lines.append('            from utils.db import init_db\n')
        new_lines.append('            init_db()\n')
        new_lines.append('            self.restored = True\n')
        new_lines.append('\n')
        new_lines.append('        guild = self.bot.get_guild(GUILD_ID)\n')
        new_lines.append('        if guild:\n')
        new_lines.append('            await load_tickets(guild, self.active_tickets)\n')
        new_lines.append('        self.bot.add_view(MidmanMainView())\n')
        new_lines.append('        self.bot.add_view(AdminSetupView())\n')
        new_lines.append('        self.bot.add_view(TradeFinishView())\n')
        # Skip baris lama sampai ketemu print Cog Midman siap
        i += 1
        while i < len(lines) and 'print("Cog Midman siap.")' not in lines[i]:
            i += 1
        continue
    new_lines.append(line)
    i += 1
open('cogs/midman.py', 'w').writelines(new_lines)
print("Done!")
