# Midman Bot — Cellyn Store Community

Bot Discord untuk layanan toko digital meliputi middleman trade, boost via login, topup Robux, dan topup Mobile Legends secara aman, amanah, dan transparan.

---

## Fitur

**Midman Trade**
- Sistem tiket middleman trade dengan form otomatis
- Embed status tiket real-time
- Konfirmasi fee oleh admin sebelum trade dimulai
- Reminder otomatis jika tiket tidak ada aktivitas
- Nomor tiket tampil di nama channel (contoh: trade-0001-username)
- Transcript HTML otomatis dikirim saat tiket ditutup
- Log transaksi embed ke channel log

**Boost Via Login (Vilog)**
- Sistem tiket khusus untuk boost server via login akun Roblox
- Form otomatis berisi username, password, pilihan boost, dan metode bayar
- Data sensitif tampil dalam format spoiler
- Harga otomatis mengikuti rate Robux yang diset admin
- Log transaksi embed setelah sesi selesai

**Robux Store**
- Catalog item Robux dengan kategori (Gamepass, Crate, Boost, Limited)
- Rate Robux dinamis — semua harga auto-update saat admin set rate
- Sistem tiket dengan flow pembayaran (QRIS/DANA/BCA)
- Rate dikunci setelah member klik PAID agar tagihan tidak berubah
- Auto-close tiket setelah 2 jam tidak ada aktivitas
- Proteksi spam — member tidak bisa pilih metode bayar lebih dari sekali
- Log transaksi embed ke channel log

**Topup Mobile Legends**
- Catalog 33 pilihan diamond via dropdown (dibagi Kecil & Besar)
- Harga tercantum langsung di setiap opsi dropdown
- Sistem tiket dengan form ID ML dan Server ID
- Metode pembayaran QRIS
- Log transaksi embed ke channel log

**Self Roles**
- Member bisa ambil role game sendiri via tombol toggle
- Role tersedia: Fish It, Violens District, Mobile Legends, INFO PT PT, Giveaway, Roblox

**Sistem Bot**
- Semua tombol embed tetap aktif setelah bot restart (persistent view)
- Tiket tersimpan di SQLite — aman dari restart bot
- Update bot dari Discord via `!update` tanpa perlu akses server
- `!cmd` — prefix guide untuk admin (hilang otomatis 10 detik)
- Error notification otomatis ke channel log
- Backup otomatis database setiap 6 jam ke channel Discord

---

## Konfigurasi .env

Salin `.env.example` menjadi `.env` lalu isi semua value:

```
TOKEN=                     # Token bot Discord
GUILD_ID=                  # ID server Discord
STORE_NAME=                # Nama toko (tampil di embed & log)
ADMIN_ROLE_ID=             # ID role admin
TICKET_CATEGORY_ID=        # ID kategori tempat tiket dibuat
LOG_CHANNEL_ID=            # ID channel log transaksi
TRANSCRIPT_CHANNEL_ID=     # ID channel transcript tiket
BACKUP_CHANNEL_ID=         # ID channel backup
ERROR_LOG_CHANNEL_ID=      # ID channel log error
MIDMAN_CHANNEL_ID=         # ID channel catalog midman trade
VILOG_CHANNEL_ID=          # ID channel embed vilog
ROBUX_CATALOG_CHANNEL_ID=  # ID channel catalog robux store
ML_CATALOG_CHANNEL_ID=     # ID channel catalog topup ML
SELFROLES_CHANNEL_ID=      # ID channel self roles
DANA_NUMBER=               # Nomor DANA
BCA_NUMBER=                # Nomor rekening BCA
```

---

## List Command

**Midman Trade**
```
!open               Kirim embed catalog midman trade
!acc                Konfirmasi trade selesai, tutup tiket
!batal [alasan]     Batalkan tiket midman
!fee [nominal]      Hitung fee middleman
```

**Boost Via Login**
```
!vilog              Kirim embed pricelist boost
!selesai [nominal]  Konfirmasi sesi vilog selesai
!batalin [alasan]   Batalkan tiket vilog
```

**Robux Store**
```
!catalog            Kirim embed catalog robux
!rate [angka]       Set rate Robux (contoh: !rate 90)
!gift               Konfirmasi gift item selesai
!tolak [alasan]     Batalkan tiket robux
```

**Topup Mobile Legends**
```
!mlcatalog          Kirim embed catalog topup ML
!mlselesai          Konfirmasi topup selesai
!mlbatal [alasan]   Batalkan tiket ML
```

**Lainnya**
```
!selfroles          Kirim embed self roles
!cmd                Tampilkan semua prefix (hilang 10 detik)
!update             Update bot dari GitHub dan restart otomatis
!ping               Cek bot aktif dan latency
!info               Lihat versi bot dan uptime
```

---

## Cara Install

```bash
git clone https://github.com/EqualityDev/midman.git
cd midman
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env
bash start.sh
```

---
