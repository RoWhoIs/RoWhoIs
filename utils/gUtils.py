"""
General utility functions that don't fit into any other category
Any function that requires global vars or is a task should not go here
RoWhoIs 2024
"""
import aiofiles
import hikari, datetime, re, inspect, time, os, json, asyncio, io
from pathlib import Path
from utils import logger
from typing import Optional, Any

log_collector = logger.AsyncLogCollector("logs/main.log")


async def fancy_time(initstamp: str, ret_type: str = "R") -> str:
    """Converts a datetime string or a Unix timestamp to a Discord relative time format"""
    try:
        if isinstance(initstamp, (int, float)): initstamp = datetime.datetime.fromtimestamp(initstamp, tz=datetime.timezone.utc)
        elif not isinstance(initstamp, datetime.datetime):
            match = re.match(r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(\.\d+)?Z", initstamp)
            if match:
                year, month, day, hour, minute, second, microsecond = match.groups()
                initstamp = datetime.datetime(int(year), int(month), int(day), int(hour), int(minute), int(second), int(float(microsecond)) if microsecond else 0, tzinfo=datetime.timezone.utc)
        return f"<t:{int(initstamp.timestamp())}:{ret_type}>"
    except Exception as e:
        await log_collector.error(f"Error formatting time: {e} | Returning fallback data: {initstamp}",
                                  initiator="RoWhoIs.fancy_time")
        return str(initstamp)

async def ret_uptime(uptime) -> str:
    """Returns a human-readable uptime string"""
    uptime = time.time() - uptime
    days, remainder = divmod(uptime, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{int(days)} day{'s' if int(days) != 1 else ''}, {int(hours)} hour{'s' if int(hours) != 1 else ''}, {int(minutes)} minute{'s' if int(minutes) != 1 else ''}"


class ShardAnalytics:
    def __init__(self, shard_count: int, init_shown: bool): self.shard_count, self.init_shown = shard_count, init_shown

async def shard_metrics(interaction: hikari.CommandInteraction) -> Optional[int]:
    """Returns the shard id for the given interaction"""
    guild = interaction.get_guild()
    return guild.shard_id if guild else None

async def safe_wrapper(task, *args):
    """Allows asyncio.gather to continue even if a thread throws an exception"""
    try: return await task(*args)
    except Exception as e: return e

async def cache_cursor(cursor: str, type: str, key: int, write: bool = False, pagination: int = None) -> Optional[str]:
    key, pagination = str(key), str(pagination) if pagination else '0'
    filename = "cache/cursors.json"
    cursors = {}
    if os.path.exists(filename):
        async with aiofiles.open(filename, "r") as f: cursors = json.loads(await f.read())
    if write:
        cursors.setdefault(type, {}).setdefault(key, {"expires": time.time() + 3600})
        cursors[type][key].setdefault(pagination, {})["cursor"] = cursor
    else:
        for type_key, type_value in list(cursors.items()):
            for key_key in list(type_value.keys()):
                if 'expires' in cursors[type_key][key_key] and cursors[type_key][key_key]['expires'] < time.time(): del cursors[type_key][key_key]
        if type in cursors and key in cursors[type] and pagination in cursors[type][key]: return cursors[type][key][pagination]["cursor"]
    async with aiofiles.open(filename, "w") as f: await f.write(json.dumps(cursors))
    return None
