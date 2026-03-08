# Midman Bot — Cellyn Store Community

Bot Discord untuk operasional Cellyn Store Community. Menangani transaksi middleman, boost via login (vilog), robux store, topup Mobile Legends & Free Fire, selfroles, dan admin panel berbasis web.

---

## Fitur

- **Midman Trade** — sistem tiket middleman dengan konfirmasi fee dua pihak
- **Vilog** — boost Roblox via login dengan pilihan paket
- **Robux Store** — katalog item Roblox per kategori dengan rate dinamis
- **ML & FF Topup** — topup diamond Mobile Legends dan Free Fire (4 dropdown)
- **Selfroles** — self-assignable roles via Discord
- **Admin Panel Web** — kelola produk ML/FF/Robux/Vilog via browser dari mana saja
- **Auto-restart** — bot restart otomatis jika crash (max 5x)
- **Warning & Auto-close** — tiket tidak aktif 1 jam dapat peringatan, 2 jam ditutup otomatis
- **Notifikasi URL Admin** — URL Cloudflare Tunnel dikirim otomatis ke channel admin saat bot online

---

## Setup Awal (Perangkat Baru)

### 1. Clone repo
```bash
git clone https://github.com/EqualityDev/midman.git
cd midman
```

### 2. Buat virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Setup .env
```bash
cp .env.example .env
# Edit .env dengan nilai yang sesuai
```

### 5. Jalankan
```bash
bash start.sh
```

`start.sh` otomatis melakukan:
- Cek & pull update terbaru dari GitHub
- Init database SQLite
- Seed data produk default jika DB kosong
- Jalankan admin panel di port 5000
- Install cloudflared jika belum ada
- Jalankan Cloudflare Tunnel (URL dikirim ke Discord)
- Jalankan bot dengan auto-restart

---

## Environment Variables

Salin `.env.example` ke `.env` dan isi semua variabel:

| Variable | Keterangan |
|---|---|
| `TOKEN` | Token bot Discord |
| `GUILD_ID` | ID server Discord |
| `STORE_NAME` | Nama store (tampil di embed) |
| `ADMIN_ROLE_ID` | ID role admin |
| `TICKET_CATEGORY_ID` | ID kategori channel tiket |
| `LOG_CHANNEL_ID` | ID channel log transaksi |
| `TRANSCRIPT_CHANNEL_ID` | ID channel transcript tiket |
| `BACKUP_CHANNEL_ID` | ID channel backup |
| `ERROR_LOG_CHANNEL_ID` | ID channel log error + notifikasi admin |
| `MIDMAN_CHANNEL_ID` | ID channel midman trade |
| `VILOG_CHANNEL_ID` | ID channel vilog |
| `ROBUX_CATALOG_CHANNEL_ID` | ID channel catalog robux |
| `ML_CATALOG_CHANNEL_ID` | ID channel catalog ML/FF |
| `SELFROLES_CHANNEL_ID` | ID channel selfroles |
| `DANA_NUMBER` | Nomor DANA |
| `BCA_NUMBER` | Nomor BCA |

### Opsional (Admin Panel)
| Variable | Default | Keterangan |
|---|---|---|
| `ADMIN_PASSWORD` | `cellyn123` | Password login admin panel |
| `ADMIN_SECRET` | *(auto)* | Secret key Flask session |
| `ADMIN_PORT` | `5000` | Port admin panel |

---

## Admin Panel

Admin panel otomatis jalan saat `bash start.sh`. URL Cloudflare Tunnel dikirim ke `ERROR_LOG_CHANNEL` via embed setiap kali bot online.

**Fitur:**
- **Dashboard** — ringkasan produk aktif + update rate Robux
- **ML** — tambah, edit, hapus produk Mobile Legends
- **FF** — tambah, edit, hapus produk Free Fire
- **Robux** — tambah, edit, nonaktifkan/aktifkan, hapus item + tambah kategori baru
- **Vilog** — tambah, edit, nonaktifkan/aktifkan, hapus paket boost

Perubahan produk via web langsung berlaku ke bot tanpa restart.

---

## Command Reference

| Command | Fungsi | Akses |
|---|---|---|
| `!open` | Buka catalog midman trade | Public |
| `!acc` | Tutup tiket midman | Admin |
| `!batal [alasan]` | Batalkan tiket midman | Admin |
| `!fee [nominal]` | Hitung fee | Admin |
| `!vilog` | Refresh embed vilog | Admin |
| `!selesai [nominal]` | Tutup tiket vilog | Admin |
| `!batalin [alasan]` | Batalkan tiket vilog | Admin |
| `!catalog` | Buka catalog robux | Admin |
| `!rate [angka]` | Set rate robux | Admin |
| `!gift` | Tutup tiket robux | Admin |
| `!tolak [alasan]` | Batalkan tiket robux | Admin |
| `!mlcatalog` | Buka catalog ML+FF topup | Admin |
| `!mlselesai` | Tutup tiket ML/FF | Admin |
| `!mlbatal [alasan]` | Batalkan tiket ML/FF | Admin |
| `!selfroles` | Kirim embed self roles | Admin |
| `!cmd` | Tampilkan prefix guide | Admin |
| `!update` | Pull GitHub + restart | Admin |
| `!ping` | Cek latency | Admin |
| `!info` | Info bot | Admin |

---

## Struktur File

```
midman_bot/
├── main.py               # Entry point bot + notifikasi URL tunnel
├── admin.py              # Flask admin panel
├── seed.py               # Seed data produk default ke DB
├── start.sh              # Auto-start: seed + admin + cloudflared + bot
├── requirements.txt
├── .env / .env.example
├── utils/
│   ├── config.py
│   ├── db.py             # init_db() + semua tabel SQLite
│   ├── counter.py
│   ├── transcript.py
│   ├── fee.py
│   ├── tickets.py
│   ├── vilog_db.py
│   └── robux_db.py
└── cogs/
    ├── midman.py
    ├── vilog.py
    ├── robux.py
    ├── ml.py
    ├── selfroles.py
    ├── views.py
    └── modals.py
```

---

## Database

SQLite (`midman.db`) tidak di-push ke GitHub. Di-generate otomatis saat `bash start.sh`.

Tabel produk (di-seed dari `seed.py`):
- `ml_products` — produk Mobile Legends
- `ff_products` — produk Free Fire
- `robux_products` — item Robux per kategori
- `vilog_boosts` — paket boost vilog

Tabel transaksi:
- `tickets` — midman trade
- `vilog_tickets` — tiket vilog
- `robux_tickets` — tiket robux
- `ml_tickets` — tiket ML & FF
- `robux_rate` — rate Robux saat ini
- `bot_state` — state bot (embed message ID, dll)

---

## Workflow Development

```
HP (dev/test) → GitHub → RF via !update
```

Semua perubahan kode dilakukan di HP, push ke GitHub, lalu `!update` di Discord untuk deploy ke RF.
