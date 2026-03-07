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
    c.execute('''
        CREATE TABLE IF NOT EXISTS vilog_tickets (
            channel_id      INTEGER PRIMARY KEY,
            user_id         INTEGER,
            username_roblox TEXT,
            password        TEXT,
            boost_nama      TEXT,
            boost_robux     INTEGER,
            metode          TEXT,
            nominal         INTEGER,
            admin_id        INTEGER,
            opened_at       TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS robux_rate (
            id    INTEGER PRIMARY KEY DEFAULT 1,
            rate  INTEGER DEFAULT 0
        )
    ''')
    c.execute('INSERT OR IGNORE INTO robux_rate (id, rate) VALUES (1, 0)')
    c.execute('''
        CREATE TABLE IF NOT EXISTS robux_tickets (
            channel_id  INTEGER PRIMARY KEY,
            user_id     INTEGER,
            item_id     INTEGER,
            item_name   TEXT,
            robux       INTEGER,
            rate        INTEGER,
            total       INTEGER,
            payment_method TEXT,
            payment_embed_msg_id INTEGER,
            paid        INTEGER DEFAULT 0,
            admin_id    INTEGER,
            opened_at   TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS bot_state (
            key   TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS ml_tickets (
            channel_id  INTEGER PRIMARY KEY,
            user_id     INTEGER,
            id_ml       TEXT,
            server_id   TEXT,
            dm          INTEGER,
            harga       INTEGER,
            opened_at   TEXT,
            game        TEXT DEFAULT 'ML'
        )
    ''')
    try:
        c.execute("ALTER TABLE ml_tickets ADD COLUMN game TEXT DEFAULT 'ML'")
    except Exception:
        pass
    conn.commit()
    conn.close()
    print("[DB] Database diinisialisasi.")
