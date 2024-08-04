"""
RoWhoIs
The most advanced Discord-based Roblox lookup utility

CONTRIBUTORS:
https://github.com/aut-mn
"""
import asyncio
import datetime
import json
import os
import subprocess
import sys
import traceback
import warnings

import aiohttp

from utils import errors, logger
from server import request, server

warnings.filterwarnings("ignore", category=RuntimeWarning)

if os.name != "nt":
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

for folder in ["logs", "cache", "cache/clothing", "cache/asset"]:
    if not os.path.exists(folder):
        os.makedirs(folder)


try:
    tag = subprocess.check_output(['git', 'tag', '--contains', 'HEAD']).strip()
    VERSION = tag.decode('utf-8') if tag else None
    if VERSION is None:
        raise subprocess.CalledProcessError(1, "git tag --contains HEAD")
except subprocess.CalledProcessError:
    try:  # Fallback, rely on short hash
        short_commit_id = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).strip()
        VERSION = short_commit_id.decode('utf-8')
    except subprocess.CalledProcessError:
        VERSION = "0"  # Assume not part of a git workspace


with open('config.json', 'r', encoding='utf-8') as configfile:
    config = json.load(configfile)
    configfile.close()

logger.display_banner(VERSION, config['RoWhoIs']['production_mode'], MODIFIED)

for file in ["server/request.py", "server/server.py", "config.json",
    "utils/errors.py", "utils/gtils.py"]:
    if not os.path.exists(file):
        logs.fatal(f"Missing {file}! RoWhoIs will not be able to initialize.")
        sys.exit(1)


def push_status(enabling: bool, webhook_token: str) -> None:
    """Pushes to the webhook the initialization status of RoWhoIs"""
    try:
        async def push(enabling: bool, webhook_token: str) -> None:
            async with aiohttp.ClientSession() as session:
                await session.request("POST", webhook_token, json={"username": "RoWhoIs Status",
                    "avatar_url": "https://rowhois.com//rwi-pfp.png", "embeds":
                        [{"title": "RoWhoIs Status", "color": 65293 if enabling else 0xFF0000,
                            "description": f"RoWhoIs is now {'online' if enabling else 'offline'}!"}]})
        asyncio.new_event_loop().run_until_complete(push(enabling, webhook_token))  # noqa: E501
    except Exception as e:  # noqa: W0718
        logs.error(f"Failed to push to status webhook: {e}")


try:
    productionMode = config['RoWhoIs']['production_mode']
    webhookToken = config['Authentication']['webhook']
    if productionMode:
        logs.warn("Currently running in production mode. Non-failing user data will be truncated.")  # noqa: E501
    else:
        logs.warn("Currently running in testing mode. All user data will be retained.")  # noqa: E501
except KeyError:
    logs.fatal("Failed to retrieve production type. RoWhoIs will not be able to initialize.")  # noqa: E501
    sys.exit(1)
if productionMode:
    push_status(True, webhookToken)
for i in range(5):  # Rerun server in event of a crash
    try:
        request.initialize(config, VERSION, MODIFIED)
        if server.run(VERSION) is True:
            break
    except KeyboardInterrupt:
        break
    except asyncio.exceptions.CancelledError:
        break
    except RuntimeError:
        pass  # Occurs when exited before fully initialized
    except errors.MissingRequiredConfigs:
        logs.fatal("Missing or malformed configuration options detected!")  # noqa: E501
    except Exception as e:  # noqa: W0718
        logs.fatal(f"A fatal error occurred during runtime: {type(e)} | {traceback.format_exc()}")  # noqa: E501
    if i < 4:
        logs.warn("Server crash detected. Restarting server...")

logs.info("RoWhoIs down")
if productionMode:
    push_status(False, webhookToken)
os.rename("logs/main.log", f"logs/server-{datetime.datetime.now().strftime('%Y-%m-%d-%H%M%S')}.log")  # noqa: E501
sys.exit(0)
