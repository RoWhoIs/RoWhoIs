"""
Library used for defining custom data types

RoWhoIs 2024
"""
import aiohttp

class User:
    """Used for defining a base user object"""
    def __init__(self, id: int, username: str = None, nickname: str = None, verified: bool = None, description: str = None, joined: str = None, banned: bool = None, online: bool = None, friends: int = None, followers: int = None, following: int = None):
        variables = [id, username, nickname, verified, description, joined, banned, online, friends, followers, following]
        for var in variables:
            if isinstance(var, BaseException): raise var
        self.id = id
        self.username = username
        self.nickname = nickname
        self.description = description
        self.joined = joined
        self.banned = banned
        self.verified = verified
        self.online = online
        self.friends = friends
        self.followers = followers
        self.following = following

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
        variables = [enabled, ips, username, password, logged]
        for var in variables:
            if isinstance(var, BaseException): raise var
        self.enabled = enabled
        self.ips = ips
        self.auth = aiohttp.BasicAuth(username, password) if username and password else None
        self.auth_required = True if username and password else False
        self.logged = logged

class BaseAsset:
    """Used for defining a base asset object"""
    def __init__(self, id: int, name: str):
        self.id = id
        self.name = name
