# Official Midman Bot — Cellyn Store

Bot Discord untuk layanan middleman trade item game dan boost via login secara aman dan terpercaya.

---

## Fitur

**Midman Trade**
- Sistem tiket middleman trade dengan form otomatis
- Embed status tiket real-time (menunggu, berlangsung, selesai)
- Konfirmasi fee oleh admin sebelum trade dimulai
- Reminder otomatis setiap 6 jam jika tiket tidak ada aktivitas
- Nomor tiket tampil di nama channel, contoh: trade-0001-username
- Transcript HTML otomatis dikirim saat tiket ditutup
- Log transaksi lengkap ke channel log

**Boost Via Login (Vilog)**
- Sistem tiket khusus untuk layanan boost server via login akun Roblox
- Form otomatis berisi username, password, pilihan boost, dan metode bayar
- Data sensitif tampil dalam format spoiler
- Log transaksi lengkap setelah sesi selesai

**Sistem Bot**
- Error notification otomatis ke channel log
- Backup otomatis midman.db setiap 6 jam ke channel Discord
- Restore otomatis saat bot start apabila file database hilang
- Update bot dari Discord via !update tanpa perlu akses ke Redfinger

---

## Konfigurasi .env

    TOKEN=masukkan_token_bot_discord_disini
    GUILD_ID=id_server_discord
    MIDMAN_CHANNEL_ID=id_channel_tempat_embed_tombol_midman
    TICKET_CATEGORY_ID=id_kategori_tempat_channel_tiket_dibuat
    ADMIN_ROLE_ID=id_role_admin
    TRANSCRIPT_CHANNEL_ID=id_channel_transcript_midman
    LOG_CHANNEL_ID=id_channel_log_transaksi
    BACKUP_CHANNEL_ID=id_channel_backup_midman
    ERROR_LOG_CHANNEL_ID=id_channel_error_log
    VILOG_CHANNEL_ID=id_channel_embed_boost_via_login
    STORE_NAME=Nama Store Kamu

---

## List Command

    !open               Kirim ulang embed Midman Trade
    !vilog              Kirim ulang embed Boost Via Login
    !acc                Konfirmasi trade selesai, tutup tiket
    !batal [alasan]     Batalkan tiket midman
    !selesai [nominal]  Konfirmasi sesi vilog selesai
    !batalin [alasan]   Batalkan tiket vilog
    !update             Update bot dari GitHub dan restart otomatis
    !fee [nominal]      Hitung fee middleman
    !ping               Cek bot aktif dan latency
    !info               Lihat versi bot dan uptime

---

## Cara Install

    git clone https://github.com/EqualityDev/midman.git
    cd midman
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    nano .env
    bash start.sh

---

## Catatan Penting

- Jangan membagikan file .env ke siapapun.
- File midman.db tidak perlu di-push ke GitHub, bot backup otomatis via Discord.
- Pastikan bot punya permission: Send Messages, Read Message History, Manage Channels, Attach Files.
- Data sensitif member hanya tampil di channel tiket yang bersifat private.
