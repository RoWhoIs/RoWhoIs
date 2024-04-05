"""
General utility functions that don't fit into any other category
Any function that requires global vars or is a task should not go here
RoWhoIs 2024
"""
import aiofiles
import discord, datetime, re, inspect, time, os, json, asyncio
from utils import logger
from typing import Optional

log_collector = logger.AsyncLogCollector("logs/main.log")

async def fancy_time(initstamp: str, ret_type: str = "R") -> str:
    """Converts a datetime string to a Discord relative time format"""
    try:
        match = re.match(r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(\.\d+)?Z", initstamp)
        if match:
            year, month, day, hour, minute, second, microsecond = match.groups()
            lastOnlineDatetime = datetime.datetime(int(year), int(month), int(day), int(hour), int(minute), int(second), int(float(microsecond) * 1_000_000) if microsecond else 0)
            return f"<t:{int(time.mktime(lastOnlineDatetime.timetuple()))}:{ret_type}>"
        else: return initstamp
    except Exception as e:
        await log_collector.error(f"Error formatting time: {e} | Returning fallback data: {initstamp}")
        return initstamp

async def legacy_fancy_time(timestamp: datetime.time) -> str:
    """Legacy fancy time used for raw datetime formats without the use of Discord's relative time formatting"""
    try:
        timeDifference = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - timestamp
        timeUnits = [("year", 12, timeDifference.days // 365), ("month", 1, timeDifference.days // 30),  ("week", 7, timeDifference.days // 7), ("day", 1, timeDifference.days), ("hour", 60, timeDifference.seconds // 3600), ("minute", 60, timeDifference.seconds // 60), ("second", 1, timeDifference.seconds)]
        for unit, _, value in timeUnits:
            if value > 0:
                lastOnlineFormatted = f"{value} {unit + 's' if value != 1 else unit} ago"
                break
        else: lastOnlineFormatted = f"{timeDifference.seconds} {'second' if timeDifference.seconds == 1 else 'seconds'} ago"
        lastOnlineFormatted += f" ({timestamp.strftime('%m/%d/%Y %H:%M:%S')})"
        return lastOnlineFormatted
    except Exception as e:
        await log_collector.error(f"Error formatting time: {e} | Returning fallback data: {timestamp}")
        return timestamp

class ShardAnalytics:
    def __init__(self, shard_count: int, init_shown: bool): self.shard_count, self.init_shown = shard_count, init_shown

async def shard_metrics(interaction: discord.Interaction) -> Optional[int]:
    """Returns the shard type for the given interaction"""
    return interaction.guild.shard_id if interaction.guild else None

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
