import datetime

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore[assignment]

from discord.ext import commands, tasks

from utils.config import GUILD_ID


STATUS_VOICE_CHANNEL_ID = 1476382504838500362
OPEN_NAME = "🟢 STATUS : OPEN"
CLOSE_NAME = "🔴 STATUS : CLOSE"

def _get_wib_tzinfo() -> datetime.tzinfo:
    # Termux/Python builds may not ship IANA tzdata. WIB has no DST, so UTC+7 is safe.
    if ZoneInfo is not None:
        try:
            return ZoneInfo("Asia/Jakarta")  # type: ignore[misc]
        except Exception:
            pass
    return datetime.timezone(datetime.timedelta(hours=7), name="WIB")


WIB = _get_wib_tzinfo()


def _is_open(now_wib: datetime.datetime) -> bool:
    # OPEN: 09:00-22:59 WIB, CLOSE: 23:00-08:59 WIB
    return 9 <= now_wib.hour < 23


class StoreStatusCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._status_loop.start()
        self.bot.loop.create_task(self._initial_sync())

    def cog_unload(self):
        self._status_loop.cancel()

    async def _initial_sync(self):
        await self.bot.wait_until_ready()
        await self._apply_status()

    @tasks.loop(
        time=[
            datetime.time(hour=9, minute=0, tzinfo=WIB),
            datetime.time(hour=23, minute=0, tzinfo=WIB),
        ]
    )
    async def _status_loop(self):
        await self._apply_status()

    @_status_loop.before_loop
    async def _before_status_loop(self):
        await self.bot.wait_until_ready()

    async def _apply_status(self):
        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            return
        channel = guild.get_channel(STATUS_VOICE_CHANNEL_ID)
        if not channel:
            return

        now_wib = datetime.datetime.now(WIB)
        new_name = OPEN_NAME if _is_open(now_wib) else CLOSE_NAME
        if getattr(channel, "name", None) == new_name:
            return
        try:
            await channel.edit(name=new_name)
        except Exception as e:
            print(f"[StoreStatus] Update error: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(StoreStatusCog(bot))
