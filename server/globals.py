from utils import errors
from typing import Any
from pathlib import Path
from server import request
import asyncio, time, aiohttp

heartBeat,  roliData, lastRoliUpdate, eggFollowers = False, {}, 0, []

async def coro_heartbeat():
    """[LOCAL COROUTINE, DO NOT USE]"""
    global heartBeat
    while True:
        try: heartBeat = await request.heartbeat()
        except Exception: heartBeat = False
        await asyncio.sleep(60)

async def coro_update_rolidata() -> None:
    """[LOCAL COROUTINE, DO NOT USE]"""
    global roliData, lastRoliUpdate
    while True:
        try:
            newData = await request.RoliData()
            if newData is not None:
                lastRoliUpdate = time.time()
                roliData = newData
            else: logs.error("Failed to update Rolimons data.", initiator="RoWhoIs.update_rolidata")
        except errors.UnexpectedServerResponseError: pass
        except Exception as e: logs.error(f"Error updating Rolimons data: {e}", initiator="RoWhoIs.coro_update_rolidata")
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
        except Exception as e: logs.error(f"Error fetching followers: {e}", initiator="RoWhoIs.coro_fetch_followers")
        await asyncio.sleep(35)

def init(eggEnabled: bool) -> None:
    """Estantiates the global coroutines"""
    if eggEnabled: loop.create_task(coro_fetch_followers())
    return

async def returnProxies() -> Any:
    return [await request.ret_on_prox(), await request.ret_glob_proxies()]

loop = asyncio.get_event_loop()
loop.create_task(coro_heartbeat())
loop.create_task(coro_update_rolidata())
