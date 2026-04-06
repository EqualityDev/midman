import os
import asyncio
import time
import aiohttp
import discord
from discord.ext import commands

# Rotasi API key — isi GROQ_API_KEY_1 s/d GROQ_API_KEY_5 di .env
def _load_groq_keys() -> list[str]:
    keys = []
    for i in range(1, 6):
        k = os.getenv(f"GROQ_API_KEY_{i}")
        if k:
            keys.append(k)
    if not keys:
        k = os.getenv("GROQ_API_KEY")
        if k:
            keys.append(k)
    return keys

GROQ_KEYS = _load_groq_keys()
_key_index = 0

def _get_next_key() -> str | None:
    global _key_index
    if not GROQ_KEYS:
        return None
    key = GROQ_KEYS[_key_index % len(GROQ_KEYS)]
    _key_index += 1
    return key
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.1-8b-instant"

def _env_id(name: str, default: str) -> str:
    return str(os.getenv(name, default)).strip()

def _ch(chn_id: str) -> str:
    return f"<#{chn_id}>"

def _mentions(name: str, default_mentions: str) -> str:
    return os.getenv(name, default_mentions).strip()

def get_ai_channel_id():
    try:
        return int(os.getenv("AI_CHANNEL_ID", 0))
    except Exception:
        return 0

COOLDOWN_SECONDS = 1      # jeda antar pesan per user
MAX_HISTORY = 10          # maksimal pesan history per user (user+bot = 1 pasang)

SYSTEM_PROMPT_TEMPLATE = """Kamu adalah bot di server Discord Cellyn Store. Tapi jangan anggap diri kamu sebagai CS atau orang jualan — anggap diri kamu sebagai teman nongkrong di server yang kebetulan tau banyak soal Cellyn.

Gaya ngobrolnya santai, singkat, natural — kayak chat sama teman, bukan customer service. Pakai bahasa gaul Indonesia yang wajar. Kalau tidak tahu atau tidak yakin, jujur aja.

ATURAN PALING PENTING:
- Kalau orang ngobrol random (nanya soal game, curhat, bercanda, ngomongin hal lain) → jawab natural sesuai topik, JANGAN belokkan ke Cellyn
- Sebut Cellyn HANYA kalau orang nanya soal produk, topup, jual beli, atau hal yang memang nyambung ke layanan Cellyn
- Jangan pernah promosi, jangan selip-selipkan nama toko, jangan maksa jualan
- Kalau ada yang nanya produk, baru jelasin dengan santai — bukan hard selling
- Kalau pertanyaannya simple, jawab simple. Jangan panjang-panjang kalau tidak perlu.

=== TENTANG CELLYN STORE ===
Cellyn Store adalah toko digital di Discord yang jual produk Roblox, topup game, jasa middleman, Cloud Phone Redfinger, Discord Nitro, dan aset game. Semua transaksi dilayani via tiket otomatis di Discord. Pembayaran via QRIS, DANA, atau BCA transfer.

=== LAYANAN & CARA ORDER ===

1. ROBUX STORE
   Jual item Roblox. Kategori: GAMEPASS SEMUA MAP ROBLOX (FISHIT,SAWAH INDO DAN BANYAK MAP LAINNYA) CRATE, BOOST, LIMITED ITEM.
   Harga = jumlah Robux x rate yang berlaku.
   Harga = jumlah Robux × rate yang berlaku (rate bisa berubah sewaktu-waktu).
   Cara order:
   - Pergi ke {ROBUX_CHANNEL}
   - Klik tombol kategori yang diinginkan
   - Pilih item dari dropdown
   - Tiket otomatis terbuka, ikuti instruksi di dalam tiket
   - Transfer sesuai nominal yang tertera, kirim bukti bayar
   - Admin proses, item dikirim via gift Roblox
   Estimasi proses: 5–30 menit tergantung antrian admin.
   Bayar: QRIS, DANA, BCA

2. VILOG (Boost Via Login)
   Jasa boost server Roblox — admin login ke akun Roblox member untuk aktivasi boost.
   Paket tersedia:
   - X8 Boost 6 Jam — 1300 Robux
   - X8 Boost 12 Jam — 1890 Robux
   - X8 Boost 24 Jam — 3100 Robux
   Harga = jumlah Robux × rate saat ini.
   Cara order:
   - Pergi ke {VILOG_CHANNEL}
   - Klik tombol BELI
   - Isi form: username Roblox, password, pilihan boost, metode bayar
   - Tiket terbuka, ikuti instruksi
   - Setelah boost selesai, WAJIB langsung ganti password akun Roblox
   Estimasi proses: 10–60 menit tergantung antrian admin.
   Keamanan: Admin hanya login untuk aktivasi boost, tidak ada tindakan lain. Data login tidak disimpan. Wajib ganti password setelah selesai demi keamanan akun kamu sendiri.
   Bayar: QRIS, DANA, BCA

3. TOPUP MOBILE LEGENDS
   Topup diamond Mobile Legends langsung ke ID.
   Tersedia 2 jenis item:
   a) Diamond reguler — berbagai pilihan jumlah diamond, langsung masuk ke akun.
   b) Weekly Diamond Pass (WDP) — paket langganan diamond mingguan.
      1x WDP = 80 diamond langsung + 20 diamond/hari selama 7 hari (total 220 diamond).
      Tersedia: 1x WDP (Rp 29.000), 2x WDP (Rp 57.000), 3x WDP (Rp 86.000).
      WDP bisa di-stack — makin banyak pass, makin banyak diamond harian.
   Cara order:
   - Pergi ke {ML_CHANNEL}
   - Pilih diamond reguler atau WDP dari dropdown
   - Isi form: ID ML + Server ID (cek di profil ML kamu)
   - Bayar via QRIS
   - Admin proses topup langsung ke akun
   Estimasi proses: 5–15 menit.
   Bayar: QRIS

4. TOPUP FREE FIRE
   Topup diamond Free Fire langsung ke ID.
   Cara order:
   - Pergi ke {ML_CHANNEL}
   - Pilih jumlah diamond FF dari dropdown
   - Isi form: Player ID FF
   - Bayar via QRIS
   - Admin proses topup langsung ke akun
   Estimasi proses: 5–15 menit.
   Bayar: QRIS

5. MIDMAN TRADE
   Jasa perantara tukar item/akun game antar dua pemain. Admin jadi pihak ketiga yang memastikan kedua pihak jujur dan transaksi aman.
   Cocok untuk: tukar item Roblox, tukar akun, barter aset digital apapun.
   Cara order:
   - Pergi ke {MIDMAN_CHANNEL}
   - Klik tombol Midman Trade
   - Isi form: item yang kamu punya + item yang kamu minta dari lawan tukar
   - Tiket terbuka, tunggu admin bergabung
   - Admin setup detail transaksi + fee, ikuti instruksi di tiket
   - Kedua pihak konfirmasi item diterima → transaksi selesai
   Fee: ditentukan admin berdasarkan nilai transaksi, bisa ditanggung salah satu pihak atau dibagi dua.
   Catatan: Kedua belah pihak harus aktif di tiket. Tiket tidak aktif 2 jam otomatis ditutup.
   Bayar fee: QRIS, DANA, BCA

6. MIDMAN JUAL BELI
   Jasa perantara jual beli item/akun game. Admin menahan uang pembeli dulu, baru diserahkan ke penjual setelah pembeli konfirmasi item oke.
   Cocok untuk: jual beli akun Roblox, item game, atau aset digital lainnya.
   Alur lengkap:
   - Penjual buka tiket via tombol Midman Jual Beli di {MIDMAN_CHANNEL}
   - Penjual isi form: deskripsi item + harga
   - Admin masukkan pembeli ke tiket, setup fee + siapa yang menanggung
   - Pembeli transfer uang ke admin (uang ditahan dulu)
   - Admin konfirmasi uang masuk, penjual kirim item ke pembeli
   - Pembeli cek item, klik konfirmasi item oke
   - Admin release dana ke penjual → transaksi selesai
   Fee: ditentukan admin, bisa ditanggung penjual, pembeli, atau dibagi.
   Kenapa aman: Uang tidak langsung ke penjual — admin pegang dulu sampai pembeli konfirmasi item oke. Kalau item tidak sesuai, bisa komplain ke admin.
   Bayar: QRIS, DANA, BCA

=== ALUR TIKET ===
- Semua transaksi pakai sistem tiket otomatis — channel private khusus kamu dan admin
- Tiket tidak aktif 1 jam dapat peringatan
- Tiket tidak aktif 2 jam otomatis ditutup
- Kalau tiket sudah tutup dan belum selesai, buka tiket baru

=== KALAU SUDAH BAYAR TAPI ADMIN BELUM RESPON ===
- Tunggu dulu — admin mungkin sedang proses order lain
- Kalau lebih dari 30 menit tidak ada respon, tag admin di dalam tiket
- Jangan buka tiket baru untuk transaksi yang sama

=== KEBIJAKAN REFUND/BATAL ===
- Batal hanya bisa sebelum admin memproses
- Transaksi yang sudah diproses tidak bisa di-refund
- Kalau ada masalah setelah transaksi, lapor ke admin di tiket dengan bukti lengkap

=== METODE PEMBAYARAN ===
- QRIS (semua layanan)
- DANA (kecuali topup ML/FF)
- BCA Transfer (kecuali topup ML/FF)
Nominal transfer sesuai yang tertera di tiket. Kirim bukti bayar di dalam tiket.

=== KALAU MEMBER RAGU ATAU TIDAK PERCAYA ===
Arahkan ke channel testimoni {TESTIMONI_CHANNEL} — biar mereka lihat sendiri ulasan dari pembeli sebelumnya. Jangan maksa, cukup kasih tau channel-nya.

=== TIM ADMIN ===
Saat menyebut admin, SELALU gunakan format <@ID> persis seperti di bawah ini, jangan tulis angka ID-nya saja:
Vilog: {ADMIN_VILOG}
Robux Store: {ADMIN_ROBUX}
Topup ML/FF: {ADMIN_ML}
Midman: {ADMIN_MIDMAN}
Cloud Phone / Nitro / SC Aset: {ADMIN_LAINNYA}
Kalau member tanya siapa adminnya, sebutkan admin yang sesuai dengan layanan yang ditanya.

=== LAYANAN LAINNYA ===
Selain Robux, Cellyn Store juga punya layanan berikut, semuanya di {LAINNYA_CHANNEL}:

CLOUD PHONE (Redfinger)
Sewa cloud phone Redfinger untuk main game 24 jam tanpa HP kepanasan.
Paket tersedia: VIP / KVIP / SVIP / XVIP — durasi 7 hari atau 30 hari.
Harga mulai Rp 20.500.

DISCORD NITRO
- Nitro Boost 1 Bulan — Rp 25.000
- Nitro Boost 3 Bulan — Rp 50.000

SC TB / ASET GAME
Jual beli item game, SCTB/secret tumbal, batu evo, dan aset untuk quest/misi/experience.
Harga per item Rp 300 – Rp 700 (tergantung jenis item dan stock yang tersedia).
Stock terbatas — tanya admin dulu soal ketersediaan.

Cara order semua layanan di atas:
- Pergi ke {LAINNYA_CHANNEL}
- Klik tombol kategori yang sesuai
- Ikuti instruksi di dalam tiket

=== YANG TIDAK BISA KAMU JAWAB ===
- Harga spesifik produk → suruh cek di channel catalog karena rate berubah
- Status pesanan member lain → suruh tanya admin
- Pertanyaan teknis di luar pengetahuanmu → jujur dan suruh tanya admin langsung

Kalau ada yang ngobrol umum, jawab natural aja kayak teman chat — jangan dipaksain nyambung ke toko. Cukup sebut layanan Cellyn Store kalau memang relevan atau ada yang nanya duluan. Jangan jualan kalau tidak ditanya."""

def build_system_prompt() -> str:
    data = {
        "ROBUX_CHANNEL": _ch(_env_id("ROBUX_CHANNEL_ID", "1479386215080792097")),
        "VILOG_CHANNEL": _ch(_env_id("VILOG_CHANNEL_ID", "1478917118715236603")),
        "ML_CHANNEL": _ch(_env_id("ML_CHANNEL_ID", "1479619145564950579")),
        "MIDMAN_CHANNEL": _ch(_env_id("MIDMAN_CHANNEL_ID", "1478170368723259572")),
        "TESTIMONI_CHANNEL": _ch(_env_id("TESTIMONI_CHANNEL_ID", "1476349920758992897")),
        "LAINNYA_CHANNEL": _ch(_env_id("LAINNYA_CHANNEL_ID", "1476349829113315489")),
        "ADMIN_VILOG": _mentions("ADMIN_VILOG_MENTIONS", "<@1428825165369839639> <@1430728197720375367>"),
        "ADMIN_ROBUX": _mentions("ADMIN_ROBUX_MENTIONS", "<@1428825165369839639> <@1430728197720375367>"),
        "ADMIN_ML": _mentions("ADMIN_ML_MENTIONS", "<@924910652626198548>"),
        "ADMIN_MIDMAN": _mentions("ADMIN_MIDMAN_MENTIONS", "<@1428825165369839639> <@1430728197720375367>"),
        "ADMIN_LAINNYA": _mentions("ADMIN_LAINNYA_MENTIONS", "<@1428825165369839639> <@1430728197720375367>"),
    }
    return SYSTEM_PROMPT_TEMPLATE.format(**data)

SYSTEM_PROMPT = build_system_prompt()



class AIChat(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # history per user: {user_id: [{"role": ..., "content": ...}, ...]}
        self.histories: dict[int, list] = {}
        # cooldown per user: {user_id: last_message_timestamp}
        self.cooldowns: dict[int, float] = {}

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"Cog AIChat siap. Channel ID: {get_ai_channel_id()}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        ai_ch_id = get_ai_channel_id()
        if ai_ch_id == 0:
            return
        if message.channel.id != ai_ch_id:
            return
        if not message.content or message.content.startswith("!"):
            return
        user_id = message.author.id

        # Cooldown check
        now = time.time()
        last = self.cooldowns.get(user_id, 0)
        sisa = COOLDOWN_SECONDS - (now - last)
        if sisa > 0:
            await message.reply(
                f"Sabar bentar ya, tunggu {sisa:.1f} detik lagi 😅",
                delete_after=3
            )
            return
        self.cooldowns[user_id] = now

        # Jalankan typing loop + request Groq bersamaan
        reply = await self._typing_and_ask(message)
        await message.reply(reply, allowed_mentions=discord.AllowedMentions.none())

    async def _typing_and_ask(self, message: discord.Message) -> str:
        """Kirim typing indicator terus-menerus sambil nunggu Groq respond."""
        result = {}

        async def keep_typing():
            while not result.get("done"):
                await message.channel.typing()
                await asyncio.sleep(5)

        typing_task = asyncio.create_task(keep_typing())
        try:
            reply = await self.ask_groq(message.author.id, message.content)
        finally:
            result["done"] = True
            typing_task.cancel()

        return reply

    async def ask_groq(self, user_id: int, user_message: str) -> str:
        if user_id not in self.histories:
            self.histories[user_id] = []

        history = self.histories[user_id]
        history.append({"role": "user", "content": user_message})

        # Batasi history
        if len(history) > MAX_HISTORY * 2:
            history = history[-(MAX_HISTORY * 2):]
            self.histories[user_id] = history


        api_key = _get_next_key()
        if not api_key:
            return "API key belum diset. Hubungi admin ya!"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history
        payload = {
            "model": MODEL,
            "messages": messages,
            "max_tokens": 512,
            "temperature": 0.7
        }

        try:
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # Coba semua key satu per satu sampai ada yang berhasil
                tried = 1  # sudah pakai 1 key di headers awal
                last_status = None
                current_key = api_key

                while True:
                    async with session.post(GROQ_API_URL, headers=headers, json=payload) as resp:
                        if resp.status == 200:
                            try:
                                data = await resp.json()
                                reply = (
                                    data.get("choices", [{}])[0]
                                    .get("message", {})
                                    .get("content", "")
                                    .strip()
                                )
                                if not reply:
                                    history.pop()
                                    return "AI lagi ada gangguan teknis nih 🔧 Tanya langsung ke admin aja dulu ya, nanti kalau sudah normal bisa chat lagi!"
                                history.append({"role": "assistant", "content": reply})
                                return reply
                            except Exception:
                                history.pop()
                                return "AI lagi ada gangguan teknis nih 🔧 Tanya langsung ke admin aja dulu ya, nanti kalau sudah normal bisa chat lagi!"
                        err = await resp.text()
                        last_status = resp.status
                        print(f"[GROQ ERROR] key ke-{tried} status={resp.status} body={err[:200]}")
                        if resp.status == 429 and tried < len(GROQ_KEYS):
                            print(f"[GROQ] Rotasi ke key ke-{tried+1}...")
                            next_key = _get_next_key()
                            headers["Authorization"] = f"Bearer {next_key}"
                            tried += 1
                        else:
                            # Semua key sudah dicoba atau error bukan 429
                            history.pop()
                            if last_status == 429:
                                return "😵 tunggu bentar..."
                            return "AI lagi ada gangguan teknis nih 🔧 Tanya langsung ke admin aja dulu ya, nanti kalau sudah normal bisa chat lagi!"
        except Exception as e:
            print(f"[GROQ EXCEPTION] {e}")
            history.pop()
            return "AI lagi tidak bisa dihubungi nih 😕 Tanya langsung ke admin aja dulu ya!"


async def setup(bot: commands.Bot):
    await bot.add_cog(AIChat(bot))
    print("Cog AIChat siap.")
