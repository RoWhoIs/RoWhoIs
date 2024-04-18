"""
AsyncLogger, an asynchronous logging utility
Forked from https://github.com/aut-mn/AsyncLogger
Modified for RoWhoIs
"""
import asyncio, aiofiles
from datetime import datetime

class AsyncLogCollector:
    def __init__(self, filename):
        if not filename: raise ValueError("Filename cannot be None or empty.")
        self.filename = filename
        self.log_format = "%(timestamp)s [%(level)s] %(message)s"
        self.log_queue = asyncio.Queue()
        self.log_levels = {
            'D': '\033[1;90mD\033[22m',
            'I': '\033[1;32mI\033[22m',
            'W': '\033[1;33mW\033[22m',
            'E': '\033[1;31mE\033[22m',
            'F': '\033[1;31;1mF\033[22m',
            'C': '\033[1;31;1;4mC\033[22m'
        }
    async def log(self, level, message, initiator: str = None, shard_id: int = None):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]
        colored_level = self.log_levels.get(level.upper(), level.upper())
        if shard_id is None:
            print(f"{colored_level} {timestamp} \033[1m{initiator if initiator else 'unknowninitiator'}{'.' + shard_id if shard_id is not None else ''}\033[22m: {message}")
            async with aiofiles.open(self.filename, mode='a') as file:
                await file.write(f"{level.upper()} {timestamp} {initiator} {'SH' + str(shard_id) if shard_id is not None else ''}: {message}\n")
    async def debug(self, message, shard_id: int = None, initiator: str = None): await self.log('D', message, initiator, shard_id)
    async def info(self, message, shard_id: int = None, initiator: str = None): await self.log('I', message, initiator, shard_id)
    async def warn(self, message, shard_id: int = None, initiator: str = None): await self.log('W', message, initiator, shard_id)
    async def error(self, message, shard_id: int = None, initiator: str = None): await self.log('E', message, initiator, shard_id)
    async def fatal(self, message, shard_id: int = None, initiator: str = None): await self.log('F', message, initiator, shard_id)
    async def critical(self, message, shard_id: int = None, initiator: str = None): await self.log('C', message, initiator, shard_id)
    def get_colored_timestamp(self): return '\033[90m' + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '\033[0m'
    def get_timestamp(self): return datetime.now().strftime('%Y-%m-%d %H:%M:%S')