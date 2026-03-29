"""
autopost.py — Cellyn Store Auto Post
Jalankan terpisah dari bot: python autopost.py
Baca task dari DB, kirim pesan ke Discord pakai user token.

Setup:
  Isi USER_TOKEN di .env:
    AUTOPOST_TOKEN=user_token_kamu_di_sini

Cara jalankan di Termux (background):
  nohup python autopost.py > autopost.log 2>&1 &
"""

import os
import sys
import time
import sqlite3
import json
import requests
import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "midman.db")

# Load .env manual (tidak pakai python-dotenv agar ringan)
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(_env_path):
    for line in open(_env_path):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

USER_TOKEN = os.environ.get("AUTOPOST_TOKEN", "")
BOT_TOKEN  = os.environ.get("TOKEN", "")
CHECK_INTERVAL = 60  # cek DB setiap 60 detik


def get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_table():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS autopost_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            label TEXT NOT NULL,
            channel_id TEXT NOT NULL,
            message TEXT NOT NULL,
            interval_minutes INTEGER NOT NULL DEFAULT 60,
            active INTEGER NOT NULL DEFAULT 1,
            last_sent TEXT DEFAULT NULL,
            embed_json TEXT DEFAULT NULL,
            content TEXT DEFAULT NULL
        )
    """)
    conn.commit()
    conn.close()


def send_embed(channel_id: str, embed_json_str: str, content_msg: str = "") -> bool:
    """Kirim embed via Bot token."""
    try:
        embed_data = json.loads(embed_json_str)
    except Exception:
        print(f"[AUTOPOST] embed_json invalid JSON")
        return False

    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    headers = {
        "Authorization": f"Bot {BOT_TOKEN}",
        "Content-Type": "application/json"
    }

    def build_payload(d):
        embed = {}
        if d.get("title"):       embed["title"] = d["title"]
        if d.get("url"):         embed["url"]   = d["url"]
        if d.get("description"): embed["description"] = d["description"]
        if d.get("color"):
            try: embed["color"] = int(str(d["color"]).lstrip("#"), 16)
            except: pass
        if d.get("timestamp"):
            ts = d["timestamp"]
            embed["timestamp"] = ts + ":00" if len(ts) == 16 else ts
        a = d.get("author", {})
        if a.get("name"):
            au = {"name": a["name"]}
            if a.get("url"):      au["url"]      = a["url"]
            if a.get("icon_url"): au["icon_url"]  = a["icon_url"]
            embed["author"] = au
        if d.get("thumbnail"): embed["thumbnail"] = {"url": d["thumbnail"]}
        if d.get("image"):     embed["image"]     = {"url": d["image"]}
        f = d.get("footer", {})
        if f.get("text"):
            fo = {"text": f["text"]}
            if f.get("icon_url"): fo["icon_url"] = f["icon_url"]
            embed["footer"] = fo
        fields = [{"name": x["name"], "value": x["value"], "inline": bool(x.get("inline", False))}
                  for x in d.get("fields", []) if x.get("name") and x.get("value")]
        if fields: embed["fields"] = fields
        return embed

    payload = {"embeds": [build_payload(embed_data)]}
    if content_msg:
        payload["content"] = content_msg

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        if resp.status_code in (200, 201):
            return True
        print(f"[AUTOPOST] Gagal kirim embed ke {channel_id}: {resp.status_code} — {resp.text[:200]}")
        return False
    except Exception as e:
        print(f"[AUTOPOST] Exception embed: {e}")
        return False


def send_message(channel_id: str, message: str) -> bool:
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
    headers = {
        "Authorization": USER_TOKEN,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }
    payload = {"content": message}
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        if resp.status_code == 200:
            return True
        else:
            print(f"[AUTOPOST] Gagal kirim ke {channel_id}: {resp.status_code} — {resp.text[:200]}")
            return False
    except Exception as e:
        print(f"[AUTOPOST] Exception: {e}")
        return False


def run():
    if not USER_TOKEN:
        print("[AUTOPOST] ERROR: AUTOPOST_TOKEN belum diset di .env")
        sys.exit(1)

    ensure_table()
    print(f"[AUTOPOST] Berjalan. Cek task setiap {CHECK_INTERVAL} detik.")

    while True:
        try:
            now = datetime.datetime.now(datetime.timezone.utc)
            conn = get_conn()
            tasks = conn.execute(
                "SELECT * FROM autopost_tasks WHERE active=1"
            ).fetchall()
            conn.close()

            for task in tasks:
                last_sent = task["last_sent"]
                interval_minutes = task["interval_minutes"]

                if last_sent:
                    try:
                        last_dt = datetime.datetime.fromisoformat(last_sent)
                        if last_dt.tzinfo is None:
                            last_dt = last_dt.replace(tzinfo=datetime.timezone.utc)
                        elapsed = (now - last_dt).total_seconds() / 60
                        if elapsed < interval_minutes:
                            continue
                    except Exception:
                        pass

                print(f"[AUTOPOST] Mengirim task '{task["label"]}' ke channel {task["channel_id"]}...")
                embed_json = task["embed_json"] if "embed_json" in task.keys() else None
                content_msg = task["content"] if "content" in task.keys() else ""
                if embed_json and BOT_TOKEN:
                    ok = send_embed(task["channel_id"], embed_json, content_msg or "")
                else:
                    ok = send_message(task["channel_id"], task["message"])
                if ok:
                    now_str = now.isoformat()
                    conn2 = get_conn()
                    conn2.execute(
                        "UPDATE autopost_tasks SET last_sent=? WHERE id=?",
                        (now_str, task["id"])
                    )
                    conn2.commit()
                    conn2.close()
                    print(f"[AUTOPOST] Berhasil: '{task['label']}'")

        except Exception as e:
            print(f"[AUTOPOST] Error loop: {e}")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    run()
