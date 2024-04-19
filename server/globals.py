from utils import logger, ErrorDict
from pathlib import Path
from server import Roquest
from typing import Tuple
import asyncio, time

heartBeat,  roliData, lastRoliUpdate = False, {}, 0
log_collector = logger.AsyncLogCollector("logs/main.log")

async def coro_heartbeat():
    """[LOCAL COROUTINE, DO NOT USE]"""
    global heartBeat
    while True:
        try: heartBeat = await Roquest.heartbeat()
        except Exception: heartBeat = False
        await asyncio.sleep(60)

async def coro_update_rolidata() -> None:
    """[LOCAL COROUTINE, DO NOT USE]"""
    global roliData, lastRoliUpdate
    while True:
        try:
            newData = await Roquest.RoliData()
            if newData is not None:
                lastRoliUpdate = time.time()
                roliData = newData
            else: await log_collector.error("Failed to update Rolimons data.", initiator="RoWhoIs.update_rolidata")
        except ErrorDict.UnexpectedServerResponseError: pass
        except Exception as e: await log_collector.error(f"Error updating Rolimons data: {e}", initiator="RoWhoIs.coro_update_rolidata")
        await asyncio.sleep(3600)

async def coro_flush_volatile_cache() -> None:
    """Flushes volatile cache every minute"""
    while True:
        for file in Path("cache/volatile/").glob("**/*"):
            if file.is_file(): file.unlink()
        await asyncio.sleep(60)

async def init() -> None:
    """Estantiates the global coroutines"""
    return

loop = asyncio.get_event_loop()
loop.create_task(coro_heartbeat())
loop.create_task(coro_update_rolidata())
loop.create_task(coro_flush_volatile_cache())