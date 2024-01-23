import random, json
import aiohttp, asyncio
from secret import RWI
from logger import AsyncLogCollector

log_collector = AsyncLogCollector("logs/Roquest.log")
x_csrf_token = None
proxy_urls, available_proxies = [], []

async def load_config():
    global log_token_failures, proxy_urls, proxy_pw, proxy_us, enable_proxying, proxy_auth_required
    message_shown = False
    while True:
        try:
            with open('config.json', 'r') as file: config = json.load(file)
            log_token_failures = config.get("Roquest", {}).get("log_token_failures", False)
            enable_proxying = config.get("Proxy", {}).get("enable_proxying", False)
            if enable_proxying:
                await log_collector.info("In config.json: enable_proxying set to True. Roquests will be proxied.")
                proxy_urls.extend([id for module_data in config.values() if 'proxy_urls' in module_data for id in module_data['proxy_urls']])
                proxy_pw = config.get("Proxy", {}).get("password", False)
                proxy_us = config.get("Proxy", {}).get("username", False)
                if proxy_us and proxy_pw == "": proxy_auth_required = False
                else: proxy_auth_required = True
            elif not message_shown: await log_collector.info("In config.json: enable_proxying set to False. Roquests will not be proxied.")
            if not log_token_failures and not message_shown: await log_collector.info("In config.json: log_token_failures set to False. X-CSRF-TOKEN calls will not be logged.")
            message_shown = True
            await asyncio.sleep(3600)
        except Exception as e:
            await log_collector.error(f"Failed to update Roquest configuration data: {e}")
            await asyncio.sleep(10)

async def TestProxies():
    global available_proxies
    no_proxies_message_shown = False
    while enable_proxying:
        if proxy_auth_required: proxy_auth = aiohttp.BasicAuth(proxy_us, proxy_pw)
        else: proxy_auth = None
        async def test_proxy(session, proxy_url):
            try:
                async with session.get("https://auth.roblox.com/", proxy=proxy_url, proxy_auth=proxy_auth, timeout=10) as response:
                    if response.status == 200: return True
            except Exception as e: pass
            return False
        async with aiohttp.ClientSession() as session:
            tasks = [test_proxy(session, proxy_url) for proxy_url in proxy_urls]
            results = await asyncio.gather(*tasks)
            available_proxies = [proxy_url for proxy_url, result in zip(proxy_urls, results) if result]
            if len(available_proxies) <= 0 and not no_proxies_message_shown:
                await log_collector.warn("No usable proxies found! Fallbacking to non-proxied.")
                no_proxies_message_shown = True
        await asyncio.sleep(600)

async def TokenRenew():
    global RoliData
    while True:
        try:
            if log_token_failures: await log_collector.info('Renewing X-CSRF-TOKEN')
            async with aiohttp.ClientSession(cookies={".ROBLOSECURITY": RWI.RSEC}) as session:
                async with session.get('https://users.roblox.com/v1/users/authenticated') as resp:
                    if resp.status == 200:
                        renew_token = resp.headers.get('x-csrf-token')
                        if renew_token is None and log_token_failures: await log_collector.error("Failed to get X-CSRF token. X-CSRF-TOKEN not found in headers")
                        else:
                            x_csrf_token = renew_token
                            if log_token_failures: await log_collector.info('Successfully renewed X-CSRF-TOKEN')
                    elif log_token_failures: await log_collector.error(f"Failed to get X-CSRF-TOKEN. Status code: {resp.status}")
                    await asyncio.sleep(180)
        except Exception as e:
            if log_token_failures: await log_collector.error(f"An unexpected error occurred during X-CSRF-TOKEN renewal: {e}")
            await asyncio.sleep(10)

loop = asyncio.get_event_loop()
loop.create_task(load_config())
loop.create_task(TestProxies())
loop.create_task(TokenRenew())

async def Roquest(method, url, max_retries=3, retry_interval=2, **kwargs):
    method = method.lower()
    headers = {"x-csrf-token": f"{x_csrf_token}"}
    if enable_proxying and len(available_proxies) >= 1: 
        proxy = f"http://{available_proxies[random.randint(0, len(available_proxies))]}"
        await log_collector.info(f"Setting proxy to: {proxy}")
        if proxy_auth_required: proxy_auth = aiohttp.BasicAuth(proxy_us, proxy_pw)
        else: proxy_auth = None
    else: proxy, proxy_auth = None, None
    async with aiohttp.ClientSession(cookies={".ROBLOSECURITY": RWI.RSEC}) as main_session:
        await log_collector.info(f'Performing Roquest with method {method} to {url}')
        for retry in range(max_retries):
            try:
                async with main_session.request(method, url, headers=headers, proxy=proxy, proxy_auth=proxy_auth, **kwargs) as resp:
                    if resp.status == 200: return await resp.json()
                    elif resp.status in [403, 404, 400]:
                        await log_collector.warn(f"Failed to perform Roquest with method {method} to {url}: Got status code {resp.status}")
                        return resp.status
                    else:
                        await log_collector.warn(f"Roquest to {url} with method {method} failed with status code {resp.status}. Retrying...")
                        await asyncio.sleep(retry_interval)
            except Exception as e:
                await log_collector.error(f"An error occurred during the request: {e}")
                if enable_proxying and len(available_proxies) >= 1: # Switch proxies in case it was a bad proxy
                    proxy = f"http://{available_proxies[random.randint(0, len(available_proxies))]}"
                    await log_collector.info(f"Switching proxies to: {proxy}")
        await log_collector.error(f"Failed to make a successful Roquest after {max_retries} retries to {url} ({method})")
        return -1

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

async def GetFileContent(asset_id):
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