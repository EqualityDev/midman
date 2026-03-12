import discord
import asyncio
import datetime
import json
import os

from discord.ext import commands, tasks
from utils.db import get_conn

AUTOPOST_TEST_FILE = os.path.join(os.path.dirname(__file__), "..", ".autopost_test")


def _log_autopost(task_id: int, label: str, channel_id: str, status: str, note: str = None):
    try:
        conn = get_conn()
        conn.execute(
            "INSERT INTO autopost_log (task_id, task_label, channel_id, status, note, sent_at) VALUES (?,?,?,?,?,?)",
            (task_id, label, channel_id, status, note,
             datetime.datetime.now(datetime.timezone.utc).isoformat())
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[AUTOPOST] Gagal log: {e}")


def _color_to_int(hex_color: str) -> int:
    try:
        return int(hex_color.lstrip("#"), 16)
    except Exception:
        return 0x5865F2


class AutopostCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.autopost_loop.start()
        self.test_loop.start()
        print("Cog Autopost siap.")

    def cog_unload(self):
        self.autopost_loop.cancel()
        self.test_loop.cancel()

    async def _send_task(self, task: dict, is_test: bool = False) -> tuple:
        """Kirim satu task. Return (sukses, note)."""
        try:
            channel = self.bot.get_channel(int(task["channel_id"]))
            if not channel:
                return False, "Channel tidak ditemukan"

            if task.get("use_embed"):
                embed = discord.Embed(
                    title=task.get("embed_title") or "",
                    description=task["message"],
                    color=_color_to_int(task.get("embed_color") or "#5865F2"),
                    timestamp=datetime.datetime.now(datetime.timezone.utc)
                )
                if is_test:
                    embed.set_footer(text="[TEST] Autopost")
                await channel.send(embed=embed)
            else:
                msg = task["message"]
                if is_test:
                    msg = f"**[TEST]** {msg}"
                await channel.send(msg)

            return True, "OK"
        except discord.Forbidden:
            return False, "Bot tidak punya izin kirim di channel ini"
        except discord.HTTPException as e:
            return False, f"HTTP error: {e}"
        except Exception as e:
            return False, str(e)

    @tasks.loop(minutes=1)
    async def autopost_loop(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        try:
            conn = get_conn()
            tasks_list = conn.execute(
                "SELECT * FROM autopost_tasks WHERE active=1"
            ).fetchall()
            conn.close()
        except Exception as e:
            print(f"[AUTOPOST] Gagal ambil tasks: {e}")
            return

        for task in tasks_list:
            try:
                next_send = task["next_send"]
                if not next_send:
                    continue

                next_dt = datetime.datetime.fromisoformat(next_send)
                if next_dt.tzinfo is None:
                    next_dt = next_dt.replace(tzinfo=datetime.timezone.utc)

                if now < next_dt:
                    continue

                # Kirim
                ok, note = await self._send_task(dict(task))
                _log_autopost(task["id"], task["label"], task["channel_id"],
                              "sukses" if ok else "gagal", note if not ok else None)

                # Hitung next_send berikutnya
                sched = task["scheduled_time"]
                if sched:
                    try:
                        h, m = map(int, sched.split(":"))
                        nxt = now.replace(hour=h, minute=m, second=0, microsecond=0)
                        if nxt <= now:
                            nxt += datetime.timedelta(days=1)
                    except Exception:
                        nxt = now + datetime.timedelta(minutes=task["interval_minutes"] or 60)
                else:
                    nxt = now + datetime.timedelta(minutes=task["interval_minutes"] or 60)

                conn = get_conn()
                conn.execute(
                    "UPDATE autopost_tasks SET last_sent=?, next_send=? WHERE id=?",
                    (now.isoformat(), nxt.isoformat(), task["id"])
                )
                conn.commit()
                conn.close()

                if not ok:
                    print(f"[AUTOPOST] Task '{task['label']}' gagal: {note}")

            except Exception as e:
                print(f"[AUTOPOST] Error task {task['id']}: {e}")

    @autopost_loop.before_loop
    async def before_autopost(self):
        await self.bot.wait_until_ready()

    @tasks.loop(seconds=5)
    async def test_loop(self):
        """Cek .autopost_test dari admin panel untuk test kirim."""
        if not os.path.exists(AUTOPOST_TEST_FILE):
            return
        try:
            with open(AUTOPOST_TEST_FILE) as f:
                data = json.load(f)
            os.remove(AUTOPOST_TEST_FILE)
            ok, note = await self._send_task(data, is_test=True)
            _log_autopost(
                data["task_id"], data["label"], data["channel_id"],
                "sukses (test)" if ok else "gagal (test)",
                note if not ok else "Test kirim dari admin panel"
            )
        except Exception as e:
            print(f"[AUTOPOST] Test error: {e}")
            try:
                os.remove(AUTOPOST_TEST_FILE)
            except Exception:
                pass

    @test_loop.before_loop
    async def before_test(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(AutopostCog(bot))
