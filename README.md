# RoWhoIs

The most advanced Roblox lookup Discord bot.

![Demo of the whois command](https://rowhois.com/demo-whois-small.gif)

![Internal Screenshot of a RoWhoIs Instance](https://rowhois.com/rowhois-internal.png)

## Commands

|     Command     | Parameters            |                                                                                                                                                                                Description |
|:---------------:|:----------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------:|
|      help       | None                  |                                                                                                                                                   Displays a list of commands RoWhoIs has. |
|      whois      | `User`                | Returns User ID, account status, joined, last online, description, previous usernames, verified email, total rap, total value, group count, friend count, follower count, following count. |
| clothingtexture | `Clothing ID`         |                                                                                                                         Returns a PNG file containing the texture for a 2D clothing asset. |
|    ownsitem     | `User`, `Item ID`     |                                                                                          Returns the item name, a count of the item owned and the unique asset ids for each item if owned. |
|    ownsbadge    | `User`, `Badge ID`    |                                                                                                                                        Returns badge award date, name, and image if owned. |
|  isfriendswith  | `User1`, `User`       |                                                                                                                                                                  Returns True/False embed. |
|      game       | `Game ID`             |                                                                                               Returns game data like like/dislikes, favorites, players, max player count, copylocked, etc. |
|      group      | `Group ID`            |                                                                                         Returns the group name, ID, status, created, owner username, owner userid, shout, and description. |
|    isingroup    | `User`, `Group ID`    |                                                                                                                                              Returns player's role and group name if True. |
|     limited     | `Limited`             |                                                                                                                                               Returns the ID, RAP, and Value of a limited. |
|   itemdetails   | `Item ID`             |                                                                                   Returns the creator username & id, description, created, updated, quantity, remaining, and lowest price. |
|   membership    | `User`                |                                                                                                                               Returns whether a player has Premium, or has had BC/TBC/OBC. |
|  checkusername  | `Username`            |                                                                                                                                                    Checks whether a username is available. |
|     userid      | `Username`            |                                                                                                                                                       Returns the User ID from a username. |
|    username     | `User ID`             |                                                                                                                                                       Returns the username from a User ID. |
|  groupclothing  | `Group ID`, `Page`    |                                                                                                   Fetches bulk clothing assets from a group. This command is restricted to a subscription. |
|  userclothing   | `User`, `Page`        |                                                                                                    Fetches bulk clothing assets from a user. This command is restricted to a subscription. |
|      about      | None                  |                                                                                                         Shows advanced statistics about RoWhoIs, including cache size, users, shards, etc. |
|      asset      | `Asset ID`, `Version` |                                                                                                  Fetches an asset file from Roblox. This command is not recommended for clothing textures. |


## In-Console Commands
|  Name   | Description                        |
|:-------:|:-----------------------------------|
|  down   | Shuts the server down              |
|   up    | Prints the server uptime           |
| shards  | Prints the server shard count      |
| servers | Prints the server guild count      |
|  cache  | Prints the cache size              |
| cflush  | Flushes the cursors cache          |
| lflush  | Flushes old logs                   |
|  flush  | Flushes entire cache               |
| reload  | Hot-reloads the configuration file |

## Dependencies

RoWhoIs relies on a set of dependencies to function properly.
The following are all external dependencies RoWhoIs relies on to work:

`aioconsole, aiofiles, aiohttp, hikari, uvloop`

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
    "api_key": "Roblox-provided Cloud API key here"
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

| Emoji                | Use case                                                                          |
|:---------------------|:----------------------------------------------------------------------------------|
| verified             | Used for players who have the "verified" status on their profile.                 |
| staff                | Used on the profile of RoWhoIs operators.                                         |
| subscription         | Used for RoWhoIs+, the subscription tier for RoWhoIs                              |
| donor                | Placed on the profile of users who donate to RoWhoIs through GitHub or Bitcoin    |
| limited              | Applied to a limited item.                                                        |
| limitedu             | Applied to a limited-unique item.                                                 |
| robux                | Used for symbolizing the virtual currency.                                        |
| collectible          | Used for user-generated limiteds.                                                 |
| bc                   | Used for players who had Builders Club, a predecessor to Premium 450.             |
| tbc                  | Used for players who had Turbo Builders Club, a predecessor to Premium 1000.      |
| obc                  | Used for players who had Outrageous Builders Club, a predecessor to Premium 2200. |
| premium              | Used for players who have the Premium subscription.                               |
| administrator        | Part of the `robloxbadges` command.                                               |
| ambassador           | Part of the `robloxbadges` command.                                               |
| bloxxer              | Part of the `robloxbadges` command.                                               |
| bricksmith           | Part of the `robloxbadges` command.                                               |
| combat initiation    | Part of the `robloxbadges` command.                                               |
| homestead            | Part of the `robloxbadges` command.                                               |
| inviter              | Part of the `robloxbadges` command.                                               |
| official model maker | Part of the `robloxbadges` command.                                               |
| veteran              | Part of the `robloxbadges` command.                                               |
| warrior              | Part of the `robloxbadges` command.                                               |
| welcome to the club  | Part of the `robloxbadges` command.                                               |
| friendship           | Part of the `robloxbadges` command.                                               |

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

First and foremost, `main.py`. This initializes `server/Roquest.py` with the needed parameters to begin making API calls to Roblox. Next is `server/RoWhoIs.py`. This is instantiated in `main.py` and is the main class for RoWhoIs. It handles all the commands and interactions with the user. You can find every public-facing RoWhoIs command in this file.

`server/app_commands.py` is the infrastructure for handling slash commands. This file is responsible for handling all the app commands RoWhoIs has. This not only serves as a wrapper to every command, it also validates user cooldowns, entitlements, and permissions. An added bonus of it being a wrapper is ease of error handling, as it's all done automatically.

`server/RoModules.py` essentially is an 'API-wrapper' for Roblox, providing useful automatation such as raw user input strings to proper User objects and other useful, common functions.

`utils/typedefs.py` contains all the type definitions for RoWhoIs. This is useful for type hinting and ensuring that the codebase is consistent. It also makes it easier to understand what each function is returning by converting certain data types to classes.

`utils/logger.py` is the logging infrastructure for RoWhoIs. It logs all the interactions, errors, and other important information.

`utils/gUtils.py` contains general utilities that are used throughout the codebase. Generally this is for internal use, and does not interact with the API.

`utils/ErrorDict.py` contains all the error messages that RoWhoIs can return. This is useful for ensuring that the error messages are consistent and easy to understand and makes handling exceptions far more intuitive.

## Caching

RoWhoIs caches catalog nextPageCursors and asset files to reduce the number of API calls made. This is especially useful for the `groupclothing` and `userclothing` commands, as they can make a large number of API calls in a short period of time.

Due to the non-changing nature of assets, caching makes sense as to reduce bandwith and API calls used.

nextPageCursor cache is retained for an hour per group/user, and asset files are retained permanently.

## Moderation

RoWhoIs has a built-in moderation system. This system is used to prevent abuse of the bot and to ensure that the bot is used in a safe and responsible manner. The moderation system is split into three parts: opt-out users/assets, and banned users.
These are all stored in `config.json` under the `RoWhoIs` key and loaded during initialization.

## Sharding

RoWhoIs operates under shards. There may be a performance drawback during initialization, but it's a necessary evil to ensure the bot can operate in a large number of guilds.

While if some instances of RoWhoIs don't operate in more than 2,500+ guilds (the required amount to begin sharding), it's still a good idea to have sharding in place for future-proofing or larger instances.

In the log outputs, each user-invoked call will have a shard ID. This is the shard that the user's guild is located on. An example output of this is `.1`, meaning that that request was performed on shard 1.

A full example log output:

```
I 2024-04-18 04:39:37,220 RoWhoIs.Roquest.0: http://168.181.229.86:50100;  GET friends | v1/users/5192280939/followers/count
```

This level of fine-grain logging allows for further performance optimizations in the future.

## SKUs

Because RoWhoIs has paid commands, testing to ensure these paid features work is critical. When RoWhoIs is not in `productionMode`, it will override any entitlement checks.

To simplify things, as RoWhoIs will only ever have one paid tier, the SKU system is very simple. RoWhoIs checks the entitlements of the interaction, and if they are greater than 0 (meaning they have purchased an SKU), it will grant them access to the paid features.

Paid features include lowered cooldown rates, more filetype downloads, and access to additional commands.
