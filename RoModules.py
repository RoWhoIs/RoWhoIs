import Roquest, asyncio
from logger import AsyncLogCollector
log_collector = AsyncLogCollector("logs/RoModules.log")

async def convert_to_id(username): # Returns user id, username, display name, verified badge
    try:
        userid = await Roquest.Roquest("POST", "https://users.roblox.com/v1/usernames/users", json={"usernames": [username],"excludeBannedUsers": False})
        if userid[0] in [-1, 403]: return -2, -2, -2, -2
        elif userid[0] in [404, 400]: return -1, -1, -1, -1
        if "data" in userid[1] and userid[1]["data"]:
            user_data = userid[1]["data"][0]
            if "id" in user_data and "name" in user_data: return user_data["id"], user_data["name"], user_data["displayName"], user_data["hasVerifiedBadge"]
            else: return -1, -1, -1, -1
        else: return -1, -1, -1, -1
    except Exception as e:
        await log_collector.error(f"Encountered an error while running the convert_to_id function: {e}")
        return -2, -2, -2, -2
        
async def convert_to_username(userid:int):
    try:
        userid = await Roquest.Roquest("POST", "https://users.roblox.com/v1/users", json={"userIds": [userid],"excludeBannedUsers": False})
        if userid[0] in [-1, 403]: return -2, -2
        elif userid[0] in [404, 400]: return -1, -1
        if "data" in userid[1] and userid[1]["data"]:
            user_data = userid[1]["data"][0]
            if "id" in user_data: return user_data["name"], user_data["displayName"], user_data["hasVerifiedBadge"]
            else: return -1, -1, -1
        else: return -1, -1, -1
    except Exception as e:
        await log_collector.error(f"Encountered an error while running the convert_to_id function: {e}")
        return -2, -2

async def check_verification(user_id:int):
    try:
        verifhat, verifsign = await asyncio.gather(
            Roquest.Roquest("GET", f"https://inventory.roblox.com/v1/users/{user_id}/items/4/102611803"),
            Roquest.Roquest("GET", f"https://inventory.roblox.com/v1/users/{user_id}/items/4/1567446")
        )
        hat_owned = verifhat[0] not in [-1, 403, 400, 404] and any("type" in item for item in verifhat[1].get("data", []))
        sign_owned = verifsign[0] not in [-1, 403, 400, 404] and any("type" in item for item in verifsign[1].get("data", []))
        return 4 if hat_owned and sign_owned else 1 if hat_owned else 2 if sign_owned else 3
    except Exception as e:
        await log_collector.error(f"Encountered an error while running the check_verification function: {e}")
        return -1

async def last_online(user_id:int):
    try:
        last_data = await Roquest.Roquest("POST", "https://presence.roblox.com/v1/presence/last-online", json={"userIds": [user_id]})
        if last_data[0] in [-1, 403]: return -2
        elif last_data[0] in [404, 400]: return -1
        else: return last_data[1]["lastOnlineTimestamps"][0]["lastOnline"]
    except Exception as e:
        await log_collector.error(f"Encountered an error while running the last_online function: {e}")
        return -1

async def get_player_thumbnail(user_id:int, size):
    try:
        thumbnail_url = await Roquest.Roquest("GET", f"https://thumbnails.roblox.com/v1/users/avatar?userIds={user_id}&size={size}&format=Png&isCircular=false")
        if thumbnail_url[0] in [-1, 403]: return -2
        elif thumbnail_url[0] in [404, 400]: return -1
        elif thumbnail_url[1]["data"][0]["state"] == "Blocked": return "https://robloxians.com/resources/blocked.png"
        else: return thumbnail_url[1]["data"][0]["imageUrl"]
    except Exception as e:
        await log_collector.error(f"Encountered an error while running the get_player_thumbnail function: {e}")
        return -2

async def get_item_thumbnail(item_id:int, size):
    try:
        thumbnail_url = await Roquest.Roquest("GET", f"https://thumbnails.roblox.com/v1/assets?assetIds={item_id}&returnPolicy=PlaceHolder&size={size}&format=Png&isCircular=false")
        if thumbnail_url[0] in [-1, 403]: return -2
        elif thumbnail_url[0] in [404, 400]: return -1
        elif thumbnail_url[1]["data"][0]["state"] == "Blocked": return "https://robloxians.com/resources/blocked.png"
        else: return thumbnail_url[1]["data"][0]["imageUrl"]
    except Exception as e:
        await log_collector.error(f"Encountered an error while running the get_item_thumbnail function: {e}")
        return -2

async def get_player_profile(user_id:int): # Returns description, joined, banned, username, display name, verified
    try:
        desc = await Roquest.Roquest("GET", f"https://users.roblox.com/v1/users/{user_id}")
        if desc[0] in [-1, 403]: return -2, -2, -2, -2, -2, -2
        elif desc[0] in [400, 404]: return -1, -1, -1, -1, -1, -1
        else: return desc[1]["description"], desc[1]["created"], desc[1]["isBanned"], desc[1]["name"], desc[1]["displayName"], desc[1]["hasVerifiedBadge"]
    except Exception as e:
        await log_collector.error(f"Encountered an error while running the get_player_profile function: {e}")
        return -2, -2, -2, -2, -2, -2
    
async def get_previous_usernames(user_id:int):
    try:
        usernames = []
        next_page_cursor = None
        while True:
            url = f"https://users.roblox.com/v1/users/{user_id}/username-history?limit=100&sortOrder=Asc"
            if next_page_cursor:
                url += f"&cursor={next_page_cursor}"
            data = await Roquest.Roquest("GET", url)
            if data[0] in [-1, 403]: return -2
            elif data[0] in [400, 404]: return -1
            usernames += [entry["name"] for entry in data[1]["data"]]
            next_page_cursor = data[1].get("nextPageCursor")
            if not next_page_cursor: break
        return usernames
    except Exception as e:
        await log_collector.error(f"Encountered an error while running the get_previous_usernames function: {e}")
        return -2

async def get_group_count(user_id:int):
    try:
        gdata = await Roquest.Roquest("GET", f"https://groups.roblox.com/v2/users/{user_id}/groups/roles?includeLocked=true")
        if gdata[0] in [-1, 403]: return -2
        elif gdata[0] in [400, 404]: return -1
        else: return len(gdata[1]['data'])
    except Exception as e:
        await log_collector.error(f"Encountered an error while running the get_group_count function: {e}")
        return -2
    
async def get_socials(user_id:int): # Returns Friends, Followers, Following
    try:
        friend_count, following_count, follow_count = await asyncio.gather(
            Roquest.Roquest("GET", f"https://friends.roblox.com/v1/users/{user_id}/friends/count"),
            Roquest.Roquest("GET", f"https://friends.roblox.com/v1/users/{user_id}/followings/count"),
            Roquest.Roquest("GET", f"https://friends.roblox.com/v1/users/{user_id}/followers/count")
        )
        if friend_count[0] in [-1, 403]: return -2, -2, -2
        elif friend_count[0] in [400, 404]: return -1, -1, -1
        if following_count[0] in [-1, 403]: return -2, -2, -2
        elif following_count[0] in [400, 404]: return -1, -1, -1
        if follow_count[0] in [-1, 403]: return -2, -2, -2
        elif follow_count[0] in [400, 404]: return -1, -1, -1
        return friend_count[1]["count"], follow_count[1]["count"], following_count[1]["count"]
    except Exception as e:
        await log_collector.error(f"Encountered an error while running the get_socials function: {e}")
        return -2
    
async def get_friends(user_id:int):
    try:
        friend_data = await Roquest.Roquest("GET", f"https://friends.roblox.com/v1/users/{user_id}/friends?userSort=0")
        if friend_data[0] in [-1, 403]: return -2
        elif friend_data[0] in [404, 400]: return -1
        else: return friend_data[1]
    except Exception as e:
        await log_collector.error(f"Encountered an error while running the get_friends function: {e}")
        return -2

async def get_groups(user_id:int):
    try:
        group_data = await Roquest.Roquest("GET", f"https://groups.roblox.com/v1/users/{user_id}/groups/roles")
        if group_data[0] in [-1, 403]: return -2
        elif group_data[0] in [404, 400]: return -1
        else: return group_data[1]
    except Exception as e:
        await log_collector.error(f"Encountered an error while running the get_groups function: {e}")
        return -2
    
async def get_player_headshot(user_id:int, size):
    try:
        thumbnail_url = await Roquest.Roquest("GET", f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size={size}&format=Png&isCircular=false")
        if thumbnail_url[0] in [-1, 403]: return -2
        elif thumbnail_url[0] in [404, 400]: return -1
        elif thumbnail_url[1]["data"][0]["state"] == "Blocked": return "https://robloxians.com/resources/blocked.png"
        else: return thumbnail_url[1]["data"][0]["imageUrl"]
    except Exception as e:
        await log_collector.error(f"Encountered an error while running the get_player_headshot function: {e}")
        return -2
    
async def get_badge_thumbnail(badge_id:int):
    try:
        thumbnail_url = await Roquest.Roquest("GET", f"https://thumbnails.roblox.com/v1/badges/icons?badgeIds={badge_id}&size=150x150&format=Png&isCircular=false")
        if thumbnail_url[0] in [-1, 403]: return -2
        elif thumbnail_url[0] in [404, 400]: return -1
        elif thumbnail_url[1]["data"][0]["state"] == "Blocked": return "https://robloxians.com/resources/blocked.png"
        else: return thumbnail_url[1]["data"][0]["imageUrl"]
    except Exception as e:
        await log_collector.error(f"Encountered an error while running the get_badge_thumbnail function: {e}")
        return -2
    
async def get_group_emblem(group:int, size):
    try:
        thumbnail_url = await Roquest.Roquest("GET", f"https://thumbnails.roblox.com/v1/groups/icons?groupIds={group}&size={size}&format=Png&isCircular=false")
        if thumbnail_url[0] in [-1, 403]: return -2
        elif thumbnail_url[0] in [404, 400]: return -1
        elif thumbnail_url[1]["data"][0]["state"] == "Blocked": return "https://robloxians.com/resources/blocked.png"
        else: return thumbnail_url[1]["data"][0]["imageUrl"]
    except Exception as e:
        await log_collector.error(f"Encountered an error while running the get_group_emblem function: {e}")
        return -2

async def get_rolidata_from_item(rolidata, item): # Returns limited id, name, acronym, rap, and value
    for limited_id, item_data in rolidata["items"].items():
        if item.lower() in [item_data[0].lower(), item_data[1].lower(), limited_id]:
            return limited_id, item_data[0], item_data[1], item_data[2], item_data[4]
    else: return -1, -1, -1, -1, -1

async def get_membership(user:int): # Returns successType, hasPremium, ownedBc, ownedTbc, and ownedObc
    checkBc = await Roquest.Roquest("GET", f"https://inventory.roblox.com/v1/users/{user}/items/4/24814192")
    if checkBc[0] != 200:
        if checkBc[1]['errors'][0]['message'] == "The specified user does not exist!": return False, False, False, False, False
    checkPremium, checkTbc, checkObc = await asyncio.gather(Roquest.Roquest("GET", f"https://premiumfeatures.roblox.com/v1/users/{user}/validate-membership"),Roquest.Roquest("GET", f"https://inventory.roblox.com/v1/users/{user}/items/4/11895536"),Roquest.Roquest("GET", f"https://inventory.roblox.com/v1/users/{user}/items/4/17407931"))
    hasPremium = checkPremium[0] not in [-1, 403, 400, 404] and checkPremium[1] == True
    ownedBc = checkBc[0] not in [-1, 403, 400, 404] and any("type" in item for item in checkBc[1].get("data", []))
    ownedTbc = checkTbc[0] not in [-1, 403, 400, 404] and any("type" in item for item in checkTbc[1].get("data", []))
    ownedObc =  checkObc[0] not in [-1, 403, 400, 404] and any("type" in item for item in checkObc[1].get("data", []))
    return True, hasPremium, ownedBc, ownedTbc, ownedObc

async def get_group(group:int): # Returns name (0), description (1), created (2), verified (3), owner (4), shout (5), members (6), public (7), isLocked (8)
    try:
        getGroup, getGroupV1 = await asyncio.gather(Roquest.Roquest("GET", f"https://groups.roblox.com/v2/groups?groupIds={group}"),Roquest.Roquest("GET", f"https://groups.roblox.com/v1/groups/{group}"))
        if getGroup[0] == 200 and getGroupV1[0] == 200:
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
        else: return False, False, False, False, False, False, False, False, False, False
    except Exception as e:
        await log_collector.error(f"Encountered an error while running the get_groups function: {e}")
        return -1, -1, -1, -1, -1, -1, -1, -1, -1, -1

async def nil_pointer(): return 0 #Returns nil data