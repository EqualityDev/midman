# Midman Bot — Cellyn Store Community

Bot Discord untuk operasional toko digital. Menangani transaksi middleman trade, middleman jual beli, robux store, topup Mobile Legends & Free Fire (termasuk Weekly Diamond Pass), Cloud Phone, Discord Nitro, SC/Aset Game, AI customer service, selfroles, giveaway, welcome, dan admin panel berbasis web.

---

## Fitur

- **Midman Trade** — tiket perantara tukar item antar dua pihak
- **Midman Jual Beli** — tiket perantara jual beli, admin tahan uang pembeli sampai item konfirmasi oke
- **Robux Store** — katalog item Roblox per kategori dengan rate dinamis
- **ML & FF Topup** — topup diamond Mobile Legends, Free Fire, dan Weekly Diamond Pass (WDP)
- **Cloud Phone & Discord Nitro** — order Redfinger cloud phone dan Discord Nitro via tiket
- **SC TB / Aset Game** — jual beli item game, aset, dan kebutuhan quest/misi; admin input item + harga dinamis per tiket
- **Giveaway** — slash command giveaway dengan timer, auto-end, reroll, dan persistent setelah restart
- **Welcome** — welcome/leave/boost notif dengan GIF, auto-assign role Customer saat member join
- **Broadcast** — kirim pengumuman ke channel dengan modal preview, cooldown per admin
- **Auto React** — auto react emoji ke pesan di channel tertentu atau semua pesan admin
- **Server Stats** — voice channel nama otomatis update jumlah member
- **AI Customer Service** — bot AI menjawab pertanyaan member 24/7 via Groq API (rotasi hingga 5 API key)
- **Selfroles** — self-assignable roles via Discord
- **Admin Panel Web** — kelola produk ML/FF/WDP/Robux/Lainnya dan statistik transaksi via browser
- **Statistik Transaksi** — dashboard grafik 7 hari dan 30 hari, produk terlaris, jam tersibuk per layanan
- **Royal Customer** — auto-assign role setelah transaksi sukses di semua layanan
- **Auto-restart** — bot restart otomatis jika crash (max 5x)
- **Warning & Auto-close** — tiket tidak aktif 1 jam dapat peringatan, 2 jam ditutup otomatis
- **Notifikasi URL Admin** — URL Cloudflare Tunnel dikirim ke channel admin setiap bot online

---

## Persyaratan

- Python 3.12+
- Termux (Android) atau Linux
- Akun Discord + Bot Token
- Akun Groq (gratis) untuk fitur AI CS

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
| `ROBUX_CATALOG_CHANNEL_ID` | ID channel catalog robux |
| `ML_CATALOG_CHANNEL_ID` | ID channel catalog ML/FF |
| `SELFROLES_CHANNEL_ID` | ID channel selfroles |
| `AI_CHANNEL_ID` | ID channel AI customer service |
| `DANA_NUMBER` | Nomor DANA |
| `BCA_NUMBER` | Nomor BCA |
| `TESTIMONI_CHANNEL_ID` | ID channel testimoni |
| `CELLYN_TEAM_ROLE_ID` | ID role Cellyn Team (untuk nickname enforcer) |
| `GROQ_API_KEY_1` | API key Groq utama untuk fitur AI CS |
| `GROQ_API_KEY_2` | API key Groq cadangan ke-2 (opsional) |
| `GROQ_API_KEY_3` | API key Groq cadangan ke-3 (opsional) |
| `GROQ_API_KEY_4` | API key Groq cadangan ke-4 (opsional) |
| `GROQ_API_KEY_5` | API key Groq cadangan ke-5 (opsional) |

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
- **Lainnya** — tambah, edit, nonaktifkan/aktifkan, hapus produk Cloud Phone & Discord Nitro + tambah kategori baru
- **Statistik** — grafik transaksi 7 hari dan 30 hari, produk terlaris, jam tersibuk per layanan

Perubahan produk via web langsung berlaku ke bot tanpa restart.

---

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

### Cloud Phone & Discord Nitro
| Command | Fungsi |
|---|---|
| `!lainnya` | Kirim embed katalog Cloud Phone & Nitro |
| `!done` | Tutup tiket sukses |
| `!cancel [alasan]` | Batalkan tiket |

### SC TB / Aset Game
| Command | Fungsi |
|---|---|
| `!aset` | Kirim embed katalog SC/Aset Game |
| `!additem <nama> <qty> <harga>` | Tambah item ke tiket (admin) |
| `!delitem <nomor>` | Hapus item dari tiket (admin) |
| `!done` | Tutup tiket sukses |
| `!cancel [alasan]` | Batalkan tiket |

### Giveaway
| Command | Fungsi |
|---|---|
| `/giveaway` | Buat giveaway baru |
| `/giveaway_end` | Akhiri giveaway lebih awal |
| `/giveaway_reroll` | Reroll pemenang |
| `/giveaway_list` | Lihat giveaway aktif |

### Welcome & Tools
| Command | Fungsi |
|---|---|
| `/setwelcome` | Atur channel/GIF welcome, boost notif, atau nonaktifkan |
| `/broadcast` | Kirim pengumuman ke channel (modal preview) |
| `/setreact` | Set auto react di channel untuk pesan admin |
| `/setreactall` | Set auto react untuk semua user di channel |
| `/reactlist` | Lihat daftar channel auto react |
| `/setstatschannel` | Set voice channel untuk stats member |
| `/unsetstatschannel` | Nonaktifkan stats channel |

### Lainnya
| Command | Fungsi |
|---|---|
| `!selfroles` | Kirim embed self roles |
| `!cmd` | Tampilkan prefix guide (auto-hapus 10 detik) |
| `!update` | Pull GitHub + restart bot |
| `!ping` | Cek latency |
| `!info` | Info bot |

> Semua command prefix kecuali `!open` hanya bisa digunakan oleh role admin.

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

### Cloud Phone & Discord Nitro
1. Member klik kategori di channel lainnya
2. Pilih item dari dropdown
3. Tiket terbuka, member ketik **1/2/3** untuk pilih metode bayar
4. Bayar sesuai nominal, kirim bukti transfer
5. Admin proses, ketik `!done` untuk tutup tiket

### SC TB / Aset Game
1. Member klik tombol di channel lainnya
2. Tiket terbuka, member ketik **1/2/3** untuk pilih metode bayar
3. Member beritahu admin item yang dibutuhkan
4. Admin input item: `!additem <nama> <qty> <harga>`
5. Embed tiket otomatis update dengan daftar item + subtotal
6. Admin ketik `!done` setelah item terkirim

---

## Struktur File

```
midman/
├── main.py               # Entry point bot + notifikasi URL tunnel
├── admin.py              # Flask admin panel (port 5000)
├── seed.py               # Seed data produk default ke DB
├── start.sh              # Auto-start semua service
├── requirements.txt
├── .env.example
├── utils/
│   ├── config.py         # Semua env variable
│   ├── db.py             # init_db() + semua tabel SQLite + log_transaction()
│   ├── counter.py        # Auto-increment nomor tiket
│   ├── transcript.py     # Generate HTML transcript
│   ├── fee.py            # Kalkulator fee midman
│   ├── tickets.py        # CRUD tiket midman trade
│   └── robux_db.py       # CRUD tiket robux + bot_state
└── cogs/
    ├── midman.py         # Midman trade
    ├── jualbeli.py       # Midman jual beli
    ├── robux.py          # Robux store
    ├── ml.py             # Topup ML, FF & WDP
    ├── lainnya.py        # Cloud Phone & Discord Nitro
    ├── scaset.py         # SC TB / Aset Game
    ├── orders.py         # Shared !done & !cancel untuk lainnya + scaset
    ├── giveaway.py       # Giveaway slash commands
    ├── welcome.py        # Welcome/leave/boost notif + auto role Customer
    ├── broadcast.py      # Broadcast pengumuman dengan cooldown
    ├── auto_react.py     # Auto react emoji per channel
    ├── server_stats.py   # Voice channel stats member count
    ├── ai_chat.py        # AI customer service (Groq, rotasi 5 key)
    ├── selfroles.py      # Self-assignable roles
    ├── testimoni.py      # Auto-reply channel testimoni
    └── nickname_enforcer.py  # Auto-enforce suffix nama
```

---

## Database

SQLite (`midman.db`) tidak di-push ke GitHub. Di-generate otomatis saat `bash start.sh`.

**Tabel produk:**
- `ml_products` — produk Mobile Legends
- `wdp_products` — paket Weekly Diamond Pass
- `ff_products` — produk Free Fire
- `robux_products` — item Robux per kategori
- `lainnya_products` — produk Cloud Phone & Discord Nitro

**Tabel transaksi:**
- `tickets` — midman trade
- `jb_tickets` — midman jual beli
- `robux_tickets` — tiket robux
- `ml_tickets` — tiket ML & FF
- `lainnya_tickets` — tiket Cloud Phone & Nitro
- `scaset_tickets` — tiket SC/Aset Game
- `transaction_log` — log semua transaksi sukses (untuk statistik)
- `robux_rate` — rate Robux saat ini

**Tabel lainnya:**
- `giveaways` — giveaway aktif
- `auto_react` — channel auto react
- `bot_state` — state bot (embed message ID catalog, welcome settings, broadcast cooldown, dll)

---

## Cara Tambah Layanan Baru

1. Buat `cogs/namalayanan.py` — ikuti pola cog yang sudah ada (tiket, modal, auto-close, warning, persistent view, log, transcript, Royal Customer)
2. Tambah tabel di `utils/db.py`
3. Tambah data produk di `seed.py` (jika ada)
4. Tambah halaman di `admin.py` (jika ada produk yang perlu dikelola)
5. Daftarkan di `main.py` — `await bot.load_extension("cogs.namalayanan")`
6. Tambah prefix di `!cmd` di `cogs/midman.py`
7. Update system prompt AI di `cogs/ai_chat.py`
8. Update `README.md`

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
