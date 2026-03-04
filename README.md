# Official Midman Bot — Cellyn Store

Bot Discord untuk layanan middleman trade item game secara aman dan terpercaya.

---

## Daftar Isi

- [Fitur](#fitur)
- [Struktur Folder](#struktur-folder)
- [Persyaratan](#persyaratan)
- [Cara Install dan Setup](#cara-install-dan-setup)
- [Konfigurasi .env](#konfigurasi-env)
- [List Command](#list-command)
- [Cara Deploy ke Redfinger](#cara-deploy-ke-redfinger)
- [Catatan Penting](#catatan-penting)

---

## Fitur

- Sistem tiket middleman trade dengan form otomatis
- Embed status tiket real-time (menunggu, berlangsung, selesai)
- Konfirmasi fee oleh admin sebelum trade dimulai
- Peringatan embed fee otomatis saat setup trade
- Reminder otomatis setiap 6 jam jika tiket tidak ada aktivitas
- Nomor tiket tampil di nama channel, contoh: trade-0001-username
- Transcript HTML otomatis dikirim saat tiket ditutup
- Log transaksi lengkap ke channel log
- Error notification otomatis ke channel log jika terjadi error pada command
- Backup otomatis midman.db setiap 6 jam ke channel Discord
- Restore otomatis saat bot start apabila file database hilang
- Maksimal 1 tiket aktif per user, redirect otomatis jika mencoba buka tiket baru
- Data tersimpan di SQLite untuk keamanan dan ketahanan data

---

## Struktur Folder

```
midman_bot/
├── main.py                  # Entry point bot
├── .env                     # Konfigurasi token dan ID channel (jangan di-push ke GitHub)
├── midman.db                # Database SQLite (dibuat otomatis, jangan dihapus)
├── requirements.txt         # Daftar library Python yang dibutuhkan
├── cogs/
│   ├── midman.py            # Cog utama, berisi semua command dan logic bot
│   ├── modals.py            # Form modal untuk buka tiket dan setup trade
│   └── views.py             # Tombol interaktif dan fungsi builder embed
└── utils/
    ├── config.py            # Membaca konfigurasi dari file .env
    ├── backup.py            # Fungsi backup dan restore database
    ├── counter.py           # Penomoran tiket otomatis
    ├── db.py                # Inisialisasi dan koneksi database SQLite
    ├── fee.py               # Kalkulasi dan format nominal fee
    ├── tickets.py           # Simpan dan muat data tiket dari database
    └── transcript.py        # Generate file transcript HTML
```

---

## Persyaratan

- Python versi 3.10 atau lebih baru
- Git
- Akun Discord Developer dan bot token
- Server Discord dengan channel dan role yang sudah disiapkan

---

## Cara Install dan Setup

Langkah 1 - Clone repository

    git clone https://github.com/EqualityDev/midman.git
    cd midman_bot

Langkah 2 - Buat virtual environment

    python3 -m venv venv
    source venv/bin/activate

Setiap kali membuka terminal baru, aktifkan dulu sebelum jalankan bot:

    source venv/bin/activate

Langkah 3 - Install library

    pip install -r requirements.txt

Langkah 4 - Buat file .env

    nano .env

Isi konfigurasi yang sesuai, simpan dengan Ctrl+X lalu Y lalu Enter.

Langkah 5 - Jalankan bot

    python main.py

Jika berhasil, terminal menampilkan:

    [RESTORE] midman.db berhasil di-restore dari backup.
    [DB] Database diinisialisasi.
    Cog Midman siap.

Atau jika pertama kali dijalankan dan belum ada backup:

    [DB] Database diinisialisasi.
    Cog Midman siap.
    [BACKUP] Backup berhasil dikirim ke channel ...

Langkah 6 - Kirim embed ke channel Midman Trade

Ketik perintah berikut di Discord (butuh role admin):

    !open

---

## Konfigurasi .env

Isi file .env dengan format berikut:

    TOKEN=masukkan_token_bot_discord_disini
    GUILD_ID=id_server_discord
    MIDMAN_CHANNEL_ID=id_channel_tempat_embed_tombol_midman
    TICKET_CATEGORY_ID=id_kategori_tempat_channel_tiket_dibuat
    ADMIN_ROLE_ID=id_role_admin
    TRANSCRIPT_CHANNEL_ID=id_channel_transcript_midman
    LOG_CHANNEL_ID=id_channel_log_transaksi
    BACKUP_CHANNEL_ID=id_channel_backup_midman
    STORE_NAME=Nama Store Kamu

Penjelasan variabel:

    TOKEN                  Token bot dari Discord Developer Portal
    GUILD_ID               ID server Discord tempat bot digunakan
    MIDMAN_CHANNEL_ID      Channel tempat embed tombol Midman Trade dikirim
    TICKET_CATEGORY_ID     Kategori channel tempat tiket baru dibuat otomatis
    ADMIN_ROLE_ID          Role yang bisa menggunakan command admin
    TRANSCRIPT_CHANNEL_ID  Channel untuk file transcript tiket selesai
    LOG_CHANNEL_ID         Channel untuk log transaksi sukses dan error notification
    BACKUP_CHANNEL_ID      Channel untuk backup otomatis database
    STORE_NAME             Nama store yang tampil di semua embed bot

Cara mendapatkan ID di Discord:
1. Buka Pengaturan Discord
2. Pilih Tampilan, aktifkan Mode Pengembang
3. Klik kanan pada server, channel, atau role
4. Pilih Salin ID

---

## List Command

Command Admin (butuh role admin):

    !open               Kirim ulang embed Midman Trade, embed lama dihapus otomatis
    !acc                Konfirmasi trade selesai, kirim transcript dan log, tutup tiket
    !cancel             Batalkan tiket tanpa alasan
    !cancel [alasan]    Batalkan tiket dengan alasan tertentu
    !fee [nominal]      Hitung fee middleman dari nominal yang diberikan
    !ping               Cek apakah bot aktif dan lihat latency koneksi

Contoh penggunaan:

    !cancel Pihak 1 tidak responsif lebih dari 24 jam
    !fee 50000
    !fee 50k
    !ping

Tombol interaktif di Discord:

    Midman Trade            Semua user    Membuka form tiket baru
    Setup Trade (Admin)     Admin         Input data pihak 2, fee, dan link server
    Fee Diterima (Admin)    Admin         Konfirmasi bahwa fee sudah diterima

---

## Cara Deploy ke Redfinger

Redfinger adalah layanan cloud phone yang digunakan sebagai server production agar bot
dapat berjalan 24 jam penuh tanpa perlu menyalakan perangkat pribadi.

Langkah 1 - Akses Redfinger

Buka aplikasi Redfinger dan masuk ke cloud phone yang sudah disiapkan.

Langkah 2 - Install Termux

Download Termux dari browser di dalam Redfinger. Disarankan download dari F-Droid
bukan Play Store karena versi Play Store sudah tidak diupdate.

Langkah 3 - Setup awal Termux

    pkg update && pkg upgrade
    pkg install python git

Langkah 4 - Clone dan setup bot

    git clone https://github.com/EqualityDev/midman.git
    cd midman_bot
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt

Langkah 5 - Buat file .env

    nano .env

Isi konfigurasi yang sesuai, simpan dengan Ctrl+X lalu Y lalu Enter.

Langkah 6 - Jalankan bot dengan screen

Screen memungkinkan bot tetap berjalan meskipun Termux ditutup atau layar Redfinger mati.

Install screen:

    pkg install screen

Buat sesi screen baru dan jalankan bot:

    screen -S midmanbot
    source venv/bin/activate
    python main.py

Untuk keluar dari screen tanpa mematikan bot, tekan Ctrl+A lalu D.

Untuk kembali ke sesi bot:

    screen -r midmanbot

Langkah 7 - Update bot dari GitHub

    cd ~/midman_bot
    git pull origin main

Kemudian restart bot:

    screen -r midmanbot
    python main.py

---

## Catatan Penting

- Jangan membagikan atau mengupload file .env ke siapapun. File ini berisi token bot
  yang bersifat rahasia dan dapat disalahgunakan.

- File midman.db tidak perlu di-push ke GitHub karena sudah masuk .gitignore.
  Bot akan backup dan restore file ini secara otomatis lewat channel Discord.

- Pastikan bot memiliki permission yang cukup di semua channel yang dikonfigurasi,
  minimal: Send Messages, Read Message History, Manage Channels, dan Attach Files.

- Jika bot tidak merespons setelah update, cek log error di terminal Termux atau
  pantau channel log di Discord untuk error notification otomatis.

- Database midman.db yang hilang akan di-restore otomatis dari backup terakhir
  di channel Discord saat bot dinyalakan kembali.
