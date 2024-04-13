"""
Library used for defining custom data types

RoWhoIs 2024
"""
import aiohttp
class User:
    """Used for defining a base user object"""
    def __init__(self, id: int, username: str = None, nickname: str = None, verified: bool = False):
        self.id = id
        self.username = username
        self.nickname = nickname
        self.verified = verified

class UserAuth:
    """Used for defining a base authenticated user object"""
    def __init__(self, token: str, csrf: str):
        self.token = token
        self.csrf = csrf


class Proxy:
    """Used for defining a proxy object"""
    def __init__(self, ip: str):
        self.ip = ip

class Proxies:
    """Used for defining a proxy configuration for a request"""
    def __init__(self, enabled: bool, ips: tuple[str, str], username: str = None, password: str = None, logged: bool = False):
        self.enabled = enabled
        self.ips = ips
        self.auth = aiohttp.BasicAuth(username, password)
        self.auth_required = True if username and password else False
        self.logged = logged

class BaseAsset:
    """Used for defining a base asset object"""
    def __init__(self, id: int, name: str):
        self.id = id
        self.name = name