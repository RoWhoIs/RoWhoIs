"""
RoWhoIs
The most advanced Discord-based Roblox lookup utility

CONTRIBUTORS:
https://github.com/aut-mn
"""
import asyncio, subprocess, datetime, json, os, aiohttp, traceback, warnings
from utils import logger
warnings.filterwarnings("ignore", category=RuntimeWarning)

if os.name != "nt":
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
setattr(asyncio.sslproto._SSLProtocolTransport, "_start_tls_compatible", True)
for folder in ["logs", "cache", "cache/clothing", "cache/asset"]:
    if not os.path.exists(folder): os.makedirs(folder)

logCollector, modified = logger.AsyncLogCollector("logs/main.log"), True

def sync_logging(errorlevel: str, errorcontent: str) -> None:
    """Allows for synchronous logging using https://github.com/aut-mn/AsyncLogger"""
    log_functions = {"fatal": lambda: logCollector.fatal(errorcontent, initiator="RoWhoIs.main"), "error": lambda: logCollector.error(errorcontent, initiator="RoWhoIs.main"), "warn": lambda: logCollector.warn(errorcontent, initiator="RoWhoIs.main"), "info": lambda: logCollector.info(errorcontent, initiator="RoWhoIs.main")}
    asyncio.new_event_loop().run_until_complete(log_functions[errorlevel]())

try:
    tag = subprocess.check_output(['git', 'tag', '--contains', 'HEAD']).strip()
    version = tag.decode('utf-8') if tag else None
    if version is None: raise subprocess.CalledProcessError(1, "git tag --contains HEAD")
    else: modified = False
except subprocess.CalledProcessError:
    try: # Fallback, rely on short hash
        short_commit_id = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).strip()
        version = short_commit_id.decode('utf-8')
    except subprocess.CalledProcessError: version = "0"  # Assume not part of a git workspace

with open('config.json', 'r') as configfile:
    config = json.load(configfile)
    configfile.close()

logger.display_banner(version, config['RoWhoIs']['production_mode'], modified)

for file in ["server/Roquest.py", "server/RoWhoIs.py", "config.json", "utils/ErrorDict.py", "utils/gUtils.py"]:
    if not os.path.exists(file):
        sync_logging("fatal", f"Missing {file}! RoWhoIs will not be able to initialize.")
        exit(1)


def push_status(enabling: bool, webhook_token: str) -> None:
    """Pushes to the webhook the initialization status of RoWhoIs"""
    try:
        async def push(enabling: bool, webhook_token: str) -> None:
            async with aiohttp.ClientSession() as session: await session.request("POST", webhook_token, json={"username": "RoWhoIs Status", "avatar_url": "https://rowhois.com//rwi-pfp.png", "embeds": [{"title": "RoWhoIs Status", "color": 65293 if enabling else 0xFF0000, "description": f"RoWhoIs is now {'online' if enabling else 'offline'}!"}]})
        asyncio.new_event_loop().run_until_complete(push(enabling, webhook_token))
    except Exception as e: sync_logging("error", f"Failed to push to status webhook: {e}")

try:
    from utils import ErrorDict
    productionMode = config['RoWhoIs']['production_mode']
    webhookToken = config['Authentication']['webhook']
    if productionMode: sync_logging("warn", "Currently running in production mode. Non-failing user data will be truncated.")
    else: sync_logging("warn", "Currently running in testing mode. All user data will be retained.")
except KeyError:
    sync_logging("fatal", "Failed to retrieve production type. RoWhoIs will not be able to initialize.")
    exit(1)
if productionMode: push_status(True, webhookToken)
for i in range(5): # Rerun server in event of a crash
    try:
        from server import Roquest, RoWhoIs
        Roquest.initialize(config, version, modified)
        if RoWhoIs.run(version) is True: break
    except KeyboardInterrupt: break
    except asyncio.exceptions.CancelledError: break
    except RuntimeError: pass  # Occurs when exited before fully initialized
    except ErrorDict.MissingRequiredConfigs: sync_logging("fatal", f"Missing or malformed configuration options detected!")
    except Exception as e:
        sync_logging("fatal", f"A fatal error occurred during runtime: {type(e)} | {traceback.format_exc()}")
    if i < 4: sync_logging("warn", f"Server crash detected. Restarting server...")

sync_logging("info", "RoWhoIs down")
if productionMode: push_status(False, webhookToken)
os.rename("logs/main.log", f"logs/server-{datetime.datetime.now().strftime('%Y-%m-%d-%H%M%S')}.log")
exit(0)
