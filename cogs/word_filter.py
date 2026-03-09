import re
import discord
from discord.ext import commands

# Daftar kata kasar — tambah/kurangi sesuai kebutuhan
BAD_WORDS = [
    "anjing", "anjg", "a njing", "4njing", "anying", "ajg", "ajig",
    "babi", "b4bi",
    "bangsat", "bngsat", "b4ngsat", "bgst",
    "kontol", "k0ntol", "kntol", "kntl", "kontl", k0nt0l",
    "memek", "m3mek", "mmk", "m3m3k",
    "ngentot", "ng3ntot", "ngewe", "ngwe", "ewe", "entod", "entd",
    "bajingan", "b4jingan",
    "tolol", "t0lol", "tlol", "tll",
    "goblok", "g0blok", "goblog", "gblk", "gblg", "g0bl0g", "g0bl0k",
    "bodoh", "bodo",
    "kampret", "k4mpret",
    "keparat", "k3parat",
    "sialan", "s1alan",
    "monyet", "m0nyet", "mnyt",
    "tai", "t4i", "tae", "taik",
    "jancok", "j4ncok", "jancuk", "j4ncuk", "jnck",
    "asu", "4su", "asw",
    "celeng",
    "dancok",
]

# Kompilasi regex sekali saja
_PATTERN = re.compile(
    r"(?<!\w)(" + "|".join(re.escape(w) for w in BAD_WORDS) + r")(?!\w)",
    re.IGNORECASE
)


def contains_bad_word(text: str) -> bool:
    # Normalisasi: hapus karakter non-alfanumerik berulang biar tidak lolos filter
    normalized = re.sub(r"[^a-zA-Z0-9\s]", "", text)
    return bool(_PATTERN.search(text)) or bool(_PATTERN.search(normalized))


class WordFilter(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore bot dan DM
        if message.author.bot:
            return
        if not message.guild:
            return
        # Ignore admin
        if message.author.guild_permissions.administrator:
            return

        if not contains_bad_word(message.content):
            return

        # Hapus pesan
        try:
            await message.delete()
        except discord.Forbidden:
            return
        except discord.NotFound:
            return

        # Kirim teguran di channel yang sama, auto-hapus 10 detik
        try:
            await message.channel.send(
                f"{message.author.mention} Mohon jaga bahasa ya maniez. "
                f"Kata-kata kasar tidak diperbolehkan di server ini 😉.",
                delete_after=10
            )
        except discord.Forbidden:
            pass

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        # Cek juga pesan yang diedit
        if after.author.bot:
            return
        if not after.guild:
            return
        if after.author.guild_permissions.administrator:
            return

        if not contains_bad_word(after.content):
            return

        try:
            await after.delete()
        except (discord.Forbidden, discord.NotFound):
            return

        try:
            await after.channel.send(
                f"{after.author.mention} Mohon jaga bahasa ya maniez. "
                f"Kata-kata kasar tidak diperbolehkan di server ini 😉.",
                delete_after=10
            )
        except discord.Forbidden:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(WordFilter(bot))
