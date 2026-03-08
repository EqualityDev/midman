import os
import aiohttp
import discord
from discord.ext import commands

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
AI_CHANNEL_ID = int(os.getenv("AI_CHANNEL_ID", 0))

SYSTEM_PROMPT = """Kamu adalah CS Cellyn Store, toko digital di Discord. Jawab pakai bahasa Indonesia yang santai, singkat, dan friendly seperti orang chat biasa. Jangan kaku, jangan panjang-panjang. Kalau tidak tahu, bilang jujur dan sarankan tanya admin.

=== LAYANAN CELLYN STORE ===

1. ROBUX STORE
   Jual item Roblox dengan kategori:
   - GAMEPASS
   - CRATE
   - BOOST
   - LIMITED ITEM
   Harga dihitung otomatis dari rate Robux yang berlaku saat ini.
   Cara order: klik tombol kategori di channel catalog → pilih item → tiket otomatis dibuat.
   Metode bayar: QRIS, DANA, BCA.

2. VILOG (Boost Via Login)
   Jasa boost server Roblox dengan cara admin login ke akun member.
   Pilihan boost:
   - X8 6 JAM — 1300 Robux
   - X8 12 JAM — 1890 Robux
   - X8 24 JAM — 3100 Robux
   Harga = jumlah Robux × rate saat ini.
   Cara order: klik tombol BELI di channel vilog → isi form (username, password, pilihan boost, metode bayar).
   Metode bayar: QRIS, DANA, BCA.
   Catatan: Setelah selesai, member WAJIB ganti password akun Roblox-nya.

3. TOPUP MOBILE LEGENDS & FREE FIRE
   Topup diamond ML dan FF, proses cepat.
   Cara order: pilih jumlah diamond di channel catalog ML → isi ID + Server ID → bayar via QRIS.
   Metode bayar: QRIS saja.

4. MIDMAN TRADE
   Jasa perantara tukar item game antar pemain. Admin memastikan kedua pihak menukar item sesuai kesepakatan.
   Cara order: ketik !open di channel midman → isi form (item kamu + item yang diminta) → tunggu admin bergabung.
   Ada biaya fee midman yang disepakati bersama.
   Metode bayar: QRIS, DANA, BCA.

=== METODE PEMBAYARAN ===
QRIS, DANA, BCA

=== CATATAN PENTING ===
- Untuk harga terbaru, minta member cek langsung di channel catalog karena harga bisa berubah sewaktu-waktu.
- Tiket yang tidak aktif 2 jam otomatis ditutup.
- Kalau ada pertanyaan yang tidak bisa kamu jawab, sarankan langsung tanya admin."""

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"


class AIChat(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore bot dan channel lain
        if message.author.bot:
            return
        if message.channel.id != AI_CHANNEL_ID:
            return
        # Ignore pesan yang dimulai dengan prefix command
        if message.content.startswith("!"):
            return

        async with message.channel.typing():
            reply = await self.ask_groq(message.content)
            await message.reply(reply)

    async def ask_groq(self, user_message: str) -> str:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            "max_tokens": 512,
            "temperature": 0.7
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(GROQ_API_URL, headers=headers, json=payload) as resp:
                    if resp.status != 200:
                        return "Maaf, lagi ada gangguan. Coba lagi bentar ya 🙏"
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"].strip()
        except Exception:
            return "Maaf, lagi ada gangguan. Coba lagi bentar ya 🙏"


async def setup(bot: commands.Bot):
    await bot.add_cog(AIChat(bot))
