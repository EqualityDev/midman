import datetime

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore[assignment]


OPEN_HOUR_WIB = 9
CLOSE_HOUR_WIB = 23


def get_wib_tzinfo() -> datetime.tzinfo:
    # Termux/Python builds may not ship IANA tzdata. WIB has no DST, so UTC+7 is safe.
    if ZoneInfo is not None:
        try:
            return ZoneInfo("Asia/Jakarta")  # type: ignore[misc]
        except Exception:
            pass
    return datetime.timezone(datetime.timedelta(hours=7), name="WIB")


WIB = get_wib_tzinfo()


def is_store_open(now: datetime.datetime | None = None) -> bool:
    now_wib = now.astimezone(WIB) if now else datetime.datetime.now(WIB)
    # OPEN: 09:00-22:59 WIB, CLOSE: 23:00-08:59 WIB
    return OPEN_HOUR_WIB <= now_wib.hour < CLOSE_HOUR_WIB

