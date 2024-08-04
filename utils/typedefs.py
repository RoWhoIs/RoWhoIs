"""
Library used for defining custom data types

RoWhoIs 2024
"""
from dataclasses import dataclass
import datetime
from typing import List


@dataclass
class User:
    """Used for defining a base user object"""
    id: int
    username: str | None
    nickname: str | None
    description: str | None
    joined: str | None
    banned: bool | None
    verified: bool | None
    online: bool | None
    friends: int | None
    followers: int | None
    following: int | None
    thumbnail: str | None
    headshot: str | None
    bust: str | None


@dataclass
class UserAuth:
    """Used for defining a base authenticated user object"""
    token: str
    csrf: str


@dataclass
class Proxy:
    """Used for defining a proxy object"""
    ip: str | None


@dataclass
class Proxies:
    """Used for defining a proxy configuration for a request"""
    enabled: bool
    ips: List[str] | None
    username: str | None = None
    password: str | None = None
    logged: bool = False


@dataclass
class BaseAsset:
    """
    Used for defining a base asset object,
    which unlike a full asset object, does not contain all the information
    """
    id: int
    name: str


@dataclass
class Game:
    """Used for defining a game object"""
    id: int
    universe: int | None
    creator: User | None
    name: str | None
    price: int | None
    url: str | None
    description: str | None
    max_players: int | None
    created: datetime.datetime | None
    updated: datetime.datetime | None
    genre: str | None
    thumbnail: str | None
    video_enabled: bool | None
    copy_protected: bool | None
    voice_chat: bool = False
    likes: int  = 0
    dislikes: int = 0
    visits: int = 0
    favorites: int = 0
    playing: int = 0
    playable: bool = False


@dataclass
class Message:
    """Used for defining messages or group shouts"""
    id: int
    author: User
    content: str
    created: datetime.datetime


@dataclass
class Group:
    """Used to define a group"""
    id: int
    name: str
    description: str | None
    owner: User | None
    created: datetime.datetime
    locked: bool
    public: bool
    member_count: int = 0
    locked: bool = False
    public: bool = False
    verified: bool = False
    shout: Message | None = None
    emblem: str = "https://rowhois.com/not-available.png"


@dataclass
class Limited:
    """Used for defining a limited Roblox item"""
    id: int
    name: str
    acronym: str | None
    rap: int | None
    value: int | None
    demand: str | None
    trend: str | None
    projected: bool | None
    rare: bool | None
