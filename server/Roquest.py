"""
RoWhoIs library for performing raw requests to API endpoints.
"""
import aiohttp, asyncio
from utils.logger import AsyncLogCollector
from utils import ErrorDict, typedefs
from typing import Any

log_collector = AsyncLogCollector("logs/main.log")

def initialize(config, version: str, modded: bool):
    """Sets configurations for proxying. Needs to be ran before running any other function."""
    try:
        global productionMode, globProxies, BaseUserAuth, currentProxy, poolProxies, uasString
        globProxies = typedefs.Proxies(config["Proxying"]["proxying_enabled"], config["Proxying"]["proxy_urls"], config["Proxying"]["username"], config["Proxying"]["password"], config["Proxying"]["log_proxying"])
        productionMode = config["RoWhoIs"]["production_mode"]
        BaseUserAuth = typedefs.UserAuth(config["Authentication"]["roblosecurity"], "", config["Authentication"]["api_key"])
        uasString = f"RoWhoIs-server/{version}; {'modified' if modded else 'genuine'} ({'prod-mode' if productionMode else 'testing-mode'})"
        currentProxy, poolProxies = typedefs.Proxy(None), typedefs.Proxies(globProxies.enabled, [])
        if globProxies.enabled: loop.create_task(proxy_handler())
        loop.create_task(validate_cookie())
    except KeyError: raise ErrorDict.MissingRequiredConfigs

async def proxy_handler() -> None:
    """Determines what proxies are usable by the server"""
    global poolProxies
    try:
        while globProxies.enabled:
            async def test_proxy(alivesession, proxy_url):
                try:
                    async with alivesession.post("https://auth.roblox.com/v2/logout", headers={"User-Agent": uasString}, proxy=proxy_url, proxy_auth=globProxies.auth, timeout=2) as response:
                        if response.status == 401: return True
                except Exception: pass
                return False
            async with aiohttp.ClientSession() as session:
                if len(globProxies.ips) <= 0 and globProxies.logged: await log_collector.debug("No usable proxies found! Fallbacking to non-proxied.", initiator="RoWhoIs.proxy_handler")
                else:
                    tasks = [test_proxy(session, proxy_url) for proxy_url in globProxies.ips]
                    results = await asyncio.gather(*tasks)
                    poolProxies = typedefs.Proxies(globProxies.enabled, [proxy_url for proxy_url, result in zip(globProxies.ips, results) if result])
                    if len(poolProxies.ips) <= 0 and globProxies.logged: await log_collector.debug("No usable proxies found! Fallbacking to non-proxied.", initiator="RoWhoIs.proxy_handler")
                    elif globProxies.logged: await log_collector.debug(f"Refreshed proxy pool. {len(poolProxies.ips)} usable IP{'s' if len(poolProxies.ips) >= 2 else ''}.", initiator="RoWhoIs.proxy_handler")
            await asyncio.sleep(300)
    except Exception as e:
        await log_collector.error(f"proxy_handler encountered a severe error while refreshing proxy pool: {e}", initiator="RoWhoIs.proxy_handler")
        pass

async def ret_on_prox() -> tuple[str, str]:
    """Returns list of usable proxies"""
    return poolProxies.ips

async def ret_glob_proxies() -> tuple[str, str]:
    """Returns the global proxy pool"""
    return globProxies.ips

async def proxy_picker(diderror: bool = False):
    """Chronologically picks a usable proxy from the proxy pool"""
    global poolProxies, currentProxy
    try:
        if not globProxies.enabled or len(poolProxies.ips) == 0:
            currentProxy = typedefs.Proxy(None)
            return
        if diderror and currentProxy.ip is not None:
            poolProxies.ips = [proxy for proxy in poolProxies.ips if proxy != currentProxy.ip]
            if globProxies.enabled: await log_collector.debug(f"Removing bad proxy {currentProxy.ip}.", initiator="RoWhoIs.proxy_picker")
        if len(poolProxies.ips) == 0:
            currentProxy = typedefs.Proxy(None)
            return
        index = poolProxies.ips.index(currentProxy.ip) if currentProxy.ip in poolProxies.ips else -1
        next_index = (index + 1) % len(poolProxies.ips)
        currentProxy = typedefs.Proxy(poolProxies.ips[next_index])
    except Exception as e:
        await log_collector.error(f"Proxy picker fallbacking to non-proxied. Severe error: {e}", initiator="RoWhoIs.proxy_picker")
        currentProxy = typedefs.Proxy(None)
        return

async def validate_cookie() -> None:
    """Validates the RSEC value from config.json"""
    async with aiohttp.ClientSession(cookies={".roblosecurity": BaseUserAuth.token}, headers={"User-Agent": uasString}) as main_session:
        async with main_session.get("https://users.roblox.com/v1/users/authenticated") as resp:
            if resp.status == 200: await loop.create_task(token_renewal(True))
            else: await log_collector.error("Invalid ROBLOSECURITY cookie. RoWhoIs will not function properly.", initiator="RoWhoIs.validate_cookie")

async def token_renewal(automated: bool = False) -> None:
    """Renews the X-CSRF token"""
    global BaseUserAuth
    while True:
        try:
            async with aiohttp.ClientSession(cookies={".roblosecurity": BaseUserAuth.token}) as main_session:
                async with main_session.post("https://auth.roblox.com/v2/logout", headers={"User-Agent": uasString}) as resp:
                    if 'x-csrf-token' in resp.headers: BaseUserAuth.csrf = resp.headers['x-csrf-token']
        except Exception as e:
            await log_collector.error(f"token_renewal encountered an error while updating x-csrf-token: {e}", initiator="RoWhoIs.token_renewal")
            pass
        finally:
            if automated: break
            await asyncio.sleep(50)

loop = asyncio.get_event_loop()

async def Roquest(method: str, node: str, endpoint: str, shard_id: int = None, failretry=False, bypass_proxy: bool = False, **kwargs) -> tuple[int, Any]:
    """Performs a request to the Roblox API. Returns a tuple with the status code and the response data.
    bypass_proxy will override proxying and perform an authenticated roquest"""
    for retry in range(3):
        async with aiohttp.ClientSession(cookies={".roblosecurity": BaseUserAuth.token} if bypass_proxy else {}, headers={"x-csrf-token": BaseUserAuth.csrf, 'User-Agent': uasString, 'x-api-key': BaseUserAuth.api_key} if bypass_proxy else {'User-Agent': uasString}) as main_session:
            try:
                if not bypass_proxy: await proxy_picker()
                logBlurb = f"{currentProxy.ip + ';' if currentProxy.ip is not None and not bypass_proxy else 'non-proxied;'}  {method.upper()} {node} {'| ' + endpoint if endpoint != '' else endpoint}"
                if not productionMode: await log_collector.info(f"{logBlurb}", initiator="RoWhoIs.Roquest", shard_id=shard_id) # PRIVACY FILTER
                try:
                    async with main_session.request(method.lower(), f"https://{node}.roblox.com/{endpoint}", timeout=4, proxy=currentProxy.ip if not bypass_proxy else None, proxy_auth=globProxies.auth if not bypass_proxy else None, **kwargs) as resp:
                        if resp.status == 200: return resp.status, await resp.json()
                        await log_collector.warn(f"{logBlurb}: {resp.status} {('- ' + str(retry + 1) + '/3')}", initiator="RoWhoIs.Roquest", shard_id=shard_id)
                        if resp.status in [404, 400]: return resp.status, await resp.json() # Standard not exist, disregard retries
                        elif resp.status == 403:
                            if not failretry: return resp.status, await resp.json()
                            await token_renewal()
                        if not failretry and (resp.status not in [429, 500]): break
                except Exception as e:
                    await proxy_picker(True)
                    await log_collector.error(f"{logBlurb}: {type(e)} |  {e if not isinstance(e, asyncio.exceptions.TimeoutError) else 'Timed out.'}", initiator="RoWhoIs.Roquest", shard_id=shard_id)
            except Exception as e:
                await log_collector.error(f"{logBlurb}: Severe error: {type(e)} | {e}", initiator="RoWhoIs.Roquest", shard_id=shard_id)
                raise ErrorDict.UnexpectedServerResponseError
    await log_collector.error(f"{logBlurb}: Failed after {retry + 1} attempt{'s' if retry >= 1 else ''}.", initiator="RoWhoIs.Roquest", shard_id=shard_id)
    return resp.status, {"error": "Failed to retrieve data"}

async def GetFileContent(asset_id: int, version: int = None, shard_id: int = None) -> bytes:
    """Retrieves large non-json assets"""
    try:
        await proxy_picker()
        logBlurb = f"{currentProxy.ip + ';' if currentProxy.ip is not None else 'non-proxied;'} GETFILECONTENT  | {asset_id}"
        if not productionMode: await log_collector.info(logBlurb, initiator="RoWhoIs.GetFileContent", shard_id=shard_id)
        async with aiohttp.ClientSession() as main_session:
            async with main_session.request("GET", f"https://assetdelivery.roblox.com/v1/asset/?id={asset_id}&version={version if version is not None else ''}", headers={'User-Agent': uasString}, proxy=currentProxy.ip, proxy_auth=globProxies.auth) as resp:
                if resp.status == 200:
                    content = await resp.read()
                    return content
                elif resp.status == 409: raise ErrorDict.MismatchedDataError  # Returns 409 if a user tries to get a game with getclothingtexture (Yes, that really happened)
                elif resp.status == 403:
                    if (await resp.json())['errors'][0]['message'] == 'Asset is not approved for the requester': raise ErrorDict.AssetNotAvailable
                elif resp.status in [404, 400]: raise ErrorDict.DoesNotExistError
                else:
                    await log_collector.warn(f"{logBlurb}: {resp.status}", initiator="RoWhoIs.GetFileContent", shard_id=shard_id)
                    raise ErrorDict.UnexpectedServerResponseError
    finally: # Hold the connection hostage until we FINISH downloading THE FILE.
        if resp: await resp.release()

async def RoliData():
    """Fetches Rolimons limited data"""
    async with aiohttp.ClientSession() as session:
        for retry in range(3):
            async with session.get("https://www.rolimons.com/itemapi/itemdetails", headers={'User-Agent': uasString}) as resp:
                if resp.status == 200: return await resp.json()
                elif resp.status == 429:
                    await log_collector.warn(f"GET rolimons | itemdetails: {resp.status} (WAIT 5s) {retry + 1}/3", initiator="RoWhoIs.RoliData")
                    await asyncio.sleep(5)
                else: await log_collector.warn(f"GET rolimons | itemdetails: {resp.status} {retry + 1}/3", initiator="RoWhoIs.RoliData")
        await log_collector.error(f"GET rolimons | itemdetails: Failed after 3 attempts.", initiator="RoWhoIs.RoliData")
        raise ErrorDict.UnexpectedServerResponseError

async def heartbeat() -> bool:
    """Determines if Roblox is OK by checking if the API is up, returns True if alive"""
    try:
        data = await Roquest("GET", "premiumfeatures", "v1/users/1/validate-membership", bypass_proxy=True)
        if data[0] == 200: return True
        if data[0] == 403: return None
        return False
    except Exception as e:
        await log_collector.warn(f"Heartbeat error: {e}", initiator="RoWhoIs.heartbeat")
        return False
