"""
RoWhoIs library for performing raw requests to API endpoints.
"""
import aiohttp, asyncio
from utils.logger import AsyncLogCollector
from utils import ErrorDict
from typing import Any

log_collector = AsyncLogCollector("logs/main.log")
lastProxy, x_csrf_token = None, ""

def initialize(config):
    """Sets configurations for proxying. Needs to be ran before running any other function."""
    try:
        global enableProxying, proxyUrls, proxyCredentials, logProxying, rsec, productionMode, proxyPool
        proxyPool = []
        enableProxying = config["Proxying"]["proxying_enabled"]
        logProxying = config["Proxying"]["log_proxying"]
        username, password = config["Proxying"]["username"], config["Proxying"]["password"]
        rsec = config["Authentication"]["roblosecurity"]
        if password == "": password = None
        proxyUrls = config["Proxying"]["proxy_urls"]
        productionMode = config["RoWhoIs"]["production_mode"]
        if username != "": proxyCredentials = aiohttp.BasicAuth(login=username, password=password)
        else: proxyCredentials = None
        if enableProxying: loop.create_task(proxy_handler())
        loop.create_task(validate_cookie())
    except KeyError: raise ErrorDict.MissingRequiredConfigs

async def proxy_handler() -> None:
    """Determines what proxies are usable by the server"""
    global enableProxying, proxyUrls, proxyCredentials, proxyPool, logProxying
    try:
        while enableProxying:
            async def test_proxy(alivesession, proxy_url):
                try:
                    async with alivesession.get("https://auth.roblox.com/", proxy=proxy_url, proxy_auth=proxyCredentials, timeout=2) as response:
                        if response.status == 200: return True
                except Exception: pass
                return False
            async with aiohttp.ClientSession() as session:
                if len(proxyUrls) <= 0 and logProxying: await log_collector.debug("No usable proxies found! Fallbacking to non-proxied.")
                else:
                    tasks = [test_proxy(session, proxy_url) for proxy_url in proxyUrls]
                    results = await asyncio.gather(*tasks)
                    proxyPool = [proxy_url for proxy_url, result in zip(proxyUrls, results) if result]
                    if len(proxyPool) <= 0 and logProxying: await log_collector.debug("No usable proxies found! Fallbacking to non-proxied.")
                    elif logProxying: await log_collector.debug(f"Refreshed proxy pool. {len(proxyPool)} usable IP{'s' if len(proxyPool) >= 2 else ''}.")
            await asyncio.sleep(300)
    except Exception as e:
        await log_collector.error(f"proxy_handler encountered a severe error while refreshing proxy pool: {e}")
        pass

async def proxy_picker(currentproxy, diderror: bool):
    """Chronologically picks a usable proxy from the proxy pool"""
    try:
        global proxyPool, logProxying
        if not enableProxying: return None
        if diderror and currentproxy is not None:
            if logProxying: await log_collector.debug(f"Removing bad proxy {currentproxy}.")
            for proxy in proxyPool:
                if proxy == currentproxy: proxyPool.remove(proxy)
        if len(proxyPool) == 0: return None
        if currentproxy is None: return proxyPool[0]
        else:
            try:
                index = proxyPool.index(currentproxy)
                next_index = (index + 1) % len(proxyPool)
                return proxyPool[next_index]
            except ValueError:
                if len(proxyPool) != 0 and diderror:
                    for proxy in proxyPool:
                        if proxy == currentproxy: proxyPool.remove(proxy)
                if len(proxyPool) == 0: return None
                return proxyPool[0]
    except Exception as e:
        await log_collector.error(f"Proxy picker fallbacking to non-proxied. Severe error: {e}")
        return None

async def validate_cookie() -> None:
    """Validates the RSEC value from config.json"""
    async with aiohttp.ClientSession(cookies={".roblosecurity": rsec}) as main_session:
        async with main_session.get("https://users.roblox.com/v1/users/authenticated") as resp:
            if resp.status == 200: await loop.create_task(token_renewal(True))
            else: await log_collector.error("Invalid ROBLOSECURITY cookie. RoWhoIs will not function properly.")

async def token_renewal(automated: bool = False) -> None:
    """Renews the X-CSRF token"""
    global x_csrf_token
    try:
        async with aiohttp.ClientSession(cookies={".roblosecurity": rsec}) as main_session:
            async with main_session.post("https://auth.roblox.com/v2/logout") as resp:
                if 'x-csrf-token' in resp.headers: x_csrf_token = resp.headers['x-csrf-token']
                else: x_csrf_token = ""
    except Exception as e:
        await log_collector.error(f"token_renewal encountered an error while updating x-csrf-token: {e}")
        pass
    if automated:
        while True:
            try:
                await asyncio.sleep(50)  # Recheck quickly to ensure we have a refreshed token before a command is ran
                await token_renewal()
            except Exception: pass

loop = asyncio.get_event_loop()

async def Roquest(method: str, node: str, endpoint: str, shard_id: int = None, failretry=False, **kwargs) -> tuple[int, Any]:
    """Performs API calls to Roblox, returns status code and json response"""
    global proxyCredentials, lastProxy, x_csrf_token
    method = method.lower()
    for retry in range(3):
        async with aiohttp.ClientSession(cookies={".roblosecurity": rsec}, headers={"x-csrf-token": x_csrf_token}) as main_session:
            try:
                proxy = await proxy_picker(lastProxy, False) # Moved here so on retry, switch proxies
                lastProxy = proxy
                logBlurb = f"{method.upper()} {node} [{proxy if proxy is not None else 'non-proxied'}] {'| ' + endpoint if endpoint != '' else endpoint}"
                if not productionMode: await log_collector.info(f"{logBlurb}", shard_id=shard_id) # PRIVACY FILTER
                try:
                    async with main_session.request(method, f"https://{node}.roblox.com/{endpoint}", proxy=proxy, proxy_auth=proxyCredentials, timeout=4, **kwargs) as resp:
                        if resp.status == 200: return resp.status, await resp.json()
                        await log_collector.warn(f"{logBlurb}: {resp.status} {('- ' + str(retry + 1) + '/3') if failretry else ''}", shard_id=shard_id)
                        if resp.status in [404, 400]: return resp.status, await resp.json() # Standard not exist, disregard retries
                        elif resp.status == 403:
                            if not failretry: return resp.status, await resp.json()
                            await token_renewal()
                        elif resp.status == 429: await asyncio.sleep(2) # Proxy changed per retry, so proxy_picker not needed here
                        if not failretry: break
                except Exception as e:
                    await proxy_picker(proxy, True)
                    await log_collector.error(f"{logBlurb}: {type(e)} |  {e if not isinstance(e, asyncio.exceptions.TimeoutError) else 'Timed out.'}", shard_id=shard_id)
            except Exception as e:
                await log_collector.error(f"{logBlurb}: Severe error: {type(e)} | {e}", shard_id=shard_id)
                raise ErrorDict.UnexpectedServerResponseError
    await log_collector.error(f"{logBlurb}: Failed after {retry + 1} attempt{'s' if retry >= 1 else ''}.", shard_id=shard_id)
    return resp.status, {"error": "Failed to retrieve data"}

async def GetFileContent(asset_id: int, version: int = None, shard_id: int = None) -> bytes:
    """Retrieves large non-json assets"""
    global proxyCredentials, lastProxy, x_csrf_token
    try:
        proxy = await proxy_picker(lastProxy, False)
        lastProxy = proxy
        await log_collector.info(f"GETFILECONTENT [{proxy if proxy is not None else 'non-proxied'}] | {asset_id}", shard_id=shard_id)
        async with aiohttp.ClientSession(cookies={".ROBLOSECURITY": rsec}, headers={"x-csrf-token": x_csrf_token}) as main_session:
            async with main_session.request("GET", f"https://assetdelivery.roblox.com/v1/asset/?id={asset_id}&version={version if version is not None else ''}", proxy=proxy, proxy_auth=proxyCredentials) as resp:
                if resp.status == 200:
                    content = await resp.read()
                    return content
                elif resp.status == 409: raise ErrorDict.MismatchedDataError  # Returns 409 if a user tries to get a game with getclothingtexture (Yes, that really happened)
                elif resp.status == 403:
                    if (await resp.json())['errors'][0]['message'] == 'Asset is not approved for the requester': raise ErrorDict.AssetNotAvailable
                elif resp.status in [404, 400]: raise ErrorDict.DoesNotExistError
                else:
                    proxy = await proxy_picker(lastProxy, True)
                    await log_collector.warn(f"GETFILECONTENT [{proxy if proxy is not None else 'non-proxied'}] | {asset_id}: {resp.status}", shard_id=shard_id)
                    raise ErrorDict.UnexpectedServerResponseError
    finally: # Hold the connection hostage until we FINISH downloading THE FILE.
        if resp: await resp.release()

async def RoliData():
    """Fetches Rolimons limited data"""
    async with aiohttp.ClientSession() as session:
        for retry in range(3):
            async with session.get("https://www.rolimons.com/itemapi/itemdetails") as resp:
                if resp.status == 200: return await resp.json()
                elif resp.status == 429:
                    await log_collector.warn(f"GET rolimons | itemdetails: {resp.status} (WAIT 5s) {retry + 1}/3")
                    await asyncio.sleep(5)
                else: await log_collector.warn(f"GET rolimons | itemdetails: {resp.status} {retry + 1}/3")
        await log_collector.error(f"GET rolimons | itemdetails: Failed after 3 attempts.")
        raise ErrorDict.UnexpectedServerResponseError

async def heartbeat() -> bool:
    """Determines if Roblox is OK by checking if the API is up, returns True if alive"""
    try:
        data = await Roquest("GET", "users", "")
        if data[0] == 200: return True
        return False
    except Exception as e:
        await log_collector.warn(f"Heartbeat error: {e}")
        return False
