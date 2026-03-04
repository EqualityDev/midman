import discord
import os
import datetime

TICKETS_FILE = "tickets.json"
COUNTER_FILE = "ticket_counter.json"
BACKUP_LABEL = "MIDMAN-BACKUP"

async def do_backup(bot, channel_id):
    channel = bot.get_channel(channel_id)
    if not channel:
        print("[BACKUP] Channel tidak ditemukan.")
        return
    files = []
    for f in [TICKETS_FILE, COUNTER_FILE]:
        if os.path.exists(f):
            files.append(discord.File(f))
    if not files:
        print("[BACKUP] Tidak ada file untuk di-backup.")
        return
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
    await channel.send(
        content=f"🗄️ **{BACKUP_LABEL}**\n🗓️ {now}\n📁 `{TICKETS_FILE}` & `{COUNTER_FILE}`",
        files=files
    )
    print(f"[BACKUP] Backup berhasil dikirim ke channel {channel_id}.")

async def do_restore(bot, channel_id):
    restored = []
    for filename in [TICKETS_FILE, COUNTER_FILE]:
        if os.path.exists(filename):
            continue
        channel = bot.get_channel(channel_id)
        if not channel:
            print("[RESTORE] Channel tidak ditemukan.")
            return
        async for msg in channel.history(limit=50):
            if BACKUP_LABEL not in (msg.content or ""):
                continue
            for attachment in msg.attachments:
                if attachment.filename == filename:
                    await attachment.save(filename)
                    print(f"[RESTORE] {filename} berhasil di-restore dari backup.")
                    restored.append(filename)
                    break
            if filename in restored:
                break
    return restored
