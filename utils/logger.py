"""
N/A
"""
import asyncio
import aiofiles
from datetime import datetime

COLOR_CODES = {
    "%{blue}": "\033[34m", "%{clear}": "\033[0m", "%{bold}": "\033[1m", "%{grey}": "\033[90m",
    "%{black}": "\033[30m", "%{red}": "\033[31m", "%{green}": "\033[32m",
    "%{yellow}": "\033[33m", "%{magenta}": "\033[35m", "%{cyan}": "\033[36m",
    "%{white}": "\033[37m",  "%{darkgrey}": "\033[90m"
}


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
                else:
                    line = ''.join([f'{background_color}{char}\033[0m' if char != '$' and background_color is not None else char for char in line])
                for code, color in COLOR_CODES.items():
                    if code in line:
                        if i == 0:
                            foreground_color, line = color, ''
                        elif i == 1:
                            background_color, line = color, ''
                        line = line.replace(code, color)
                if foreground_color:
                    line = line.replace('$', f'{foreground_color}$')
                line = line.replace('%{version}', version).replace('%{production_mode}', str(production_mode)).replace('%{modified}', str(modified))
                if line:
                    print(line, end='')
    except FileNotFoundError:
        print(f"RoWhoIs | {version} ({'Modified' if modified else 'Unmodified'}) | {'Production Mode' if production_mode else 'Testing Mode'}")
