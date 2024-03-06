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
        self.log_levels = {'DEBUG': '\033[90mDEBUG\033[0m', 'INFO': '\033[32mINFO\033[0m', 'WARN': '\033[33mWARN\033[0m', 'ERROR': '\033[31mERROR\033[0m', 'FATAL': '\033[31;1mFATAL\033[0m', 'CRITICAL': '\033[31;1;4mCRIT\033[0m'}
    async def log(self, level, message, shard_id: int = None):
        timestamp = self.get_colored_timestamp()
        if shard_id is None: print(self.log_format % {'timestamp': timestamp, 'level': self.log_levels.get(level, level), 'message': message})
        else: print(self.log_format % {'timestamp': timestamp, 'level': self.log_levels.get(level, level), 'message': f"[\033[94mSH{shard_id}\033[0m] {message}"})
        async with aiofiles.open(self.filename, mode='a') as file:
            if shard_id is None: await file.write(self.log_format % {'timestamp': self.get_timestamp(), 'level': level, 'message': message} + '\n')
            else: await file.write(self.log_format % {'timestamp': self.get_timestamp(), 'level': level, 'message': f"[SH{shard_id}] {message}"} + '\n')
    async def debug(self, message, shard_id: int = None): await self.log('DEBUG', message, shard_id)
    async def info(self, message, shard_id: int = None): await self.log('INFO', message, shard_id)
    async def warn(self, message, shard_id: int = None): await self.log('WARN', message, shard_id)
    async def error(self, message, shard_id: int = None): await self.log('ERROR', message, shard_id)
    async def fatal(self, message, shard_id: int = None): await self.log('FATAL', message, shard_id)
    async def critical(self, message, shard_id: int = None): await self.log('CRITICAL', message, shard_id)
    def get_colored_timestamp(self): return '\033[90m' + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '\033[0m'
    def get_timestamp(self): return datetime.now().strftime('%Y-%m-%d %H:%M:%S')