import aiohttp, asyncio
from secret import RWI
from logger import AsyncLogCollector

log_collector = AsyncLogCollector("logs/Roquest.log")
lastProxy = None

def set_configs(enable_proxying:bool, proxy_urls, username:str, password):
    global enableProxying, proxyUrls, proxyCredentials, proxyPool
    enableProxying, proxyUrls, proxyPool = enable_proxying, proxy_urls, []
    if username != "": proxyCredentials = aiohttp.BasicAuth(login=username, password=password)
    else: proxyCredentials = None
    if enableProxying: loop.create_task(proxy_handler())

async def proxy_handler():
    global enableProxying, proxyUrls, proxyCredentials, proxyPool
    proxiesMessageShown = False
    while enableProxying:
        async def test_proxy(session, proxy_url):
            try:
                async with session.get("https://auth.roblox.com/", proxy=proxy_url, proxy_auth=proxyCredentials, timeout=2) as response:
                    if response.status == 200: return True
            except Exception: pass
            return False
        async with aiohttp.ClientSession() as session:
            if len(proxyUrls) <= 0 and not proxiesMessageShown: await log_collector.warn("No usable proxies found! Fallbacking to non-proxied.")
            else:
                tasks = [test_proxy(session, proxy_url) for proxy_url in proxyUrls]
                results = await asyncio.gather(*tasks)
                proxyPool = [proxy_url for proxy_url, result in zip(proxyUrls, results) if result]
                if len(proxyPool) <= 0 and not proxiesMessageShown:
                    await log_collector.warn("No usable proxies found! Fallbacking to non-proxied.")
                    proxiesMessageShown = True
                elif not proxiesMessageShown:
                    proxiesMessageShown = True
                    await log_collector.info(f"Proxy pool has {len(proxyPool)} usable IPs and RoWhoIs will proxy roquests.")
        await asyncio.sleep(300)

async def proxy_picker(currentProxy, didError:bool):
    try:
        global proxyPool
        if not enableProxying:  return None
        if didError and currentProxy != None:
            for proxy in proxyPool:
                if proxy == currentProxy: proxyPool.remove(proxy)
        if len(proxyPool) == 0:  return None
        if currentProxy is None: return proxyPool[0]
        else:
            try:
                index = proxyPool.index(currentProxy)
                next_index = (index + 1) % len(proxyPool)
                return proxyPool[next_index]
            except ValueError:
                if len(proxyPool) != 0 and didError:
                    for proxy in proxyPool:
                        if proxy == currentProxy: proxyPool.remove(proxy)
                if len(proxyPool) == 0: return None
                return proxyPool[0]
    except Exception as e:
        await log_collector.error(f"Encountered severe error while picking proxy: {e}")
        return None

loop = asyncio.get_event_loop()

async def Roquest(method:str, node:str, endpoint:str, **kwargs):
    global proxyCredentials, lastProxy
    method = method.lower()
    async with aiohttp.ClientSession(cookies={".ROBLOSECURITY": RWI.RSEC}) as main_session:
        proxy = await proxy_picker(lastProxy, False)
        lastProxy = proxy
        await log_collector.info(f"{method.upper()} {node} [{proxy if proxy != None else 'non-proxied'}] | {endpoint}")
        for retry in range(3):
            try:
                async with main_session.request(method, f"https://{node}.roblox.com/{endpoint}", proxy=proxy, proxy_auth=proxyCredentials, timeout=4, **kwargs) as resp:
                    if resp.status == 200: return resp.status, await resp.json()
                    elif resp.status in [403, 404, 400]:
                        await log_collector.warn(f"{method.upper()} {node} [{proxy if proxy != None else 'non-proxied'}] | {endpoint}: {resp.status} - {retry + 1}/3")
                        return resp.status, await resp.json()
                    elif resp.status == 429:
                        proxy = await proxy_picker(lastProxy, False)
                        lastProxy = proxy
                    else:
                        await log_collector.warn(f"{method.upper()} {node} [{proxy if proxy != None else 'non-proxied'}] | {endpoint}: Code {resp.status}. Retrying... {retry + 1}/3")
                        await asyncio.sleep(3)
            except Exception as e:  
                proxy = await proxy_picker(lastProxy, True)
                lastProxy = proxy
                await log_collector.error(f"{method.upper()} {node} [{proxy if proxy != None else 'non-proxied'}] | {endpoint}: {e if e != '' else 'connection timed out'}")
        await log_collector.error(f"{method.upper()} {node} [{proxy if proxy != None else 'non-proxied'}] | {endpoint}: Failed after 3 attempts." )
        return -1, {"error":"Failed to retrieve data."}

async def RoliData(max_retries=5, retry_interval=5):
    async with aiohttp.ClientSession(cookies={".ROBLOSECURITY": RWI.RSEC}) as session:
        for retry in range(max_retries):
            async with session.get("https://www.rolimons.com/itemapi/itemdetails") as resp:
                if resp.status == 200: return await resp.json()
                elif resp.status == 429:
                    await log_collector.warn(f"Flood limit exceeded. Waiting {retry_interval} seconds. Retrying...")
                    await asyncio.sleep(retry_interval)
                else: await log_collector.warn(f"RoliData update failed with status code {resp.status}. Retrying...")
        raise await log_collector.error(f"Failed to make a successful request to RoliData after {max_retries} retries.")

async def GetFileContent(asset_id): # This will cause issues in the future but proxying larger content seems unstable
    try:
        await log_collector.info(f'Performing GetFileContent for item: {asset_id}')
        async with aiohttp.ClientSession(cookies={".ROBLOSECURITY": RWI.RSEC}) as main_session:
            async with main_session.request("GET", f"https://assetdelivery.roblox.com/v1/asset/?id={asset_id}") as resp:
                if resp.status == 200:
                    content = await resp.read()
                    return content
                else: return False
    except Exception as e:
        await log_collector.error(f"Exception while fetching asset {asset_id}: {e}")
        return False
    finally: # Hold the connection hostage until we FINISH downloading THE FILE.
        if resp: await resp.release()