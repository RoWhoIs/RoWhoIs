"""
General utility functions that don't fit into any other category
Any function that requires global vars or is a task should not go here
RoWhoIs 2024
"""
import discord, datetime, re, inspect, time
from utils import logger
from typing import Optional

log_collector = logger.AsyncLogCollector("logs/main.log")
userCooldowns = {}

async def fancy_time(last_online_timestamp: str) -> str:
    """Converts a datetime string to a Discord relative time format"""
    try:
        match = re.match(r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(\.\d+)?Z", last_online_timestamp)
        if match:
            year, month, day, hour, minute, second, microsecond = match.groups()
            lastOnlineDatetime = datetime.datetime(int(year), int(month), int(day), int(hour), int(minute), int(second), int(float(microsecond) * 1_000_000) if microsecond else 0)
            timestamp = int(time.mktime(lastOnlineDatetime.timetuple()))
            return f"<t:{timestamp}:R>"
        else: return last_online_timestamp
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
