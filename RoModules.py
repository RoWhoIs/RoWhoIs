import Roquest, asyncio, ErrorDict

async def general_error_handler(data:int, expectedResponseCode:int=200) -> None:
    """Will throw an error when data doesn't match requirements"""
    if data == 403: raise ErrorDict.InvalidAuthorizationError
    elif data in [404, 400]: raise ErrorDict.DoesNotExistError
    elif data == -1: raise ErrorDict.UndocumentedError
    elif data == 409: raise ErrorDict.MismatchedDataError
    elif data == 429: raise ErrorDict.RatelimitedError
    elif data != expectedResponseCode: raise ErrorDict.UnexpectedServerResponseError

async def convert_to_id(username) -> tuple[int, str, str, bool]:
    """Returns user id, username, display name, verified badge"""
    userid = await Roquest.Roquest("POST", "users", "v1/usernames/users", json={"usernames": [username],"excludeBannedUsers": False})
    await general_error_handler(userid[0])
    if "data" in userid[1] and userid[1]["data"]:
        user_data = userid[1]["data"][0]
        if "id" in user_data and "name" in user_data: return user_data["id"], user_data["name"], user_data["displayName"], user_data["hasVerifiedBadge"]
        else: raise ErrorDict.DoesNotExistError
    else: raise ErrorDict.DoesNotExistError
        
async def convert_to_username(userid:int) -> tuple[str, str, bool]:
    userid = await Roquest.Roquest("POST", "users", "v1/users", json={"userIds": [userid],"excludeBannedUsers": False})
    await general_error_handler(userid[0])
    if "data" in userid[1] and userid[1]["data"]:
        user_data = userid[1]["data"][0]
        if "id" in user_data: return user_data["name"], user_data["displayName"], user_data["hasVerifiedBadge"]
        else: raise ErrorDict.DoesNotExistError
    else: raise ErrorDict.DoesNotExistError

async def check_verification(user_id:int) -> int:
    verifhat, verifsign = await asyncio.gather(Roquest.Roquest("GET", "inventory", f"v1/users/{user_id}/items/4/102611803"),Roquest.Roquest("GET", "inventory", f"v1/users/{user_id}/items/4/1567446"))
    await asyncio.gather(general_error_handler(verifhat[0]), general_error_handler(verifsign[0]))
    hatOwned = any("type" in item for item in verifhat[1].get("data", []))
    signOwned = any("type" in item for item in verifsign[1].get("data", []))
    return 4 if hatOwned and signOwned else 1 if hatOwned else 2 if signOwned else 3

async def last_online(user_id:int):
    last_data = await Roquest.Roquest("POST", "presence", "v1/presence/last-online", failRetry=True, json={"userIds": [user_id]})
    await general_error_handler(last_data[0])
    return last_data[1]["lastOnlineTimestamps"][0]["lastOnline"]

async def get_player_thumbnail(user_id:int, size):
    thumbnail_url = await Roquest.Roquest("GET", "thumbnails", f"v1/users/avatar?userIds={user_id}&size={size}&format=Png&isCircular=false")
    if thumbnail_url[0] != 200: return "https://www.robloxians.com/resources/not-available.png"
    elif thumbnail_url[1]["data"][0]["state"] == "Blocked": return "https://robloxians.com/resources/blocked.png"
    else: return thumbnail_url[1]["data"][0]["imageUrl"]


async def get_item_thumbnail(item_id:int, size):
    thumbnail_url = await Roquest.Roquest("GET", "thumbnails", f"v1/assets?assetIds={item_id}&returnPolicy=PlaceHolder&size={size}&format=Png&isCircular=false", failRetry=True)
    if thumbnail_url[0] != 200: return "https://www.robloxians.com/resources/not-available.png"
    elif thumbnail_url[1]["data"][0]["state"] == "Blocked": return "https://robloxians.com/resources/blocked.png"
    else: return thumbnail_url[1]["data"][0]["imageUrl"]

async def get_player_profile(user_id:int) -> tuple[str, str, bool, str, str, bool]: 
    """Returns description, joined, banned, username, display name, verified"""
    desc = await Roquest.Roquest("GET", "users", f"v1/users/{user_id}")
    await general_error_handler(desc[0], 200)
    return desc[1]["description"], desc[1]["created"], desc[1]["isBanned"], desc[1]["name"], desc[1]["displayName"], desc[1]["hasVerifiedBadge"]

async def get_previous_usernames(user_id:int):
    usernames = []
    next_page_cursor = None
    while True:
        url = f"v1/users/{user_id}/username-history?limit=100&sortOrder=Asc"
        if next_page_cursor:
            url += f"&cursor={next_page_cursor}"
        data = await Roquest.Roquest("GET", "users", url)
        await general_error_handler(data[0])
        usernames += [entry["name"] for entry in data[1]["data"]]
        next_page_cursor = data[1].get("nextPageCursor")
        if not next_page_cursor: break
    return usernames

async def get_group_count(user_id:int) -> int:
    gdata = await Roquest.Roquest("GET", "groups", f"v2/users/{user_id}/groups/roles?includeLocked=true")
    await general_error_handler(gdata[0])
    return len(gdata[1]['data'])
    
async def get_socials(user_id:int) -> tuple[int, int, int]:
    """Returns Friends, Followers, Following"""
    friend_count, following_count, follow_count = await asyncio.gather(Roquest.Roquest("GET", "friends", f"v1/users/{user_id}/friends/count"),Roquest.Roquest("GET", "friends", f"v1/users/{user_id}/followings/count"),Roquest.Roquest("GET", "friends", f"v1/users/{user_id}/followers/count"))
    await asyncio.gather(general_error_handler(friend_count[0]),general_error_handler(following_count[0]),general_error_handler(follow_count[0]))
    return friend_count[1]["count"], follow_count[1]["count"], following_count[1]["count"]

async def get_friends(user_id:int):
    friend_data = await Roquest.Roquest("GET", "friends", f"v1/users/{user_id}/friends?userSort=0")
    await general_error_handler(friend_data[0])
    return friend_data[1]

async def get_groups(user_id:int):
    group_data = await Roquest.Roquest("GET", "groups", f"v1/users/{user_id}/groups/roles")
    await general_error_handler(group_data[0])
    return group_data[1]
    
async def get_player_headshot(user_id:int, size):
    thumbnail_url = await Roquest.Roquest("GET", "thumbnails", f"v1/users/avatar-headshot?userIds={user_id}&size={size}&format=Png&isCircular=false", failRetry=True)
    if thumbnail_url[0] != 200: return "https://www.robloxians.com/resources/not-available.png"
    elif thumbnail_url[1]["data"][0]["state"] == "Blocked": return "https://robloxians.com/resources/blocked.png"
    else: return thumbnail_url[1]["data"][0]["imageUrl"]
    
async def get_badge_thumbnail(badge_id:int):
    thumbnail_url = await Roquest.Roquest("GET", "thumbnails", f"v1/badges/icons?badgeIds={badge_id}&size=150x150&format=Png&isCircular=false", failRetry=True)
    if thumbnail_url[0] != 200: return "https://www.robloxians.com/resources/not-available.png"
    elif thumbnail_url[1]["data"][0]["state"] == "Blocked": return "https://robloxians.com/resources/blocked.png"
    else: return thumbnail_url[1]["data"][0]["imageUrl"]

async def get_group_emblem(group:int, size):
    thumbnail_url = await Roquest.Roquest("GET", "thumbnails", f"v1/groups/icons?groupIds={group}&size={size}&format=Png&isCircular=false", failRetry=True)
    if thumbnail_url[0] != 200: return "https://www.robloxians.com/resources/not-available.png"
    elif thumbnail_url[1]["data"][0]["state"] == "Blocked": return "https://robloxians.com/resources/blocked.png"
    else: return thumbnail_url[1]["data"][0]["imageUrl"]

async def get_rolidata_from_item(rolidata, item) -> tuple[int, str, str, int, int]: 
    """Returns limited id, name, acronym, rap, and value"""
    for limited_id, item_data in rolidata["items"].items():
        if item.lower() in [item_data[0].lower(), item_data[1].lower(), limited_id]: return limited_id, item_data[0], item_data[1], item_data[2], item_data[4]
    else: raise ErrorDict.DoesNotExistError

async def get_membership(user:int) -> tuple[bool, bool, bool, bool]:
    """Returns hasPremium, ownedBc, ownedTbc, and ownedObc"""
    checkBc = await Roquest.Roquest("GET", "inventory", f"v1/users/{user}/items/4/24814192")
    await general_error_handler(checkBc[0])
    checkPremium, checkTbc, checkObc = await asyncio.gather(Roquest.Roquest("GET", "premiumfeatures", f"v1/users/{user}/validate-membership"),Roquest.Roquest("GET", "inventory", f"v1/users/{user}/items/4/11895536"),Roquest.Roquest("GET", "inventory", f"v1/users/{user}/items/4/17407931"))
    await asyncio.gather(general_error_handler(checkPremium[0]), general_error_handler(checkObc[0]), general_error_handler(checkTbc[0]))
    ownedBc = any("type" in item for item in checkBc[1].get("data", []))
    ownedTbc = any("type" in item for item in checkTbc[1].get("data", []))
    ownedObc =  any("type" in item for item in checkObc[1].get("data", []))
    return checkPremium[1], ownedBc, ownedTbc, ownedObc

async def get_group(group:int) -> tuple[str, str, str, bool, tuple[str, int, bool], str, int, bool, bool]: 
    """Returns name (0), description (1), created (2), verified (3), owner (4), shout (5), members (6), public (7), isLocked (8)"""
    getGroup, getGroupV1 = await asyncio.gather(Roquest.Roquest("GET", "groups", f"v2/groups?groupIds={group}"),Roquest.Roquest("GET", "groups", f"v1/groups/{group}"))
    await asyncio.gather(general_error_handler(getGroup[0]), general_error_handler(getGroupV1[0]))
    groupName = getGroup[1]['data'][0]['name']
    groupDescription = getGroup[1]['data'][0]['description']
    groupCreated = getGroup[1]['data'][0]['created']
    groupVerified = getGroup[1]['data'][0]['hasVerifiedBadge']
    if getGroupV1[1]['owner'] is not None:
        if getGroupV1[1]['owner']['username'] is None: groupOwner = [False, False, False]
        else: groupOwner = [getGroupV1[1]['owner']['username'], getGroupV1[1]['owner']['userId'], getGroupV1[1]['owner']['hasVerifiedBadge']]
    else: groupowner = [False, False, False]
    if getGroupV1[1]['shout'] is None: groupShout = [False, False, False]
    else: groupShout = [getGroupV1[1]['shout']['body'], getGroupV1[1]['shout']['poster']['username'], getGroupV1[1]['shout']['poster']['userId'], getGroupV1[1]['shout']['poster']['hasVerifiedBadge']]
    groupMembers = getGroupV1[1]['memberCount']
    groupPublic = getGroupV1[1]['publicEntryAllowed']
    if 'groupLocked' in getGroupV1[1]: groupLocked = getGroupV1[1]['isLocked']
    else: groupLocked = False
    return groupName, groupDescription, groupCreated, groupVerified, groupOwner, groupShout, groupMembers, groupPublic, groupLocked

async def validate_username(username:str) -> tuple[int,str]:
    """Validate if a username is available"""
    data = await Roquest.Roquest("POST", "auth", f"v2/usernames/validate", json={"username": username,"birthday": "2000-01-01T00:00:00.000Z","context": 0})
    await general_error_handler(data[0])
    return data[1]['code'], data[1]['message']

async def nil_pointer() -> int: 
    """Returns nil data"""
    return 0