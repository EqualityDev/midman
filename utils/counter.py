import json

COUNTER_FILE = "ticket_counter.json"

def next_ticket_number():
    try:
        with open(COUNTER_FILE, "r") as f:
            data = json.load(f)
        data["count"] += 1
        with open(COUNTER_FILE, "w") as f:
            json.dump(data, f)
        return data["count"]
    except:
        with open(COUNTER_FILE, "w") as f:
            json.dump({"count": 1}, f)
        return 1
