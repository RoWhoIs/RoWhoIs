"""
RoWhoIs modules library. If a roquest is likely to be reused multiple times throughought the main program, it is likely to be here.
"""
# The general rule of thumb is that if it's a background task, not caused by user interaction, or doesn't require roquesting, it doesn't require a shard_id
import asyncio, aiofiles, re, io
from typing import Union, List, Dict, Tuple
from server import Roquest
from utils import ErrorDict, gUtils, typedefs

async def general_error_handler(data: int, expectedresponsecode: int = 200) -> None:
    """Will throw an error when data doesn't match requirements"""
    if data in [403, 401]: raise ErrorDict.InvalidAuthorizationError
    elif data in [404, 400]: raise ErrorDict.DoesNotExistError
    elif data == -1: raise ErrorDict.UndocumentedError
    elif data == 409: raise ErrorDict.MismatchedDataError
    elif data == 429: raise ErrorDict.RatelimitedError
    elif data != expectedresponsecode: raise ErrorDict.UnexpectedServerResponseError

async def handle_usertype(user: Union[int, str], shard_id: int) -> typedefs.User:
    """Handles a user type and returns a User object containing id, name, nickname, and verified"""
    user = str(user)
    if user.isdigit(): return await convert_to_username(user, shard_id)
    else: return await convert_to_id(user, shard_id)

async def convert_to_id(username: str, shard_id: int) -> tuple[int, str, str, bool]:
    """Returns user id, username, display name, verified badge"""
    data = await Roquest.Roquest("POST", "users", "v1/usernames/users", json={"usernames": [username], "excludeBannedUsers": False}, shard_id=shard_id)
    await general_error_handler(data[0])
    if "data" in data[1] and data[1]["data"]:
        user_data = data[1]["data"][0]
        if "id" in user_data and "name" in user_data: return typedefs.User(id=int(user_data["id"]), username=user_data["name"], nickname=user_data["displayName"], verified=user_data["hasVerifiedBadge"])
        else: raise ErrorDict.DoesNotExistError
    else: raise ErrorDict.DoesNotExistError

async def convert_to_username(user: int, shard_id: int) -> tuple[str, str, bool]:
    """Converts a user id into a username. Returns name, display name, and verified status."""
    data = await Roquest.Roquest("POST", "users", "v1/users", shard_id=shard_id, json={"userIds": [user], "excludeBannedUsers": False})
    await general_error_handler(data[0])
    if "data" in data[1] and data[1]["data"]:
        user_data = data[1]["data"][0]
        if "id" in user_data: return typedefs.User(id=int(user), username=user_data["name"], nickname=user_data["displayName"], verified=user_data["hasVerifiedBadge"])
        else: raise ErrorDict.DoesNotExistError
    else: raise ErrorDict.DoesNotExistError

async def check_verification(user_id: int, shard_id: int) -> int:
    """Retrieves the email verification status for a given account"""
    verifhat, verifsign = await asyncio.gather(Roquest.Roquest("GET", "inventory", f"v1/users/{user_id}/items/4/102611803", shard_id=shard_id), Roquest.Roquest("GET", "inventory", f"v1/users/{user_id}/items/4/1567446", shard_id=shard_id))
    await asyncio.gather(general_error_handler(verifhat[0]), general_error_handler(verifsign[0]))
    hatOwned = any("type" in item for item in verifhat[1].get("data", []))
    signOwned = any("type" in item for item in verifsign[1].get("data", []))
    return 4 if hatOwned and signOwned else 1 if hatOwned else 2 if signOwned else 3

async def last_online(user_id: int, shard_id: int):
    """Retrieves the last online date of a player"""
    last_data = await Roquest.Roquest("POST", "presence", "v1/presence/last-online", failretry=True, json={"userIds": [user_id]}, shard_id=shard_id)
    await general_error_handler(last_data[0])
    return last_data[1]["lastOnlineTimestamps"][0]["lastOnline"]


async def get_player_profile(user_id: int, shard_id: int) -> typedefs.User:
    """Returns description, joined, banned, username, display name, verified"""
    desc = await Roquest.Roquest("GET", "users", f"v1/users/{user_id}", shard_id=shard_id)
    await general_error_handler(desc[0], 200)
    return typedefs.User(id=user_id, username=desc[1]["name"], nickname=desc[1]["displayName"], verified=desc[1]["hasVerifiedBadge"], description=desc[1]["description"], joined=desc[1]["created"], banned=desc[1]["isBanned"])

async def get_previous_usernames(user_id: int, shard_id: int):
    """Returns a player's previous usernames"""
    usernames = []
    next_page_cursor = None
    while True:
        url = f"v1/users/{user_id}/username-history?limit=100&sortOrder=Asc"
        if next_page_cursor:
            url += f"&cursor={next_page_cursor}"
        data = await Roquest.Roquest("GET", "users", url, shard_id=shard_id)
        await general_error_handler(data[0])
        usernames += [entry["name"] for entry in data[1]["data"]]
        next_page_cursor = data[1].get("nextPageCursor")
        if not next_page_cursor: break
    return usernames

async def get_socials(user_id: int, shard_id: int) -> tuple[int, int, int]:
    """Returns Friends, Followers, Following"""
    friend_count, following_count, follow_count = await asyncio.gather(Roquest.Roquest("GET", "friends", f"v1/users/{user_id}/friends/count", shard_id=shard_id), Roquest.Roquest("GET", "friends", f"v1/users/{user_id}/followings/count", shard_id=shard_id), Roquest.Roquest("GET", "friends", f"v1/users/{user_id}/followers/count", shard_id=shard_id))
    await asyncio.gather(general_error_handler(friend_count[0]), general_error_handler(following_count[0]), general_error_handler(follow_count[0]))
    return friend_count[1]["count"], follow_count[1]["count"], following_count[1]["count"]

async def get_friends(user_id: int, shard_id: int):
    friend_data = await Roquest.Roquest("GET", "friends", f"v1/users/{user_id}/friends?userSort=0", shard_id=shard_id)
    await general_error_handler(friend_data[0])
    return friend_data[1]

async def get_groups(user_id: int, shard_id: int):
    group_data = await Roquest.Roquest("GET", "groups", f"v1/users/{user_id}/groups/roles", shard_id=shard_id)
    await general_error_handler(group_data[0])
    return group_data[1]

async def get_player_bust(user_id: int, size: str, shard_id: int):
    thumbnail_url = await Roquest.Roquest("GET", "thumbnails", f"v1/users/avatar-headshot?userIds={user_id}&size={size}&format=Png&isCircular=false", shard_id=shard_id, failretry=True)
    if thumbnail_url[0] != 200: return "https://rowhois.com/not-available.png"
    elif thumbnail_url[1]["data"][0]["state"] == "Blocked": return "https://rowhois.com/blocked.png"
    else: return thumbnail_url[1]["data"][0]["imageUrl"]

async def get_player_headshot(user_id: int, shard_id: int):
    thumbnail_url = await Roquest.Roquest("GET", "thumbnails", f"v1/users/avatar-headshot?userIds={user_id}&size=60x60&format=Png&isCircular=true", shard_id=shard_id, failretry=True)
    if thumbnail_url[0] != 200: return "https://rowhois.com/not-available.png"
    elif thumbnail_url[1]["data"][0]["state"] == "Blocked": return "https://rowhois.com/blocked.png"
    else: return thumbnail_url[1]["data"][0]["imageUrl"]

async def get_player_thumbnail(user_id: int, size: str, shard_id: int):
    """Retrieves a full-body thumbnail of a player's avatar"""
    thumbnail_url = await Roquest.Roquest("GET", "thumbnails", f"v1/users/avatar?userIds={user_id}&size={size}&format=Png&isCircular=false", shard_id=shard_id, failretry=True)
    if thumbnail_url[0] != 200: return "https://rowhois.com/not-available.png"
    elif thumbnail_url[1]["data"][0]["state"] == "Blocked": return "https://rowhois.com/blocked.png"
    else: return thumbnail_url[1]["data"][0]["imageUrl"]

async def get_badge_thumbnail(badge_id: int, shard_id: int):
    thumbnail_url = await Roquest.Roquest("GET", "thumbnails", f"v1/badges/icons?badgeIds={badge_id}&size=150x150&format=Png&isCircular=false", shard_id=shard_id, failretry=True)
    if thumbnail_url[0] != 200: return "https://rowhois.com/not-available.png"
    elif thumbnail_url[1]["data"][0]["state"] == "Blocked": return "https://rowhois.com/blocked.png"
    else: return thumbnail_url[1]["data"][0]["imageUrl"]

async def get_group_emblem(group: int, size: str, shard_id: int):
    thumbnail_url = await Roquest.Roquest("GET", "thumbnails", f"v1/groups/icons?groupIds={group}&size={size}&format=Png&isCircular=false", shard_id=shard_id, failretry=True)
    if thumbnail_url[0] != 200: return "https://rowhois.com/not-available.png"
    elif thumbnail_url[1]["data"][0]["state"] == "Blocked": return "https://rowhois.com/blocked.png"
    else: return thumbnail_url[1]["data"][0]["imageUrl"]

async def get_item_thumbnail(item_id: int, size: str, shard_id: int):
    """Retrieves the thumbnail of a given item"""
    thumbnail_url = await Roquest.Roquest("GET", "thumbnails", f"v1/assets?assetIds={item_id}&returnPolicy=PlaceHolder&size={size}&format=Png&isCircular=false", shard_id=shard_id, failretry=True)
    if thumbnail_url[0] != 200: return "https://rowhois.com/not-available.png"
    elif thumbnail_url[1]["data"][0]["state"] == "Blocked": return "https://rowhois.com/blocked.png"
    else: return thumbnail_url[1]["data"][0]["imageUrl"]

async def get_game_icon(universe_id: int, size: str, shard_id: int):
    """Retrieves the icon of a given game"""
    thumbnail_url = await Roquest.Roquest("GET", "thumbnails", f"v1/games/icons?universeIds={universe_id}&returnPolicy=PlaceHolder&size={size}&format=Png&isCircular=false", shard_id=shard_id, failretry=True)
    if thumbnail_url[0] != 200: return "https://rowhois.com/not-available.png"
    elif thumbnail_url[1]["data"][0]["state"] == "Blocked": return "https://rowhois.com/blocked.png"
    else: return thumbnail_url[1]["data"][0]["imageUrl"]

async def get_rolidata_from_item(rolidata, item: str) -> tuple[int, str, int, int, str, str, str, str, bool]:
    """Returns limited id, name, acronym, rap, value, demand, trend, projected, and rare"""
    demandDict = {-1: None, 0: "Terrible", 1: "Low", 2: "Normal", 3: "High", 4: "Amazing"}
    trendDict = {-1: None, 0: "Unstable", 1: "Lowering", 2: "Stable", 3: "Rising", 4: "Fluctuating"}
    for limited_id, item_data in rolidata["items"].items():
        # [0 item_name, 1 acronym, 2 rap, 3 value, 4 default_value, 5 demand, 6 trend, 7 projected, 8 hyped, 9 rare]
        if item.lower() in [item_data[0].lower(), item_data[1].lower(), limited_id]: return limited_id, item_data[0], item_data[1], item_data[2], item_data[4], demandDict.get(item_data[5]), trendDict.get(item_data[6]), True if item_data[7] != -1 else False, True if item_data[9] != -1 else False
    else: raise ErrorDict.DoesNotExistError

async def get_membership(user: int, shard_id: int) -> tuple[bool, bool, bool, bool]:
    """Returns hasPremium, ownedBc, ownedTbc, and ownedObc"""
    checkBc = await Roquest.Roquest("GET", "inventory", f"v1/users/{user}/items/4/24814192", shard_id=shard_id)
    await general_error_handler(checkBc[0])
    checkPremium, checkTbc, checkObc = await asyncio.gather(Roquest.Roquest("GET", "premiumfeatures", f"v1/users/{user}/validate-membership", shard_id=shard_id, bypass_proxy=True), Roquest.Roquest("GET", "inventory", f"v1/users/{user}/items/4/11895536", shard_id=shard_id), Roquest.Roquest("GET", "inventory", f"v1/users/{user}/items/4/17407931", shard_id=shard_id))
    await asyncio.gather(general_error_handler(checkPremium[0]), general_error_handler(checkObc[0]), general_error_handler(checkTbc[0]))
    ownedBc = any("type" in item for item in checkBc[1].get("data", []))
    ownedTbc = any("type" in item for item in checkTbc[1].get("data", []))
    ownedObc = any("type" in item for item in checkObc[1].get("data", []))
    return checkPremium[1], ownedBc, ownedTbc, ownedObc

async def get_group(group: int, shard_id: int) -> tuple[str, str, str, bool, list[Union[str, int, bool]], list[Union[str, str, int, bool]], int, bool, bool]:
    """Returns name (0), description (1), created (2), verified (3), owner (4), shout (5), members (6), public (7), isLocked (8)"""
    getGroup, getGroupV1 = await asyncio.gather(Roquest.Roquest("GET", "groups", f"v2/groups?groupIds={group}", shard_id=shard_id), Roquest.Roquest("GET", "groups", f"v1/groups/{group}", shard_id=shard_id))
    await asyncio.gather(general_error_handler(getGroup[0]), general_error_handler(getGroupV1[0]))
    groupName = getGroup[1]['data'][0]['name']
    groupDescription = getGroup[1]['data'][0]['description']
    groupCreated = getGroup[1]['data'][0]['created']
    groupVerified = getGroup[1]['data'][0]['hasVerifiedBadge']
    if getGroupV1[1]['owner'] is not None:
        if getGroupV1[1]['owner']['username'] is None: groupOwner = None
        else: groupOwner = [getGroupV1[1]['owner']['username'], getGroupV1[1]['owner']['userId'], getGroupV1[1]['owner']['hasVerifiedBadge']]
    else: groupOwner = [False, False, False]
    if getGroupV1[1]['shout'] is None: groupShout = None
    else: groupShout = [getGroupV1[1]['shout']['body'], getGroupV1[1]['shout']['poster']['username'], getGroupV1[1]['shout']['poster']['userId'], getGroupV1[1]['shout']['poster']['hasVerifiedBadge']]
    groupMembers = getGroupV1[1]['memberCount']
    groupPublic = getGroupV1[1]['publicEntryAllowed']
    if 'isLocked' in getGroupV1[1]: groupLocked = getGroupV1[1]['isLocked']
    else: groupLocked = False
    return groupName, groupDescription, groupCreated, groupVerified, groupOwner, groupShout, groupMembers, groupPublic, groupLocked

async def validate_username(username: str, shard_id: int) -> tuple[int, str]:
    """Validate if a username is available"""
    data = await Roquest.Roquest("POST", "auth", f"v2/usernames/validate", json={"username": username, "birthday": "2000-01-01T00:00:00.000Z", "context": 0}, shard_id=shard_id, bypass_proxy=True, failretry=True)
    await general_error_handler(data[0])
    return data[1]['code'], data[1]['message']

async def get_limiteds(user: int, rolidata, shard_id: int) -> tuple[bool, int, int, List[Dict[int, int]]]:
    """Retrieves the RAP and value of a player"""
    privateInventory, totalRap, totalValue, items, cursor = True, 0, 0, [], ""
    while True:
        rap = await Roquest.Roquest("GET", "inventory", f"v1/users/{user}/assets/collectibles?limit=100&sortOrder=Asc&cursor={cursor}", shard_id=shard_id)
        if rap[0] == 403:
            privateInventory = True
            break
        if rap[0] != 200: raise ErrorDict.UnexpectedServerResponseError
        else: privateInventory = False
        data = rap[1].get("data", [])
        if not data: break
        for item in data:
            assetId = str(item.get("assetId", 0))
            if assetId in rolidata['items']:
                items.append(assetId)
                itemValue = rolidata['items'][assetId][4]
                if itemValue is not None: totalValue += itemValue
            rap_value = item.get("recentAveragePrice", 0)
            if rap_value is not None: totalRap += rap_value
        cursor = rap[1].get("nextPageCursor")
        if not cursor: break
    return privateInventory, totalRap, totalValue, items

async def get_item(item: int, shard_id: int):
    """Retrieves an item and returns its data"""
    data = await Roquest.Roquest("GET", "economy", f"v2/assets/{item}/details", shard_id=shard_id)
    await general_error_handler(data[0])
    return data[1]

async def owns_item(user: int, item: int, shard_id: int) -> tuple[bool, int, str, List[Dict[int, int]]]:
    """Retrieves whether a player owns an item and returns the UAID and name of item if True"""
    itemData = await Roquest.Roquest("GET", "inventory", f"v1/users/{user}/items/4/{item}", shard_id=shard_id)
    if 'errors' in itemData[1]: return None, 0, itemData[1]['errors'][0]['message'], []
    await general_error_handler(itemData[0])
    if itemData[1]["data"] and any("type" in item for item in itemData[1]["data"]):
        itemName = itemData[1]['data'][0]['name']
        totalOwned = len(itemData[1]['data'])
        uaidList = [item["instanceId"] for item in itemData[1]["data"]]
        return True, totalOwned, itemName, uaidList
    else: return False, 0, "", []

async def owns_badge(user: int, badge: int, shard_id: int) -> tuple[bool, str]:
    """Retrieve whether a player owns a badge and returns the award date if True"""
    data = await Roquest.Roquest("GET", "badges", f"v1/users/{user}/badges/awarded-dates?badgeIds={badge}", shard_id=shard_id)
    await general_error_handler(data[0])
    if data[1]["data"] and any("type" for _ in data[1]["data"][0]): return True, data[1]["data"][0]["awardedDate"]
    else: return False, 0

async def roblox_badges(user: int, shard_id: int) -> tuple[List[int], Dict[int, str]]:
    """Retrieves a player's Roblox badges, returns a list of badge ids and a badge name lookup table."""
    badgeTable = {1: "Administrator", 2: "Friendship", 3: "Combat Initiation", 4: "Warrior", 5: "Bloxxer", 6: "Homestead", 7: "Bricksmith", 8: "Inviter", 12: "Veteran", 14: "Ambassador", 17: "Official Model Maker", 18: "Welcome To The Club"}
    data = await Roquest.Roquest("GET", "accountinformation", f"v1/users/{user}/roblox-badges", shard_id=shard_id)
    await general_error_handler(data[0])
    badges = []
    for badge in data[1]: badges.append(badge['id'])
    return sorted(badges), badgeTable

async def get_creator_assets(creator: int, creator_type: str, page: int, shard_id: int) -> tuple[int, List[Dict[str, Union[str, int]]]]:
    """Retrieves a group's assets
    Returns the assets, and the number of successful pages it iterated through"""
    nextPageCursor, assetIds, cached_pages = None, [], 0
    if page < 1: return [], 0
    for i in range(page):
        if i != 0:
            cached_cursor = await gUtils.cache_cursor(None, creator_type, creator, pagination=i)
            if not cached_cursor: break
            cached_pages += 1
            nextPageCursor = cached_cursor
    if cached_pages == page: cached_pages -= 1
    for i in range(cached_pages, page):
        data = await Roquest.Roquest("GET", "catalog", f"v1/search/items?category=Clothing&creatorTargetId={creator}&creatorType={creator_type}&cursor={nextPageCursor if nextPageCursor is not None else ''}&limit=10&sortOrder=Desc&includeNotForSale=true&sortType=Updated", failretry=True, shard_id=shard_id)
        if data[0] == 500: raise ErrorDict.DoesNotExistError # lol
        await general_error_handler(data[0])
        nextPageCursor = data[1].get('nextPageCursor')
        if nextPageCursor: await gUtils.cache_cursor(nextPageCursor, creator_type, creator, write=True, pagination=i + 1)
        if not nextPageCursor: break
    for asset in data[1]['data']: assetIds.append(asset['id'])
    return assetIds, i + 1

async def fetch_asset(asset_id: int, shard_id: int, filetype: str = "png", location: str = "clothing", version: int = None) -> int: # Unsafe by design
    """Fetches an asset and caches it locally for future use. Returns the asset id."""
    try:
        try:
            async with aiofiles.open(f"cache/{location}/{str(asset_id)}{'-' + str(version) if version is not None else ''}.{filetype}", 'rb'): return asset_id
        except FileNotFoundError:
            if filetype in ["png"]:
                initAsset = await Roquest.GetFileContent(asset_id, shard_id=shard_id)
                initAssetContent = io.BytesIO(initAsset)
                initAssetContent = initAssetContent.read().decode()
                match = re.search(r'<url>.*id=(\d+)</url>', initAssetContent)
                if not match: raise ErrorDict.DoesNotExistError
                async with aiofiles.open(f"cache/{location}/{str(asset_id)}{'-' + str(version) if version is not None else ''}.{filetype}", 'wb') as cached_content:
                    downloadedAsset = await Roquest.GetFileContent(match.group(1), shard_id=shard_id)
                    if not downloadedAsset or len(downloadedAsset) < 512: raise ErrorDict.UndocumentedError
                    await cached_content.write(downloadedAsset)
                await cached_content.close()
                return asset_id
        downloadedAsset = await Roquest.GetFileContent(asset_id, version=version, shard_id=shard_id)
        if filetype in ["png"]: raise ErrorDict.MismatchedDataError
        else:
            async with aiofiles.open(f"cache/{location}/{str(asset_id)}{'-' + str(version) if version is not None else ''}.{filetype}", 'wb') as cached_content: await cached_content.write(downloadedAsset)
            await cached_content.close()
            return asset_id
    except UnicodeDecodeError: raise ErrorDict.MismatchedDataError

async def fetch_game(game: int, shard_id: int) -> typedefs.Game:
    """Fetches a game"""
    try:
        initRequest = await Roquest.Roquest("GET", "games", f"v1/games/multiget-place-details?placeIds={game}", shard_id=shard_id, bypass_proxy=True)
        await general_error_handler(initRequest[0])
        creator = typedefs.User(id=initRequest[1][0]['builderId'], username=initRequest[1][0]['builder'], verified=initRequest[1][0]['hasVerifiedBadge'])
        game = typedefs.Game(id=game, universe=initRequest[1][0]['universeId'], creator=creator, name=initRequest[1][0]['name'], playable=initRequest[1][0]['isPlayable'], price=initRequest[1][0]['price'], url=initRequest[1][0]['url'], description=initRequest[1][0]['description'])
        thumbnail, votes, additional_stats = await asyncio.gather(get_game_icon(game.universe, "420x420", shard_id), Roquest.Roquest("GET", "games", f"v1/games/votes?universeIds={game.universe}", shard_id=shard_id), Roquest.Roquest("GET", "games", f"v1/games?universeIds={game.universe}", shard_id=shard_id))
        await asyncio.gather(general_error_handler(votes[0]), general_error_handler(additional_stats[0]))
        game.thumbnail = thumbnail
        game.visits = additional_stats[1]['data'][0]['visits']
        game.favorites = additional_stats[1]['data'][0]['favoritedCount']
        game.created = additional_stats[1]['data'][0]['created']
        game.updated = additional_stats[1]['data'][0]['updated']
        game.playing = additional_stats[1]['data'][0]['playing']
        game.max_players = additional_stats[1]['data'][0]['maxPlayers']
        game.likes = votes[1]['data'][0]['upVotes']
        game.dislikes = votes[1]['data'][0]['downVotes']
        game.copy_protected = not additional_stats[1]['data'][0]['copyingAllowed']
        game.genre = additional_stats[1]['data'][0]['genre']
        return game
    except IndexError: raise ErrorDict.DoesNotExistError

async def nil_pointer() -> int:
    """Returns nil data"""
    return 0

async def get_full_player_profile(user: int, shard_id: int) -> Tuple[typedefs.User, int, List[str], List[dict[int, str]], int]:
    """Returns a User object, group count, previous usernames, Roblox badges, and verified email status."""
    tasks = [
        get_player_profile(user, shard_id),
        get_player_headshot(user, shard_id),
        get_player_thumbnail(user, "420x420", shard_id),
        last_online(user, shard_id),
        get_socials(user, shard_id),
        get_groups(user, shard_id),
        get_previous_usernames(user, shard_id),
        roblox_badges(user, shard_id),
        check_verification(user, shard_id)
    ] # Originally used safe_wrapper, shouldn't use, error propogation needed
    profile, headshot, thumbnail, online, socials, groups, usernames, badges, email_verification = await asyncio.gather(*tasks)
    user = typedefs.User(id=user, username=profile.username, nickname=profile.nickname, verified=profile.verified, description=profile.description, joined=profile.joined, online=online, banned=profile.banned, friends=socials[0], followers=socials[1], following=socials[2], thumbnail=thumbnail, headshot=headshot)
    return user, len(groups['data']), usernames, badges, email_verification
