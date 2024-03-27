"""
General utility functions that don't fit into any other category
Any function that requires global vars or is a task should not go here
RoWhoIs 2024
"""
import discord, datetime, re, inspect
from utils import logger
from typing import Optional

log_collector = logger.AsyncLogCollector("logs/main.log")
userCooldowns = {}

async def fancy_time(last_online_timestamp: str) -> str:
    """Converts a datetime string to a human-readable, relative format"""
    try:
        match = re.match(r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(\.\d+)?Z", last_online_timestamp)
        if match:
            year, month, day, hour, minute, second, microsecond = match.groups()
            lastOnlineDatetime = datetime.datetime(int(year), int(month), int(day), int(hour), int(minute), int(second), int(float(microsecond) * 1_000_000) if microsecond else 0)
        else: return last_online_timestamp
        timeDifference = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - lastOnlineDatetime
        timeUnits = [("year", 12, timeDifference.days // 365), ("month", 1, timeDifference.days // 30),  ("week", 7, timeDifference.days // 7), ("day", 1, timeDifference.days), ("hour", 60, timeDifference.seconds // 3600), ("minute", 60, timeDifference.seconds // 60), ("second", 1, timeDifference.seconds)]
        for unit, _, value in timeUnits:
            if value > 0:
                lastOnlineFormatted = f"{value} {unit + 's' if value != 1 else unit} ago"
                break
        else: lastOnlineFormatted = f"{timeDifference.seconds} {'second' if timeDifference.seconds == 1 else 'seconds'} ago"
        lastOnlineFormatted += f" ({lastOnlineDatetime.strftime('%m/%d/%Y %H:%M:%S')})"
        return lastOnlineFormatted
    except Exception as e:
        await log_collector.error(f"Error formatting time: {e} | Returning fallback data: {last_online_timestamp}")
        return last_online_timestamp

class ShardAnalytics:
    def __init__(self, shard_count: int, init_shown: bool): self.shard_count, self.init_shown = shard_count, init_shown

async def shard_metrics(interaction: discord.Interaction) -> Optional[int]:
    """Returns the shard type for the given interaction"""
    return interaction.guild.shard_id if interaction.guild else None

async def safe_wrapper(task, *args):
    """Allows asyncio.gather to continue even if a thread throws an exception"""
    try: return await task(*args)
    except Exception as e: return e
