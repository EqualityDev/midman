import sqlite3

DB_FILE = "midman.db"

def get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            channel_id        INTEGER PRIMARY KEY,
            pihak1_id         INTEGER,
            pihak2_id         INTEGER,
            item_p1           TEXT,
            item_p2           TEXT,
            fee_final         INTEGER,
            fee_paid          INTEGER DEFAULT 0,
            link_server       TEXT,
            admin_id          INTEGER,
            embed_message_id  INTEGER,
            ticket_number     INTEGER,
            opened_at         TEXT,
            fee_warning_id    INTEGER,
            verified_by_id    INTEGER
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS counter (
            id    INTEGER PRIMARY KEY DEFAULT 1,
            count INTEGER DEFAULT 0
        )
    ''')
    c.execute('INSERT OR IGNORE INTO counter (id, count) VALUES (1, 0)')
    conn.commit()
    conn.close()
    print("[DB] Database diinisialisasi.")
