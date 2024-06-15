from utils import logger, ErrorDict
from pathlib import Path
from server import Roquest
import asyncio, time, aiohttp

heartBeat,  roliData, lastRoliUpdate, eggFollowers = False, {}, 0, []
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

async def coro_fetch_followers() -> None:
    """Enable this coroutine if eggEnabled is True. Fetches followers from the RoWhoIs API every 35 seconds and updates the global eggFollowers list"""
    global eggFollowers
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://rowhois.com/api/followers") as response:
                    if response.status == 200:
                        data = await response.json()
                        eggFollowers = data.get("followerIds", 0)
        except Exception as e: await log_collector.error(f"Error fetching followers: {e}", initiator="RoWhoIs.coro_fetch_followers")
        await asyncio.sleep(35)

def init(eggEnabled: bool) -> None:
    """Estantiates the global coroutines"""
    if eggEnabled: loop.create_task(coro_fetch_followers())
    return

async def returnProxies() -> list[tuple[str, str]]:
    return [await Roquest.ret_on_prox(), await Roquest.ret_glob_proxies()]

loop = asyncio.get_event_loop()
loop.create_task(coro_heartbeat())
loop.create_task(coro_update_rolidata())
