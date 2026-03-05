content = open('README.md').read()
old = """## Struktur Folder

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
    └── transcript.py        # Generate file transcript HTML"""

new = """## Struktur Folder
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
open('README.md', 'w').write(content.replace(old, new))
print("Done!")
