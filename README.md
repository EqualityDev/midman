# Midman Bot — Cellyn Store Community

Bot Discord untuk operasional toko digital. Menangani transaksi middleman trade, middleman jual beli, boost via login (vilog), robux store, topup Mobile Legends & Free Fire (termasuk Weekly Diamond Pass), AI customer service, selfroles, autopost, dan admin panel berbasis web.

---

## Fitur

- **Midman Trade** — tiket perantara tukar item antar dua pihak
- **Midman Jual Beli** — tiket perantara jual beli, admin tahan uang pembeli sampai item konfirmasi oke
- **Vilog** — boost server Roblox via login dengan pilihan paket
- **Robux Store** — katalog item Roblox per kategori dengan rate dinamis
- **ML & FF Topup** — topup diamond Mobile Legends, Free Fire, dan Weekly Diamond Pass (WDP)
- **AI Customer Service** — bot AI menjawab pertanyaan member 24/7 via Groq API (rotasi hingga 5 API key)
- **Selfroles** — self-assignable roles via Discord
- **Autopost** — kirim pesan promosi/pengumuman ke channel manapun secara otomatis berdasarkan interval
- **Admin Panel Web** — kelola produk ML/FF/WDP/Robux/Vilog dan task autopost via browser dari mana saja
- **Auto-restart** — bot restart otomatis jika crash (max 5x)
- **Warning & Auto-close** — tiket tidak aktif 1 jam dapat peringatan, 2 jam ditutup otomatis
- **Notifikasi URL Admin** — URL Cloudflare Tunnel dikirim ke channel admin setiap bot online

---

## Persyaratan

- Python 3.12+
- Termux (Android) atau Linux
- Akun Discord + Bot Token
- Akun Groq (gratis) untuk fitur AI CS
- User Token Discord untuk fitur Autopost

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
nano .env  # isi semua variabel
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
- Jalankan autopost script di background
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
| `ERROR_LOG_CHANNEL_ID` | ID channel log error + notifikasi admin panel |
| `MIDMAN_CHANNEL_ID` | ID channel midman |
| `VILOG_CHANNEL_ID` | ID channel vilog |
| `ROBUX_CATALOG_CHANNEL_ID` | ID channel catalog robux |
| `ML_CATALOG_CHANNEL_ID` | ID channel catalog ML/FF |
| `SELFROLES_CHANNEL_ID` | ID channel selfroles |
| `AI_CHANNEL_ID` | ID channel AI customer service |
| `DANA_NUMBER` | Nomor DANA |
| `BCA_NUMBER` | Nomor BCA |
| `GROQ_API_KEY_1` | API key Groq utama untuk fitur AI CS |
| `GROQ_API_KEY_2` | API key Groq cadangan ke-2 (opsional) |
| `GROQ_API_KEY_3` | API key Groq cadangan ke-3 (opsional) |
| `GROQ_API_KEY_4` | API key Groq cadangan ke-4 (opsional) |
| `GROQ_API_KEY_5` | API key Groq cadangan ke-5 (opsional) |
| `AUTOPOST_TOKEN` | User token Discord untuk fitur autopost |

### Opsional (Admin Panel)
| Variable | Default | Keterangan |
|---|---|---|
| `ADMIN_PASSWORD` | `cellyn123` | Password login admin panel |
| `ADMIN_SECRET` | *(auto)* | Secret key Flask session |
| `ADMIN_PORT` | `5000` | Port admin panel |

---

## Admin Panel

Admin panel otomatis jalan saat `bash start.sh`. URL Cloudflare Tunnel dikirim ke `ERROR_LOG_CHANNEL` via embed setiap kali bot online.

Akses: buka URL yang dikirim bot di channel error log → login dengan `ADMIN_PASSWORD`

**Fitur:**
- **Dashboard** — ringkasan produk aktif + update rate Robux
- **ML** — tambah, edit, hapus produk Mobile Legends + Weekly Diamond Pass (WDP)
- **FF** — tambah, edit, hapus produk Free Fire
- **Robux** — tambah, edit, nonaktifkan/aktifkan, hapus item + tambah kategori baru
- **Vilog** — tambah, edit, nonaktifkan/aktifkan, hapus paket boost
- **Autopost** — tambah, edit, hapus, aktifkan/nonaktifkan task autopost

Perubahan produk via web langsung berlaku ke bot tanpa restart.

---

## Autopost

Kirim pesan promosi atau pengumuman ke channel Discord manapun secara otomatis berdasarkan interval waktu.

**Cara pakai:**
1. Buka admin panel → menu **Autopost**
2. Klik **+ Tambah Task**
3. Isi label, channel ID tujuan, isi pesan, dan interval (dalam menit)
4. Simpan — pesan akan terkirim otomatis sesuai interval

> Autopost menggunakan user token (`AUTOPOST_TOKEN`), bukan bot token. Bisa mengirim ke channel di server manapun selama akun tersebut adalah member dan punya izin kirim pesan di channel tersebut.

---

## Command Reference

### Midman Trade
| Command | Fungsi |
|---|---|
| `!open` | Kirim embed catalog midman |
| `!acc` | Konfirmasi trade selesai |
| `!batal [alasan]` | Batalkan tiket midman |
| `!fee [nominal]` | Hitung fee midman |

### Midman Jual Beli
| Command | Fungsi |
|---|---|
| `!jbuang` | Konfirmasi uang dari pembeli diterima |
| `!jbselesai` | Release dana ke penjual (setelah pembeli konfirmasi item) |
| `!jbbatal [alasan]` | Batalkan tiket jual beli |

### Vilog
| Command | Fungsi |
|---|---|
| `!vilog` | Refresh embed pricelist vilog |
| `!selesai [nominal]` | Tutup tiket vilog |
| `!batalin [alasan]` | Batalkan tiket vilog |

### Robux Store
| Command | Fungsi |
|---|---|
| `!catalog` | Kirim embed catalog robux |
| `!rate [angka]` | Set rate Robux |
| `!gift` | Konfirmasi gift item selesai |
| `!tolak [alasan]` | Batalkan tiket robux |

### ML & FF Topup
| Command | Fungsi |
|---|---|
| `!mlcatalog` | Kirim embed catalog ML/FF/WDP |
| `!mlselesai` | Konfirmasi topup selesai |
| `!mlbatal [alasan]` | Batalkan tiket ML/FF |

### Lainnya
| Command | Fungsi |
|---|---|
| `!selfroles` | Kirim embed self roles |
| `!cmd` | Tampilkan prefix guide (auto-hapus 10 detik) |
| `!update` | Pull GitHub + restart bot |
| `!ping` | Cek latency |
| `!info` | Info bot |

> Semua command kecuali `!open` hanya bisa digunakan oleh role admin.

---

## Alur Tiket

### Midman Trade
1. Member klik tombol **⚔️ Midman Trade** di channel midman
2. Isi form: item pihak 1 + item yang diminta
3. Admin bergabung, setup pihak 2 + fee
4. Fee dibayar, admin konfirmasi → trade berlangsung
5. Admin ketik `!acc` untuk tutup tiket

### Midman Jual Beli
1. Penjual klik tombol **🛒 Midman Jual Beli** di channel midman
2. Isi form: deskripsi item + harga
3. Admin setup: tambah pembeli, set fee + penanggung fee
4. Pembeli transfer ke admin sesuai nominal
5. Admin ketik `!jbuang` → konfirmasi uang diterima, serahkan item ke pembeli
6. Pembeli klik **✅ Item Diterima & Sesuai**
7. Admin ketik `!jbselesai` → dana direlease ke penjual, tiket ditutup

### Vilog
1. Member klik tombol **BELI** di channel vilog
2. Isi form: username Roblox, password, pilihan boost, metode bayar
3. Transfer ke admin, kirim bukti bayar
4. Admin proses boost, ketik `!selesai [nominal]`
5. Member **wajib ganti password** setelah selesai

### Robux Store
1. Member klik kategori di channel catalog robux
2. Pilih item dari dropdown
3. Transfer sesuai nominal + kirim bukti bayar
4. Admin verifikasi, gift item via Roblox
5. Admin ketik `!gift` untuk tutup tiket

### ML & FF Topup
1. Member pilih diamond / WDP di channel catalog ML
2. Isi form: ID ML + Server ID (untuk ML) atau Player ID (untuk FF)
3. Bayar via QRIS
4. Admin proses topup, ketik `!mlselesai`

---

## Struktur File

```
midman/
├── main.py               # Entry point bot + notifikasi URL tunnel
├── admin.py              # Flask admin panel (port 5000)
├── autopost.py           # Script autopost background (pakai user token)
├── seed.py               # Seed data produk default ke DB
├── start.sh              # Auto-start semua service
├── requirements.txt
├── .env.example
├── utils/
│   ├── config.py         # Semua env variable
│   ├── db.py             # init_db() + semua tabel SQLite
│   ├── counter.py        # Auto-increment nomor tiket
│   ├── transcript.py     # Generate HTML transcript
│   ├── fee.py            # Kalkulator fee midman
│   ├── tickets.py        # CRUD tiket midman trade
│   ├── vilog_db.py       # CRUD tiket vilog
│   └── robux_db.py       # CRUD tiket robux + bot_state
└── cogs/
    ├── midman.py         # Midman trade
    ├── jualbeli.py       # Midman jual beli
    ├── vilog.py          # Boost via login
    ├── robux.py          # Robux store
    ├── ml.py             # Topup ML, FF & WDP
    ├── ai_chat.py        # AI customer service (Groq, rotasi 5 key)
    ├── selfroles.py      # Self-assignable roles
    ├── testimoni.py      # Auto-reply channel testimoni
    ├── nickname_enforcer.py  # Auto-enforce suffix nama
    ├── views.py          # Persistent views & embeds
    └── modals.py         # Modal forms
```

---

## Database

SQLite (`midman.db`) tidak di-push ke GitHub. Di-generate otomatis saat `bash start.sh`.

**Tabel produk** (di-seed dari `seed.py`):
- `ml_products` — produk Mobile Legends
- `wdp_products` — paket Weekly Diamond Pass
- `ff_products` — produk Free Fire
- `robux_products` — item Robux per kategori
- `vilog_boosts` — paket boost vilog

**Tabel transaksi:**
- `tickets` — midman trade
- `jb_tickets` — midman jual beli
- `vilog_tickets` — tiket vilog
- `robux_tickets` — tiket robux
- `ml_tickets` — tiket ML & FF
- `robux_rate` — rate Robux saat ini
- `bot_state` — state bot (embed message ID, dll)

**Tabel lainnya:**
- `autopost_tasks` — task autopost (label, channel ID, pesan, interval, status)

---

## Cara Tambah Layanan Baru

1. Buat `cogs/namalayanan.py` — ikuti pola cog yang sudah ada (tiket, modal, auto-close, warning, persistent view, log, transcript)
2. Tambah tabel di `utils/db.py`
3. Tambah data produk di `seed.py` (jika ada)
4. Tambah halaman di `admin.py` (jika ada produk yang perlu dikelola)
5. Daftarkan di `main.py` — `await bot.load_extension("cogs.namalayanan")`
6. Tambah prefix di `!cmd` di `cogs/midman.py`
7. Update system prompt AI di `cogs/ai_chat.py`

---

## Cara Mendapatkan Groq API Key

1. Daftar di https://console.groq.com
2. Buat API key baru
3. Isi di `.env` → `GROQ_API_KEY_1=your_key_here`

Limit gratis: 30 request/menit, 14.400 request/hari, 500.000 token/hari.
Untuk menghindari rate limit, daftarkan hingga 5 akun Groq dan isi semua `GROQ_API_KEY_1` sampai `GROQ_API_KEY_5`.

---

## Workflow Development

```
HP (dev) → GitHub → Production via !update di Discord
```

Semua perubahan kode dilakukan di HP, push ke GitHub, lalu `!update` di Discord untuk deploy ke production.
