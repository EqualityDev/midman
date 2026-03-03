import json
import os
import datetime
import json as _json

COUNTER_FILE = "ticket_counter.json"

def next_ticket_number():
    try:
        with open(COUNTER_FILE, "r") as f:
            data = _json.load(f)
        data["count"] += 1
        with open(COUNTER_FILE, "w") as f:
            _json.dump(data, f)
        return data["count"]
    except:
        return 0

TICKETS_FILE = "tickets.json"


def save_tickets(active_tickets):
    data = {}
    for ch_id, t in active_tickets.items():
        data[str(ch_id)] = {
            "pihak1_id": t["pihak1"].id if t["pihak1"] else None,
            "pihak2_id": t["pihak2"].id if t["pihak2"] else None,
            "item_p1": t["item_p1"],
            "item_p2": t["item_p2"],
            "fee": t["fee"],
            "link_server": t["link_server"],
            "admin_id": t["admin"].id if t["admin"] else None,
            "fee_final": t.get("fee_final"),
            "embed_message_id": t.get("embed_message_id"),
            "opened_at": t["opened_at"].isoformat() if t["opened_at"] else None,
        }
    with open(TICKETS_FILE, "w") as f:
        json.dump(data, f)


async def load_tickets(guild, active_tickets):
    if not os.path.exists(TICKETS_FILE):
        return
    with open(TICKETS_FILE, "r") as f:
        data = json.load(f)
    for ch_id_str, t in data.items():
        ch_id = int(ch_id_str)
        try:
            p1 = await guild.fetch_member(t["pihak1_id"]) if t["pihak1_id"] else None
            p2 = await guild.fetch_member(t["pihak2_id"]) if t["pihak2_id"] else None
            adm = await guild.fetch_member(t["admin_id"]) if t["admin_id"] else None
        except Exception:
            continue
        active_tickets[ch_id] = {
            "pihak1": p1,
            "pihak2": p2,
            "item_p1": t["item_p1"],
            "item_p2": t["item_p2"],
            "fee": t["fee"],
            "link_server": t["link_server"],
            "admin": adm,
            "fee_final": t.get("fee_final"),
            "embed_message_id": t.get("embed_message_id"),
            "opened_at": datetime.datetime.fromisoformat(t["opened_at"]) if t["opened_at"] else None,
        }
