# Fix main.py - hapus init_db dari sini
content = open('main.py').read()
content = content.replace(
    'from utils.db import init_db\ninit_db()\n\n',
    ''
)
open('main.py', 'w').write(content)

# Fix midman.py - init_db dipanggil setelah restore
content = open('cogs/midman.py').read()
content = content.replace(
    '        if not self.restored:\n            await do_restore(self.bot, BACKUP_CHANNEL_ID)\n            self.restored = True',
    '        if not self.restored:\n            await do_restore(self.bot, BACKUP_CHANNEL_ID)\n            from utils.db import init_db\n            init_db()\n            self.restored = True'
)
open('cogs/midman.py', 'w').write(content)
print("Done!")
