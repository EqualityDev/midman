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

def get_ai_channel_id():
    try:
        return int(os.getenv("AI_CHANNEL_ID", 0))
    except Exception:
        return 0

COOLDOWN_SECONDS = 1      # jeda antar pesan per user
MAX_HISTORY = 10          # maksimal pesan history per user (user+bot = 1 pasang)

SYSTEM_PROMPT = """Kamu adalah bot di server Discord Cellyn Store. Tapi jangan anggap diri kamu sebagai CS atau orang jualan — anggap diri kamu sebagai teman nongkrong di server yang kebetulan tau banyak soal Cellyn.

Gaya ngobrolnya santai, singkat, natural — kayak chat sama teman, bukan customer service. Pakai bahasa gaul Indonesia yang wajar. Kalau tidak tahu atau tidak yakin, jujur aja.

ATURAN PALING PENTING:
- Kalau orang ngobrol random (nanya soal game, curhat, bercanda, ngomongin hal lain) → jawab natural sesuai topik, JANGAN belokkan ke Cellyn
- Sebut Cellyn HANYA kalau orang nanya soal produk, topup, jual beli, atau hal yang memang nyambung ke layanan Cellyn
- Jangan pernah promosi, jangan selip-selipkan nama toko, jangan maksa jualan
- Kalau ada yang nanya produk, baru jelasin dengan santai — bukan hard selling
- Kalau pertanyaannya simple, jawab simple. Jangan panjang-panjang kalau tidak perlu.

=== TENTANG CELLYN STORE ===
Cellyn Store adalah toko digital di Discord yang jual produk Roblox, topup game, dan jasa middleman. Semua transaksi dilayani via tiket otomatis di Discord. Pembayaran via QRIS, DANA, atau BCA transfer.

=== LAYANAN & CARA ORDER ===

1. ROBUX STORE
   Jual item Roblox. Kategori: GAMEPASS, CRATE, BOOST, LIMITED ITEM.
   Harga = jumlah Robux x rate yang berlaku.
   TOPUP ROBUX VIA GAMEPASS: metode beli Robux langsung via pembelian gamepass — ini belum tersedia saat ini, masih dalam rencana dan akan segera hadir di Cellyn. Kalau ada yang nanya, bilang 'coming soon, nantikan aja'.
   Harga = jumlah Robux × rate yang berlaku (rate bisa berubah sewaktu-waktu).
   Cara order:
   - Pergi ke <#1479386215080792097>
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
   - Pergi ke <#1478917118715236603>
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
   - Pergi ke <#1479619145564950579>
   - Pilih diamond reguler atau WDP dari dropdown
   - Isi form: ID ML + Server ID (cek di profil ML kamu)
   - Bayar via QRIS
   - Admin proses topup langsung ke akun
   Estimasi proses: 5–15 menit.
   Bayar: QRIS

4. TOPUP FREE FIRE
   Topup diamond Free Fire langsung ke ID.
   Cara order:
   - Pergi ke <#1479619145564950579>
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
   - Pergi ke <#1478170368723259572>
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
   - Penjual buka tiket via tombol Midman Jual Beli di <#1478170368723259572>
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
Arahkan ke channel testimoni <#1476349920758992897> — biar mereka lihat sendiri ulasan dari pembeli sebelumnya. Jangan maksa, cukup kasih tau channel-nya.

=== TIM ADMIN ===
Vilog: <@1428825165369839639> <@1430728197720375367>
Robux Store: <@1428825165369839639> <@1430728197720375367>
Topup ML/FF: <@924910652626198548>
Midman: <@1428825165369839639> <@1430728197720375367>
Kalau member tanya siapa adminnya, sebutkan admin yang sesuai dengan layanan yang ditanya.

=== ITEM DI LUAR ROBUX ===
Kalau member cari item selain produk Robux (seperti Discord Nitro, secret tumbal untuk misi exp/batu evo, PT boost x8, dll), arahkan ke <#1476349829113315489> — di sana ada berbagai item menarik lainnya.

=== YANG TIDAK BISA KAMU JAWAB ===
- Harga spesifik produk → suruh cek di channel catalog karena rate berubah
- Status pesanan member lain → suruh tanya admin
- Pertanyaan teknis di luar pengetahuanmu → jujur dan suruh tanya admin langsung

Kalau ada yang ngobrol umum, jawab natural aja kayak teman chat — jangan dipaksain nyambung ke toko. Cukup sebut layanan Cellyn Store kalau memang relevan atau ada yang nanya duluan. Jangan jualan kalau tidak ditanya."""



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
        await message.reply(reply)

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
            async with aiohttp.ClientSession() as session:
                # Coba semua key satu per satu sampai ada yang berhasil
                tried = 1  # sudah pakai 1 key di headers awal
                last_status = None
                current_key = api_key

                while True:
                    async with session.post(GROQ_API_URL, headers=headers, json=payload) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            reply = data["choices"][0]["message"]["content"].strip()
                            history.append({"role": "assistant", "content": reply})
                            return reply
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
                                return "AI lagi istirahat bentar karena terlalu banyak request 😴 Coba lagi dalam beberapa menit, atau tanya langsung ke admin ya!"
                            return "AI lagi ada gangguan teknis nih 🔧 Tanya langsung ke admin aja dulu ya, nanti kalau sudah normal bisa chat lagi!"
        except Exception as e:
            print(f"[GROQ EXCEPTION] {e}")
            history.pop()
            return "AI lagi tidak bisa dihubungi nih 😕 Tanya langsung ke admin aja dulu ya!"


async def setup(bot: commands.Bot):
    await bot.add_cog(AIChat(bot))
    print("Cog AIChat siap.")