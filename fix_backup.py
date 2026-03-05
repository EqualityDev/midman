content = open('cogs/midman.py').read()

# Tambah import backup
old = 'from cogs.views import MidmanMainView, AdminSetupView, TradeFinishView'
new = 'from cogs.views import MidmanMainView, AdminSetupView, TradeFinishView\nfrom utils.backup import do_backup, do_restore'
content = content.replace(old, new)

# Tambah import TRANSCRIPT_CHANNEL_ID
old = '    GUILD_ID, MIDMAN_CHANNEL_ID, ADMIN_ROLE_ID,\n    TRANSCRIPT_CHANNEL_ID, LOG_CHANNEL_ID, STORE_NAME'
new = '    GUILD_ID, MIDMAN_CHANNEL_ID, ADMIN_ROLE_ID,\n    TRANSCRIPT_CHANNEL_ID, LOG_CHANNEL_ID, STORE_NAME\n'
content = content.replace(old, new)

# Tambah task backup setelah cog_unload
old = '    def cog_unload(self):\n        self.ticket_timeout_check.cancel()'
new = '    def cog_unload(self):\n        self.ticket_timeout_check.cancel()\n        self.auto_backup.cancel()\n\n    @tasks.loop(hours=6)\n    async def auto_backup(self):\n        await do_backup(self.bot, TRANSCRIPT_CHANNEL_ID)\n\n    @auto_backup.before_loop\n    async def before_auto_backup(self):\n        await self.bot.wait_until_ready()'
content = content.replace(old, new)

# Tambah restore dan start backup di on_ready
old = '        self.ticket_timeout_check.start()\n        print("Cog Midman siap.")'
new = '        await do_restore(self.bot, TRANSCRIPT_CHANNEL_ID)\n        self.ticket_timeout_check.start()\n        self.auto_backup.start()\n        print("Cog Midman siap.")'
content = content.replace(old, new)

open('cogs/midman.py', 'w').write(content)
print("Done!")
