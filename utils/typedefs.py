"""
Library used for defining custom data types

RoWhoIs 2024
"""
import aiohttp

class User:
    """Used for defining a base user object"""
    def __init__(self, id: int, username: str = None, nickname: str = None, verified: bool = None, description: str = None, joined: str = None, banned: bool = None, online: bool = None, friends: int = None, followers: int = None, following: int = None, thumbnail: str = None, headshot: str = None, bust: str = None):
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
        self.thumbnail = thumbnail
        self.headshot = headshot
        self.bust = bust

class UserAuth:
    """Used for defining a base authenticated user object"""
    def __init__(self, token: str, csrf: str, api_key: str):
        self.token = token
        self.csrf = csrf
        self.api_key = api_key


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

class Game:
    def __init__(self, id: int, universe: int = None, creator: User = None, name: str = None, playable: bool = False, price: int = None, url: str = None, description: str = None, voice_chat: bool = False, max_players: int = None, genre: str = None, created: str = None, updated: str = None, visits: int = None, favorites: int = None, likes: int = None, dislikes: int = None, thumbnail: str = None, playing: int = None, video_enabled: bool = False, copy_protected: bool = False):
        self.id = id
        self.universe = universe
        self.creator = creator
        self.name = name
        self.playable = playable
        self.price = price
        self.url = url
        self.description = description
        self.voice_chat = voice_chat
        self.max_players = max_players
        self.genre = genre
        self.created = created
        self.updated = updated
        self.visits = visits
        self.favorites = favorites
        self.likes = likes
        self.dislikes = dislikes
        self.thumbnail = thumbnail
        self.playing = playing
        self.video_enabled = video_enabled
        self.copy_protected = copy_protected
