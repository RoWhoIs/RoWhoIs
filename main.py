import asyncio, subprocess, datetime, json, os
from utils import ErrorDict

if not os.path.exists("utils/logger.py"):
    print("Missing logger.py! RoWhoIs will not be able to initialize.")
    exit(-1)
from utils.logger import AsyncLogCollector

for folder in ["logs", "cache", "cache/clothing"]:
    if not os.path.exists(folder): os.makedirs(folder)

logCollector = AsyncLogCollector("logs/main.log")

def sync_logging(errorlevel: str, errorcontent: str) -> None:
    """Allows for synchronous logging using https://github.com/aut-mn/AsyncLogger"""
    log_functions = {"fatal": logCollector.fatal, "error": logCollector.error, "warn": logCollector.warn, "info": logCollector.info}
    asyncio.new_event_loop().run_until_complete(log_functions[errorlevel](errorcontent))

try:
    short_commit_id = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).strip()
    shortHash = short_commit_id.decode('utf-8')
except subprocess.CalledProcessError: shortHash = 0 # Assume not part of a git workspace

sync_logging("info", f"Initializing RoWhoIs on version {shortHash}...")

for file in ["server/Roquest.py", "server/RoWhoIs.py", "config.json"]:
    if not os.path.exists(file):
        sync_logging("fatal", f"Missing {file}! RoWhoIs will not be able to initialize.")
        exit(-1)

with open('config.json', 'r') as configfile:
    config = json.load(configfile)
    configfile.close()
try:
    productionMode = config['RoWhoIs']['production_mode']
    if productionMode: sync_logging("warn", "Currently running in production mode.")
    else: sync_logging("warn", "Currently running in testing mode.")
except KeyError:
    sync_logging("fatal", "Failed to retrieve production type. RoWhoIs will not be able to initialize.")
    exit(-1)
try:
    from server import Roquest, RoWhoIs
    Roquest.initialize(config)
    RoWhoIs.run(productionMode, shortHash, config)
except RuntimeError: pass  # Occurs when exited before fully initialized
except ErrorDict.MissingRequiredConfigs: sync_logging("fatal", f"Missing or malformed configuration options detected!")
except Exception as e: sync_logging("fatal", f"A fatal error occurred during runtime: {e}")

os.rename("logs/main.log", f"logs/server-{datetime.datetime.now().strftime('%Y-%m-%d-%H%M%S')}.log")
exit(1)
