import asyncio, subprocess, datetime, json, os, aiohttp, traceback

if not os.path.exists("utils/logger.py"):
    print("Missing utils/logger.py! RoWhoIs will not be able to initialize.")
    exit(1)
from utils.logger import AsyncLogCollector

for folder in ["logs", "cache", "cache/clothing"]:
    if not os.path.exists(folder): os.makedirs(folder)

logCollector = AsyncLogCollector("logs/main.log")

def sync_logging(errorlevel: str, errorcontent: str) -> None:
    """Allows for synchronous logging using https://github.com/aut-mn/AsyncLogger"""
    log_functions = {"fatal": logCollector.fatal, "error": logCollector.error, "warn": logCollector.warn, "info": logCollector.info}
    asyncio.new_event_loop().run_until_complete(log_functions[errorlevel](errorcontent))

try:
    tag = subprocess.check_output(['git', 'tag', '--contains', 'HEAD']).strip()
    version = tag.decode('utf-8') if tag else None
    if version is None: raise subprocess.CalledProcessError(1, "git tag --contains HEAD")
except subprocess.CalledProcessError:
    try: # Fallback, rely on short hash
        short_commit_id = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).strip()
        version = short_commit_id.decode('utf-8')
    except subprocess.CalledProcessError: version = "0"  # Assume not part of a git workspace

sync_logging("info", f"Initializing RoWhoIs on version {version}...")

for file in ["server/Roquest.py", "server/RoWhoIs.py", "config.json", "utils/ErrorDict.py"]:
    if not os.path.exists(file):
        sync_logging("fatal", f"Missing {file}! RoWhoIs will not be able to initialize.")
        exit(1)

with open('config.json', 'r') as configfile:
    config = json.load(configfile)
    configfile.close()

def push_status(enabling: bool, webhook_token: str) -> None:
    """Pushes to the webhook the initialization status of RoWhoIs"""
    try:
        async def push(enabling: bool, webhook_token: str) -> None:
            async with aiohttp.ClientSession() as session: await session.request("POST", webhook_token, json={"username": "RoWhoIs status", "avatar_url": "https://www.robloxians.com/resources/rwi-pfp.png", "embeds": [{"title": "RoWhoIs Status", "color": 65293 if enabling else 0xFF0000, "description": f"RoWhoIs is now {'online' if enabling else 'offline'}!"}]})
        asyncio.new_event_loop().run_until_complete(push(enabling, webhook_token))
    except Exception as e: sync_logging("error", f"Failed to push to status webhook: {e}")

try:
    from utils import ErrorDict
    productionMode = config['RoWhoIs']['production_mode']
    webhookToken = config['Authentication']['webhook']
    if productionMode: sync_logging("warn", "Currently running in production mode.")
    else: sync_logging("warn", "Currently running in testing mode.")
except KeyError:
    sync_logging("fatal", "Failed to retrieve production type. RoWhoIs will not be able to initialize.")
    exit(1)
for i in range(5): # Rerun server in event of a crash
    try:
        from server import Roquest, RoWhoIs
        if productionMode: push_status(True, webhookToken)
        Roquest.initialize(config)
        if RoWhoIs.run(productionMode, version, config) is True: break
    except RuntimeError: pass  # Occurs when exited before fully initialized
    except ErrorDict.MissingRequiredConfigs: sync_logging("fatal", f"Missing or malformed configuration options detected!")
    except Exception as e:
        sync_logging("fatal", f"A fatal error occurred during runtime: {type(e)} | STACKTRACE: {''.join(traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__))}")
        if i < 4: sync_logging("warn", f"Server crash detected. Restarting server...")

if productionMode: push_status(False, webhookToken)
os.rename("logs/main.log", f"logs/server-{datetime.datetime.now().strftime('%Y-%m-%d-%H%M%S')}.log")
exit(0)
