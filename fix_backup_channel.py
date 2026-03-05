# Fix midman.py
content = open('cogs/midman.py').read()
content = content.replace(
    'from utils.backup import do_backup, do_restore\nfrom utils.backup import do_backup, do_restore',
    'from utils.backup import do_backup, do_restore'
)
content = content.replace(
    '    GUILD_ID, MIDMAN_CHANNEL_ID, ADMIN_ROLE_ID,\n    TRANSCRIPT_CHANNEL_ID, LOG_CHANNEL_ID, STORE_NAME\n',
    '    GUILD_ID, MIDMAN_CHANNEL_ID, ADMIN_ROLE_ID,\n    TRANSCRIPT_CHANNEL_ID, LOG_CHANNEL_ID, STORE_NAME, BACKUP_CHANNEL_ID'
)
content = content.replace(
    'await do_backup(self.bot, TRANSCRIPT_CHANNEL_ID)',
    'await do_backup(self.bot, BACKUP_CHANNEL_ID)'
)
content = content.replace(
    'await do_restore(self.bot, TRANSCRIPT_CHANNEL_ID)',
    'await do_restore(self.bot, BACKUP_CHANNEL_ID)'
)
open('cogs/midman.py', 'w').write(content)
print("Fixed midman.py")
