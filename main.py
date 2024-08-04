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
import logging
from logging.handlers import RotatingFileHandler
import sys
import traceback
import warnings

import aiohttp

from server import request, server

warnings.filterwarnings("ignore", category=RuntimeWarning)


if not os.path.exists('logs'):
    os.makedirs('logs')


log_handler = RotatingFileHandler('logs/main.log', maxBytes=5*1024*1024, backupCount=2)

logs = logging.getLogger()


logs.addHandler(log_handler)

if os.name != "nt":
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

for folder in ["logs", "cache", "cache/clothing", "cache/asset"]:
    if not os.path.exists(folder):
        os.makedirs(folder)

MODIFIED: bool = True
try:
    tag = subprocess.check_output(['git', 'tag', '--contains', 'HEAD']).strip()
    VERSION = tag.decode('utf-8') if tag else None
    if VERSION is None:
        raise subprocess.CalledProcessError(1, "git tag --contains HEAD")
    MODIFIED = False
except subprocess.CalledProcessError:
    try:  # Fallback, rely on short hash
        short_commit_id = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).strip()
        VERSION = short_commit_id.decode('utf-8')
    except subprocess.CalledProcessError:
        VERSION = "0"  # Assume not part of a git workspace


with open('config.json', 'r', encoding='utf-8') as configfile:
    config = json.load(configfile)
    configfile.close()

# logger.display_banner(VERSION, config['RoWhoIs']['production_mode'], MODIFIED)

for file in ["server/request.py", "server/server.py", "config.json", "utils/errors.py", "utils/gtils.py"]:  # noqa: E501
    if not os.path.exists(file):
        logs.fatal("Missing %s! RoWhoIs will not be able to initialize.", file)
        sys.exit(1)


def push_status(enabling: bool, webhook_token: str) -> None:
    """Pushes to the webhook the initialization status of RoWhoIs"""
    try:
        async def push(enabling: bool, webhook_token: str) -> None:
            async with aiohttp.ClientSession() as session:
                await session.request(
                    "POST",
                    webhook_token,
                    json={
                        "username": "RoWhoIs Status",
                        "avatar_url": "https://rowhois.com/rwi-pfp.png",
                        "embeds": [
                            {
                                "title": "RoWhoIs Status",
                                "color": 65293 if enabling else 0xFF0000,
                                "description": f"RoWhoIs is now {'online' if enabling else 'offline'}!"  # noqa: E501
                            }
                        ]
                    }
                )
        asyncio.new_event_loop().run_until_complete(push(enabling, webhook_token))
    except Exception as e:  # noqa: W0718
        logs.error("Failed to push to status webhook: %e", e)


try:
    productionMode = config['RoWhoIs']['production_mode']
    if not productionMode:
        logs.setLevel(logging.DEBUG)
    webhookToken = config['Authentication']['webhook']
    if productionMode:
        logs.warning("Currently running in production mode. Non-failing user data will be truncated.")  # noqa: E501
    else:
        logs.warning("Currently running in testing mode. All user data will be retained.")
except KeyError:
    logs.fatal("Failed to retrieve production type. RoWhoIs will not be able to initialize.")
    sys.exit(1)

if productionMode:
    push_status(True, webhookToken)


logs.info("RoWhoIs down")
if productionMode:
    push_status(False, webhookToken)
os.rename("logs/main.log", f"logs/server-{datetime.datetime.now().strftime('%Y-%m-%d-%H%M%S')}.log")  # noqa: E501
sys.exit(0)
