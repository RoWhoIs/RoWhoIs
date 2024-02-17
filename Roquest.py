import aiohttp, asyncio
from secret import RWI
from logger import AsyncLogCollector

log_collector = AsyncLogCollector("logs/Roquest.log")
lastProxy, x_csrf_token = None, None

def set_configs(enable_proxying:bool, proxy_urls, username:str, password, log_proxying:bool):
    global enableProxying, proxyUrls, proxyCredentials, proxyPool, logProxying
    enableProxying, proxyUrls, proxyPool, logProxying = enable_proxying, proxy_urls, [], log_proxying
    if username != "": proxyCredentials = aiohttp.BasicAuth(login=username, password=password)
    else: proxyCredentials = None
    if enableProxying: loop.create_task(proxy_handler())
    loop.create_task(token_renewal())

async def proxy_handler():
    global enableProxying, proxyUrls, proxyCredentials, proxyPool, logProxying
    try:
        while enableProxying:
            async def test_proxy(session, proxy_url):
                try:
                    async with session.get("https://auth.roblox.com/", proxy=proxy_url, proxy_auth=proxyCredentials, timeout=2) as response:
                        if response.status == 200: return True
                except Exception: pass
                return False
            async with aiohttp.ClientSession() as session:
                if len(proxyUrls) <= 0 and logProxying: await log_collector.warn("No usable proxies found! Fallbacking to non-proxied.")
                else:
                    tasks = [test_proxy(session, proxy_url) for proxy_url in proxyUrls]
                    results = await asyncio.gather(*tasks)
                    proxyPool = [proxy_url for proxy_url, result in zip(proxyUrls, results) if result]
                    if len(proxyPool) <= 0 and logProxying: await log_collector.warn("No usable proxies found! Fallbacking to non-proxied.")
                    elif logProxying: await log_collector.info(f"Refreshed proxy pool. {len(proxyPool)} usable IPs.")
            await asyncio.sleep(300)
    except Exception as e:
        await log_collector.error(f"proxy_handler encountered a severe error while refreshing proxy pool: {e}")
        pass

async def proxy_picker(currentProxy, didError:bool):
    try:
        global proxyPool, logProxying
        if not enableProxying:  return None
        if didError and currentProxy != None:
            if logProxying: await log_collector.warn(f"Removing bad proxy {currentProxy}.")
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
        await log_collector.error(f"Proxy picker fallbacking to non-proxied. Severe error: {e}")
        return None

async def token_renewal():
    global x_csrf_token
    while True:
        try:
            async with aiohttp.ClientSession(cookies={".roblosecurity": RWI.RSEC}) as main_session:
                async with main_session.post("https://auth.roblox.com/v2/logout") as resp:
                    if 'x-csrf-token' in resp.headers: x_csrf_token = resp.headers['x-csrf-token']
                    else: x_csrf_token = None
            await asyncio.sleep(250)
        except Exception as e:
            await log_collector.error(f"token_renewal encountered an error while updating x-csrf-token: {e}")
            pass

loop = asyncio.get_event_loop()

async def Roquest(method:str, node:str, endpoint:str, **kwargs):
    global proxyCredentials, lastProxy, x_csrf_token
    method = method.lower()
    async with aiohttp.ClientSession(cookies={".roblosecurity": RWI.RSEC}, headers={"x-csrf-token":x_csrf_token}) as main_session:
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
                        await log_collector.warn(f"{method.upper()} {node} [{proxy if proxy != None else 'non-proxied'}] | {endpoint}: {resp.status}. Retrying... {retry + 1}/3")
                        await asyncio.sleep(3)
            except Exception as e:  
                proxy = await proxy_picker(proxy, True)
                await log_collector.error(f"{method.upper()} {node} [{proxy if proxy != None else 'non-proxied'}] | {endpoint}: {e if e != '' else 'Connection timed out.'}")
        await log_collector.error(f"{method.upper()} {node} [{proxy if proxy != None else 'non-proxied'}] | {endpoint}: Failed after 3 attempts." )
        return -1, {"error":"Failed to retrieve data."}

async def RoliData():
    async with aiohttp.ClientSession(cookies={".ROBLOSECURITY": RWI.RSEC}) as session:
        for retry in range(3):
            async with session.get("https://www.rolimons.com/itemapi/itemdetails") as resp:
                if resp.status == 200: return await resp.json()
                elif resp.status == 429:
                    await log_collector.warn(f"GET rolimons | temdetails: {resp.status} (WAIT 5s) {retry + 1}/3")
                    await asyncio.sleep(5)
                else: await log_collector.warn(f"GET rolimons | temdetails: {resp.status} {retry + 1}/3")
        raise await log_collector.error(f"GET rolimons | temdetails: Failed after 3 attempts.")

async def GetFileContent(asset_id):
    global proxyCredentials, lastProxy, x_csrf_token
    try:
        proxy = await proxy_picker(lastProxy, False)
        lastProxy = proxy
        await log_collector.info(f"GETFILECONTENT [{proxy if proxy != None else 'non-proxied'}] | {asset_id}")
        async with aiohttp.ClientSession(cookies={".ROBLOSECURITY": RWI.RSEC}, headers={"x-csrf-token":x_csrf_token}) as main_session:
            async with main_session.request("GET", f"https://assetdelivery.roblox.com/v1/asset/?id={asset_id}", proxy=proxy, proxy_auth=proxyCredentials) as resp:
                if resp.status == 200:
                    content = await resp.read()
                    return content
                else: 
                    await log_collector.warn(f"GETFILECONTENT [{proxy if proxy != None else 'non-proxied'}] | {asset_id}: {resp.status}")
                    return False
    except Exception as e:
        await proxy_picker(proxy, True)
        await log_collector.error(f"GETFILECONTENT [{proxy if proxy != None else 'non-proxied'}] | {asset_id}: {e}")
        return False
    finally: # Hold the connection hostage until we FINISH downloading THE FILE.
        if resp: await resp.release()
