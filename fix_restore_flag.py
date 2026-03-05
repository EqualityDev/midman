content = open('cogs/midman.py').read()

old = '    def __init__(self, bot):\n        self.bot = bot\n        self.active_tickets = {}'
new = '    def __init__(self, bot):\n        self.bot = bot\n        self.active_tickets = {}\n        self.restored = False'
content = content.replace(old, new)

old = '        await do_restore(self.bot, BACKUP_CHANNEL_ID)'
new = '        if not self.restored:\n            await do_restore(self.bot, BACKUP_CHANNEL_ID)\n            self.restored = True'
content = content.replace(old, new)

open('cogs/midman.py', 'w').write(content)
print("Done!")
