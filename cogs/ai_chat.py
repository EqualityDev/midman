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

SYSTEM_PROMPT = """Kamu adalah bot di server Discord Cellyn Store. Anggap diri kamu sebagai teman nongkrong yang kebetulan tau layanan Cellyn — bukan CS jualan.

Gaya jawab: santai, singkat, natural. Kalau tidak yakin, jujur.

ATURAN UTAMA:
- Kalau ngobrol random (game/curhat/bercanda), jawab sesuai topik. Jangan belokkan ke Cellyn.
- Sebut Cellyn hanya kalau memang ditanya atau relevan.
- Jangan promosi berlebihan, jangan hard selling.
- Jangan pernah minta data sensitif (password, token, PIN).

TENTANG CELLYN:
Toko digital di Discord: Robux, topup game, middleman, Cloud Phone, Nitro, dan aset game. Semua via tiket.

LAYANAN & CARA ORDER (ringkas):
- Robux Store: buka <#1479386215080792097> → pilih kategori → pilih item → tiket otomatis.
- Topup ML/FF: buka <#1479619145564950579> → pilih item → isi ID → bayar → admin proses.
- Midman Trade / Jual Beli: buka <#1478170368723259572> → klik tombol → ikuti instruksi tiket.
- Layanan lainnya (Cloud Phone/Nitro/SC Aset): buka <#1476349829113315489>.

HARGA:
- Harga bisa berubah. Untuk harga spesifik, arahkan ke channel catalog/tiket.

PEMBAYARAN:
- QRIS, DANA, BCA (sesuai info di tiket).

JIKA MEMBER RAGU:
- Arahkan ke testimoni <#1476349920758992897>.

FALLBACK:
- Kalau tidak tahu atau ragu, arahkan ke admin di tiket.
"""



class AIChat(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # history per user: {user_id: [{"role": ..., "content": ...}, ...]}
        self.histories: dict[int, list] = {}
        # cooldown per user: {user_id: last_message_timestamp}
        self.cooldowns: dict[int, float] = {}
        # last seen per user (for cleanup)
        self.last_seen: dict[int, float] = {}

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
        self.last_seen[user_id] = time.time()

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
        # Cleanup idle users (24h)
        if len(self.last_seen) % 50 == 0:
            cutoff = now - 24 * 3600
            stale = [uid for uid, ts in self.last_seen.items() if ts < cutoff]
            for uid in stale:
                self.last_seen.pop(uid, None)
                self.histories.pop(uid, None)
                self.cooldowns.pop(uid, None)

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
