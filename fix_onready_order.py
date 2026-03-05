content = open('cogs/midman.py').read()

old = '''        guild = self.bot.get_guild(GUILD_ID)
        if guild:
            await load_tickets(guild, self.active_tickets)
        self.bot.add_view(MidmanMainView())
        self.bot.add_view(AdminSetupView())
        self.bot.add_view(TradeFinishView())

        if not self.restored:
            await do_restore(self.bot, BACKUP_CHANNEL_ID)
            from utils.db import init_db
            init_db()
            self.restored = True'''

new = '''        if not self.restored:
            await do_restore(self.bot, BACKUP_CHANNEL_ID)
            from utils.db import init_db
            init_db()
            self.restored = True

        guild = self.bot.get_guild(GUILD_ID)
        if guild:
            await load_tickets(guild, self.active_tickets)
        self.bot.add_view(MidmanMainView())
        self.bot.add_view(AdminSetupView())
        self.bot.add_view(TradeFinishView())'''

content = content.replace(old, new)
open('cogs/midman.py', 'w').write(content)
print("Done!")
