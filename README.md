# RoWhoIs

An advanced Roblox lookup Discord bot utility.

![Demo of the whois command](https://www.robloxians.com/resources/demo-whois-small.gif)

## Commands

|      Command       | Parameters         |                                                                                                                                                                                Description |
|:------------------:|:-------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------:|
|        help        | None               |                                                                                                                                                   Displays a list of commands RoWhoIs has. |
|       whois        | `User`             | Returns User ID, account status, joined, last online, description, previous usernames, verified email, total rap, total value, group count, friend count, follower count, following count. |
| getclothingtexture | `Clothing ID`      |                                                                                                                         Returns a PNG file containing the texture for a 2D clothing asset. |
|      ownsitem      | `User`, `Item ID`  |                                                                                          Returns the item name, a count of the item owned and the unique asset ids for each item if owned. |
|     ownsbadge      | `User`, `Badge ID` |                                                                                                                                        Returns badge award date, name, and image if owned. |
|   isfriendswith    | `User1`, `User`    |                                                                                                                                                                  Returns True/False embed. |
|       group        | `Group ID`         |                                                                                         Returns the group name, ID, status, created, owner username, owner userid, shout, and description. |
|     isingroup      | `User`, `Group ID` |                                                                                                                                              Returns player's role and group name if True. |
|      limited       | `Limited`          |                                                                                                                                               Returns the ID, RAP, and Value of a limited. |
|   getitemdetails   | `Item ID`          |                                                                                   Returns the creator username & id, description, created, updated, quantity, remaining, and lowest price. |
|   getmembership    | `User`             |                                                                                                                               Returns whether a player has Premium, or has had BC/TBC/OBC. |
|   checkusername    | `Username`         |                                                                                                                                                    Checks whether a username is available. |
|       userid       | `Username`         |                                                                                                                                                       Returns the User ID from a username. |
|      username      | `User ID`          |                                                                                                                                                       Returns the username from a User ID. |

## Dependencies

RoWhoIs relies on a set of dependencies to function properly.
The following are all external dependencies RoWhoIs relies on to work:

`aiofiles, aiohttp, discord`

These dependencies can be satisfied by pip:

```bash
pip3 install -r requirements.txt
```

## Authentication

For RoWhoIs to properly start, it needs several things:

- A production Discord bot token
- A testing Discord bot token (optional)
- A .ROBLOSECURITY cookie
- A top.gg and discordbotlist token (optional)

These can all be found in `config.json` under the `Authentication` key.

```json
"Authentication": {
    "production": "Production bot token here",
    "testing": "Testing bot token here",
    "roblosecurity": "Roblosecurity cookie here",
    "topgg": "Top.GG token here",
    "dbl": "DiscordBotList token here"
  }
```

<sup>Note for any optional values, just pass a blank string.</sup>

## Configuration

RoWhoIs utilizes `config.json` in the main folder to load the following settings:

### RoWhoIs class

- Testing/Production Mode toggle
  - Switches the Bot token so you can safely test experimental features in a sandboxed environment.
- Opt-out users
  - Roblox User IDs of users who have requested to not be searchable by RoWhoIs
- Banned users
  - Discord User IDs of users who are restricted from using RoWhoIs
- Admin users
  - These users will get a special icon next to their RoWhoIs profile

### Proxy class

- Proxying enabled toggle
- Log proxying updates
- Proxy URL tables
  - Proxies _must_ be formatted with the method, ip, and port.
- Username, Password (Authentication)
  - Note if the `username` field is left blank, authentication will automatically be disabled.

### Emojis class

All configuration options for this are optional. To disable any specific emoji, just leave a blank string.

To obtain these emojis, simply put a backslash behind the emoji in Discord then send it. An example output of this is: `<:verified:1186711315679563886>`

| Emoji       | Use case                                                                          |
|:------------|:----------------------------------------------------------------------------------|
| verified    | Used for players who have the "verified" status on their profile.                 |
| staff       | Used on the profile of RoWhoIs operators.                                         |
| donor       | Currently unused, placed on the profile of users who donate to RoWhoIs.           |
| limited     | Applied to a limited item.                                                        |
| limitedu    | Applied to a limited-unique item.                                                 |
| robux       | Used for symbolizing the virtual currency.                                        |
| collectible | Used for user-generated limiteds.                                                 |
| bc          | Used for players who had Builders Club, a predecessor to Premium 450.             |
| tbc         | Used for players who had Turbo Builders Club, a predecessor to Premium 1000.      |
| obc         | Used for players who had Outrageous Builders Club, a predecessor to Premium 2200. |
| premium     | Used for players who have the Premium subscription.                               |

## Proxying

When scaling RoWhoIs, it becomes very apparent that rate-limiting will be a limiting factor in serving data to users. An easy workaround for this is by using the built-in proxying structure for RoWhoIs.
Proxies _must_ be residential or else RoWhoIs will face issues with rate-limiting.

Proxies are picked in chronological order from within the configuration file. Once RoWhoIs is initialized, `proxy_handler()` in `Roquest.py` will validate each proxy to ensure it works. Validated proxies are added to the `proxyPool` for use in API calls.
If a proxy fails to make an API call after one try, it will be removed from the proxy pool and the request will be handled by a different proxy.

Furthermore, if RoWhoIs detects there's no usable proxies in the proxy pool, it will automatically fallback to non-proxied requests.

It's a general best practice to make sure the proxy is located within a close region of where the roblosecurity cookie was generated. If it is too far, the roblosecurity cookie may be invalidated.

```json
"Proxy": {
    "proxying_enabled": true,
    "proxy_urls": ["http://192.168.0.1:8080", "http://192.168.1.0:8080"],
    "username": "rowhois",
    "password": "password123"
  }    
```

<sub>Example structure for proxy configuration</sub>

## Codebase structure

RoWhoIs containerizes operation types by file. This eases development and makes the codebase easier to manage.

`main.py` is used for initializing `RoWhoIs.py`, the main server. From there, `RoWhoIs.py` generally uses `RoModules.py`, a file containing modules for performing different API calls, to carry out command fulfillment. `RoModules.py` uses `Roquest.py`.
`Roquest.py` is where all requests to APIs are handled, including proxying. `ErrorDict.py` is used as an error dictionary. If ever something were to go wrong with RoWhoIs, it'll be an error object defined by that. Finally, `logger.py` is the utility from [AsyncLogger](https://github.com/aut-mn/AsyncLogger) used to asynchronously log everything.

Logs that are live are written to main.log, and sessions that are gracefully closed have log files named `server-YYYY-MM-DD-HHmmSS.log`

```
.
├── cache
│   └── clothing
│       └── 106779740.png
├── logs
│   └── server-2024-02-22-150004.log
├── server
│   └── RoModules.py
│   └── Roquest.py
│   └── RoWhoIs.py
├── utils
│   └── ErrorDict.py
│   └── logger.py
├── config.json
└── main.py
```

<sub>Example filestructure for a RoWhoIs server</sub>

## Caching

The only _feasible_ thing for RoWhoIs to cache is clothing textures. RoWhoIs only caches clothing texture files for several reasons, namely though being:

- Clothing textures never change
- It is the only use-case where downloading an asset is required
  - All other image operations use embed links, meaning it's more efficient to use those
