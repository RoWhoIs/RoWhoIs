"""
AsyncLogger, an asynchronous logging utility
Forked from https://github.com/aut-mn/AsyncLogger
Modified for RoWhoIs
"""
import asyncio, aiofiles
from datetime import datetime

COLOR_CODES = {"%{blue}": "\033[34m", "%{clear}": "\033[0m", "%{bold}": "\033[1m", "%{grey}": "\033[90m", "%{black}": "\033[30m", "%{red}": "\033[31m", "%{green}": "\033[32m", "%{yellow}": "\033[33m", "%{magenta}": "\033[35m", "%{cyan}": "\033[36m",  "%{white}": "\033[37m",  "%{darkgrey}": "\033[90m" }
class AsyncLogCollector:
    def __init__(self, filename):
        if not filename: raise ValueError("Filename cannot be None or empty.")
        self.filename = filename
        self.log_format = "%(timestamp)s [%(level)s] %(message)s"
        self.log_queue = asyncio.Queue()
        self.log_levels = {'D': '\033[1;90mD\033[22m', 'I': '\033[1;32mI\033[22m', 'W': '\033[1;33mW\033[22m', 'E': '\033[1;31mE\033[22m', 'F': '\033[1;31;1mF\033[22m', 'C': '\033[1;31;1;4mC\033[22m'}
    async def log(self, level, message, initiator: str = None, shard_id: int = None):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]
        colored_level = self.log_levels.get(level.upper(), level.upper())
        print(f"{colored_level} {timestamp} \033[1m{initiator if initiator else 'unknowninitiator'}{'.' + str(shard_id) if shard_id is not None else ''}\033[22m: {message}")
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

def display_banner(version: str, production_mode: bool, modified: bool):
    try:
        with open('utils/banner.txt', mode='r') as file:
            lines = file.readlines()
            foreground_color, background_color = None, None
            for i, line in enumerate(lines):
                if '%{clear}' in line:
                    before_clear, after_clear = line.split('%{clear}', 1)
                    before_clear = ''.join([f'{background_color}{char}\033[0m' if char != '$' and background_color is not None else char for char in before_clear])
                    line = before_clear + after_clear
                else: line = ''.join([f'{background_color}{char}\033[0m' if char != '$' and background_color is not None else char for char in line])
                for code, color in COLOR_CODES.items():
                    if code in line:
                        if i == 0: foreground_color, line = color, ''
                        elif i == 1: background_color, line = color, ''
                        line = line.replace(code, color)
                if foreground_color: line = line.replace('$', f'{foreground_color}$')
                line = line.replace('%{version}', version).replace('%{production_mode}', str(production_mode)).replace('%{modified}', str(modified))
                if line: print(line, end='')
    except FileNotFoundError: print(f"RoWhoIs | {version} ({'Modified' if modified else 'Unmodified'}) | {'Production Mode' if production_mode else 'Testing Mode'}")
