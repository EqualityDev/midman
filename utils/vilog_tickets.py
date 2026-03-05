import json
import os

VILOG_FILE = "vilog_tickets.json"

def load_vilog_tickets():
    if not os.path.exists(VILOG_FILE):
        return {}
    with open(VILOG_FILE, "r") as f:
        raw = json.load(f)
    return {int(k): v for k, v in raw.items()}

def save_vilog_tickets(tickets):
    with open(VILOG_FILE, "w") as f:
        json.dump({str(k): v for k, v in tickets.items()}, f, indent=2)
