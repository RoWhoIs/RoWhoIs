"""
General utility functions that don't fit into any other category
Any function that requires global vars or is a task should not go here
RoWhoIs 2024
"""
from dataclasses import dataclass
import datetime
import json
import os
import re
import time

import aiofiles
import hikari



async def fancy_time(initstamp: str, ret_type: str = "R") -> str:
    """Converts a datetime string or a Unix timestamp to a Discord relative time format"""
    try:
        if isinstance(initstamp, (int, float)):
            initstamp = datetime.datetime.fromtimestamp(initstamp, tz=datetime.timezone.utc)
        elif not isinstance(initstamp, datetime.datetime):
            match = re.match(r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(\.\d+)?Z", initstamp)
            if match:
                year, month, day, hour, minute, second, microsecond = match.groups()
                initstamp = datetime.datetime(
                    int(year), int(month), int(day), int(hour), int(minute),
                    int(second),
                    int(float(microsecond)) if microsecond else 0,
                    tzinfo=datetime.timezone.utc
                )
        return f"<t:{int(initstamp.timestamp())}:{ret_type}>"
    except Exception as e:  # noqa: W0718
        await logs.error(
            f"Error formatting time: {e} | Returning fallback data: {initstamp}",
            initiator="RoWhoIs.fancy_time"
        )
        return str(initstamp)


async def ret_uptime(uptime) -> str:
    """Returns a human-readable uptime string"""
    uptime = time.time() - uptime
    days, remainder = divmod(uptime, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)
    days_str = f"{int(days)} day{'s' if int(days) != 1 else ''}"
    hours_str = f"{int(hours)} hour{'s' if int(hours) != 1 else ''}"
    minutes_str = f"{int(minutes)} minute{'s' if int(minutes) != 1 else ''}"
    return f"{days_str}, {hours_str}, {minutes_str}"


@dataclass
class ShardAnalytics:
    """Used for saving shard analytics data"""
    shard_count: int
    init_shown: bool


async def shard_metrics(interaction: hikari.CommandInteraction) -> int | None:
    """Returns the shard id for the given interaction"""
    guild = interaction.get_guild()
    return guild.shard_id if guild else None


async def safe_wrapper(task, *args):
    """Allows asyncio.gather to continue even if a thread throws an exception"""
    try:
        return await task(*args)
    except Exception as e:  # noqa: W0718
        return e


async def cache_cursor(
    cursor: str | None, filetype: str, key: int,
    write: bool = False, pagination: int | None = None
) -> str | None:
    """Caches a cursor for a given key and pagination, or returns the cached cursor"""
    key, pagination = str(key), str(pagination) if pagination else '0'
    filename = "cache/cursors.json"
    cursors = {}
    if os.path.exists(filename):
        async with aiofiles.open(filename, "r") as f:
            cursors = json.loads(await f.read())
    if write:
        cursors.setdefault(filetype, {}).setdefault(key, {"expires": time.time() + 3600})
        cursors[filetype][key].setdefault(pagination, {})["cursor"] = cursor
    else:
        for type_key, type_value in list(cursors.items()):
            for key_key in list(type_value.keys()):
                if 'expires' in cursors[type_key][key_key]:
                    if cursors[type_key][key_key]['expires'] < time.time():
                        del cursors[type_key][key_key]
        if filetype in cursors and key in cursors[type] and pagination in cursors[filetype][key]:
            return cursors[filetype][key][pagination]["cursor"]
    async with aiofiles.open(filename, "w") as f:
        await f.write(json.dumps(cursors))
    return None
