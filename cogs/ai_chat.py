import os
import asyncio
import time
import aiohttp
import discord
from discord.ext import commands

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def get_ai_channel_id():
    try:
        return int(os.getenv("AI_CHANNEL_ID", 0))
    except Exception:
        return 0

COOLDOWN_SECONDS = 3      # jeda antar pesan per user
MAX_HISTORY = 10          # maksimal pesan history per user (user+bot = 1 pasang)

SYSTEM_PROMPT = """Kamu adalah CS bot Cellyn Store, toko digital yang jual produk game di Discord. Gaya jawabmu santai, singkat, to the point — kayak orang chat biasa, bukan robot kaku. Pakai bahasa gaul Indonesia yang wajar. Kalau tidak tahu atau tidak yakin, jujur aja dan suruh tanya admin langsung.

Jangan pernah jawab panjang-panjang kalau tidak perlu. Kalau pertanyaannya simple, jawab simple.

=== TENTANG CELLYN STORE ===
Cellyn Store adalah toko digital di Discord yang jual produk Roblox, topup game, dan jasa middleman. Semua transaksi dilayani via tiket otomatis di Discord. Pembayaran via QRIS, DANA, atau BCA transfer.

=== LAYANAN & CARA ORDER ===

1. ROBUX STORE
   Jual item Roblox. Kategori: GAMEPASS, CRATE, BOOST, LIMITED ITEM.
   Harga = jumlah Robux × rate yang berlaku (rate bisa berubah sewaktu-waktu).
   Cara order:
   - Pergi ke channel catalog robux
   - Klik tombol kategori yang diinginkan
   - Pilih item dari dropdown
   - Tiket otomatis terbuka, ikuti instruksi di dalam tiket
   - Transfer sesuai nominal yang tertera, kirim bukti bayar
   - Admin proses, item dikirim via gift Roblox
   Bayar: QRIS, DANA, BCA

2. VILOG (Boost Via Login)
   Jasa boost server Roblox — admin login ke akun Roblox member untuk aktivasi boost.
   Paket tersedia:
   - X8 Boost 6 Jam — 1300 Robux
   - X8 Boost 12 Jam — 1890 Robux
   - X8 Boost 24 Jam — 3100 Robux
   Harga = jumlah Robux × rate saat ini.
   Cara order:
   - Pergi ke channel vilog
   - Klik tombol BELI
   - Isi form: username Roblox, password, pilihan boost, metode bayar
   - Tiket terbuka, ikuti instruksi
   - Setelah boost selesai, WAJIB langsung ganti password akun Roblox
   Bayar: QRIS, DANA, BCA
   Catatan penting: Admin hanya butuh akses login untuk boost, tidak ada tindakan lain. Tapi demi keamanan, ganti password setelah selesai.

3. TOPUP MOBILE LEGENDS
   Topup diamond Mobile Legends langsung ke ID.
   Cara order:
   - Pergi ke channel catalog ML
   - Pilih jumlah diamond ML dari dropdown
   - Isi form: ID ML + Server ID
   - Bayar via QRIS
   - Admin proses topup langsung ke akun
   Bayar: QRIS

4. TOPUP FREE FIRE
   Topup diamond Free Fire langsung ke ID.
   Cara order:
   - Pergi ke channel catalog ML (sama channelnya dengan ML)
   - Pilih jumlah diamond FF dari dropdown
   - Isi form: Player ID FF
   - Bayar via QRIS
   - Admin proses topup langsung ke akun
   Bayar: QRIS

5. MIDMAN TRADE
   Jasa perantara tukar item game antar dua pemain. Admin jadi saksi dan memastikan kedua pihak jujur.
   Cocok untuk: tukar item Roblox, tukar akun, atau barter apapun yang butuh pihak ketiga.
   Cara order:
   - Pergi ke channel midman
   - Klik tombol Midman Trade
   - Isi form: item yang kamu punya + item yang kamu minta dari lawan
   - Tiket terbuka, tunggu admin bergabung
   - Admin setup detail + fee, ikuti instruksi
   Bayar fee: QRIS, DANA, BCA

6. MIDMAN JUAL BELI
   Jasa perantara jual beli item/akun game. Admin menahan uang pembeli dulu, baru diserahkan ke penjual setelah pembeli konfirmasi item oke.
   Cocok untuk: jual beli akun Roblox, item game, atau aset digital lainnya.
   Cara order:
   - Pergi ke channel midman
   - Klik tombol Midman Jual Beli
   - Penjual isi form: deskripsi item + harga
   - Admin tambahkan pembeli ke tiket, setup fee + siapa yang menanggung
   - Pembeli transfer ke admin
   - Admin serahkan item ke pembeli
   - Pembeli konfirmasi item oke → admin release dana ke penjual
   Bayar: QRIS, DANA, BCA

=== ALUR TIKET (PENTING) ===
- Semua transaksi pakai sistem tiket otomatis — channel private terbuka khusus untuk kamu dan admin
- Tiket yang tidak ada aktivitas selama 1 jam dapat peringatan
- Tiket tidak aktif 2 jam otomatis ditutup
- Kalau tiket sudah tutup dan belum selesai, buka tiket baru

=== METODE PEMBAYARAN ===
- QRIS (semua layanan)
- DANA (kecuali topup ML/FF)
- BCA Transfer (kecuali topup ML/FF)
Nominal transfer sesuai yang tertera di tiket. Kirim bukti bayar di dalam tiket.

=== YANG TIDAK BISA KAMU JAWAB ===
- Harga spesifik produk → suruh cek di channel catalog karena rate berubah
- Status pesanan member lain → suruh tanya admin
- Pertanyaan teknis yang di luar pengetahuanmu → jujur dan tag admin

Kalau ada yang tanya di luar topik Cellyn Store, boleh jawab dengan santai seperti biasa — kamu tetap bisa ngobrol umum, bantu pertanyaan random, dll. Tapi kalau ada yang tanya soal toko, prioritaskan info Cellyn Store dulu."""

GEMINI_MODEL = "gemini-2.0-flash"


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
            reply = await self.ask_gemini(message.author.id, message.content)
        finally:
            result["done"] = True
            typing_task.cancel()

        return reply

    async def ask_gemini(self, user_id: int, user_message: str) -> str:
        if user_id not in self.histories:
            self.histories[user_id] = []

        history = self.histories[user_id]
        history.append({"role": "user", "parts": [{"text": user_message}]})

        # Batasi history
        if len(history) > MAX_HISTORY * 2:
            history = history[-(MAX_HISTORY * 2):]
            self.histories[user_id] = history

        url = f"https://generativelanguage.googleapis.com/v1/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"

        payload = {
            "system_instruction": {
                "parts": [{"text": SYSTEM_PROMPT}]
            },
            "contents": history,
            "generationConfig": {
                "maxOutputTokens": 512,
                "temperature": 0.7
            }
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as resp:
                    if resp.status != 200:
                        err = await resp.text()
                        print(f"[GEMINI ERROR] status={resp.status} body={err[:300]}")
                        history.pop()
                        return "Maaf, lagi ada gangguan. Coba lagi bentar ya 🙏"
                    data = await resp.json()
                    reply = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    history.append({"role": "model", "parts": [{"text": reply}]})
                    return reply
        except Exception as e:
            print(f"[GEMINI EXCEPTION] {e}")
            history.pop()
            return "Maaf, lagi ada gangguan. Coba lagi bentar ya 🙏"


async def setup(bot: commands.Bot):
    await bot.add_cog(AIChat(bot))
    print("Cog AIChat siap.")
