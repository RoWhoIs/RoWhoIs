import Roquest, RoModules, ErrorDict
import asyncio, discord, aiofiles, re, io, aiohttp, signal
from secret import RWI
from logger import AsyncLogCollector
from datetime import datetime

testingMode = None

def main(testing_mode:bool, staff_ids, opt_out, user_blocklist, log_config_updates:bool, short_hash:str):
    global testingMode, staffIds, optOut, userBlocklist, logConfigUpdates, shortHash, client, loop
    testingMode, staffIds, optOut, userBlocklist, logConfigUpdates, shortHash = testing_mode, staff_ids, opt_out, user_blocklist, log_config_updates, short_hash
    if testingMode:loop.run_until_complete(client.start(RWI.TESTING))
    else: loop.run_until_complete(client.start(RWI.PRODUCTION))

log_collector = AsyncLogCollector("logs/RoWhoIs.log")
class RoWhoIs(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = discord.app_commands.CommandTree(self)
    async def setup_hook(self): await self.tree.sync(guild=None)
    
async def shutdown(loop:asyncio.BaseEventLoop): # Will cause event loop stopped before future error if ran during init
    await log_collector.info("Gracefully shutting down RoWhoIs...")
    await discord.Client.close(client)
    for task in asyncio.all_tasks(loop): task.cancel()
    loop.stop()

async def update_rolidata() -> None:
    global RoliData
    while True:
        try:
            RoliData = await Roquest.RoliData()
            if RoliData != -1: 
                if logConfigUpdates: await log_collector.info("Rolimons data updated successfully.")
            else: await log_collector.error("Failed to update Rolimons data.")
        except Exception as e: await log_collector.error(f"Error updating Rolimons data: {e}")
        await asyncio.sleep(3600)

async def fancy_time(last_online_timestamp: str) -> str:
    try:
        try: last_online_datetime = datetime.strptime(last_online_timestamp, "%Y-%m-%dT%H:%M:%S.%fZ")
        except ValueError:
            try: last_online_datetime = datetime.strptime(last_online_timestamp, "%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                data = str(last_online_timestamp)
                microseconds = int(data[-7:-1])
                last_online_datetime = datetime.strptime(data[:-7] + 'Z', "%Y-%m-%dT%H:%M:%S.%fZ").replace(microsecond=microseconds)
        current_datetime = datetime.utcnow()
        time_difference = current_datetime - last_online_datetime
        time_units = [("year", 12, time_difference.days // 365), ("month", 1, time_difference.days // 30),  ("week", 7, time_difference.days // 7), ("day", 1, time_difference.days), ("hour", 60, time_difference.seconds // 3600), ("minute", 60, time_difference.seconds // 60), ("second", 1, time_difference.seconds)]
        for unit, _, value in time_units:
            if value > 0:
                last_online_formatted = f"{value} {unit + 's' if value != 1 else unit} ago"
                break
        else: last_online_formatted = f"{time_difference.seconds} {'second' if time_difference.seconds == 1 else 'seconds'} ago"
        last_online_formatted += f" ({last_online_datetime.strftime('%m/%d/%Y %H:%M:%S')})"
        return last_online_formatted
    except Exception as e:
        await log_collector.error(f"Error formatting time: {e} | Returning fallback data: {last_online_timestamp}")
        return last_online_timestamp

async def validate_user(interaction: discord.Interaction, embed: discord.Embed, userId: int = None) -> bool:
    """Check a Discord or Roblox user ID against blocklists."""
    global optOut, userBlocklist
    if interaction.user.id in userBlocklist:
        await log_collector.warn(f"Blocklist user {interaction.user.id} attempted to call a command and was denied!")
        embed.description = "You have been permanently banned from using RoWhoIs. In accordance to our [Terms of Service](https://www.robloxians.com/Terms-Of-Service/), we reserve the right to block any user from using our service."
    elif userId and userId in optOut:
        await log_collector.warn(f"Blocklist user {userId} was requested by {interaction.user.id} and denied!")
        embed.description = "This user has requested to opt-out of RoWhoIs."
    else: return True
    embed.title = None
    embed.color = 0xFF0000
    await interaction.followup.send(embed=embed, ephemeral=True)
    return False

async def handle_error(error, interaction:discord.Interaction, command:str, context:str="Requested resource") -> None:
    """Handles both user-facing and backend errors, even if they are undocumented."""
    embed = discord.Embed(color=0xFF0000)
    if type(error) == ErrorDict.DoesNotExistError: embed.description = f"{context} doesn't exist."
    elif type(error) == ErrorDict.MismatchedDataError: embed.description = f"{context} is invalid."
    elif type(error) == ErrorDict.RatelimitedError: embed.description = "RoWhoIs is experienceing unusually high demand. Please try again."
    else: 
        if type(error) == ErrorDict.InvalidAuthorizationError: await Roquest.token_renewal()
        embed.description = "Whoops! An unknown error occurred. Please try again later."
        await log_collector.error(f"Error in the {command} command: {error}")
    await interaction.followup.send(embed=embed, ephemeral=True)
    return True

async def safe_wrapper(task, *args):
    """Allows asyncio.gather to continue even if a thread throws an exception"""
    try: return await task(*args)
    except Exception as e: return e

client = RoWhoIs(intents=discord.Intents.default())
loop = asyncio.get_event_loop()
loop.create_task(update_rolidata())
loop.add_signal_handler(signal.SIGINT, lambda: asyncio.create_task(shutdown(loop)))

@client.event
async def on_ready():
    await log_collector.info(f'RoWhoIs initialized! Logged in as {client.user} (ID: {client.user.id})')
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="over Robloxia"))

@client.event
async def on_guild_join(guild): # How's this for conciseness? LOL!
    if not testingMode:
        try:
            await log_collector.info(f"RoWhoIs has joined a new server. Total servers: {len(client.guilds)}. Updating registries...")
            async with aiohttp.ClientSession() as session:
                if RWI.TOPGG != "": 
                    async with session.post(f"https://top.gg/api/bots/{client.user.id}/stats", headers={"Authorization":RWI.TOPGG}, json={"server_count":len(client.guilds)}) as response: pass
                if RWI.DBL != "":
                    async with session.post(f"https://discordbotlist.com/api/v1/bots/{client.user.id}/stats", headers={"Authorization":RWI.DBL}, json={"guilds":len(client.guilds)}) as response: pass
        except Exception as e: await log_collector.error(f"Failed to update registries. {e}")

@client.tree.command()
@discord.app_commands.checks.cooldown(3, 60, key=lambda i: (i.user.id))
async def help(interaction: discord.Interaction):
    """List all of the commands RoWhoIs supports & what they do"""
    await interaction.response.defer(ephemeral=False)
    embedVar = discord.Embed(title="RoWhoIs Commands", color=discord.Color.from_rgb(135, 136, 138))
    if not (await validate_user(interaction, embedVar)): return
    embedVar.add_field(name="whois {UserId}/{username}", value="Get detailed profile information from a User ID/Username.", inline=True)
    embedVar.add_field(name="getclothingtexture {itemId}", value="Retrieves the texture file for a 2D clothing asset.", inline=True)
    embedVar.add_field(name="userid {Username}", value="Get a User ID based off a username.", inline=True)
    embedVar.add_field(name="ownsitem {UserId}/{username}, {itemId}", value="Retrieve whether a user owns an item or not. Works with players who have a private inventory.", inline=True)
    embedVar.add_field(name="ownsbadge {UserId}/{username}, {badgeId}", value="Retrieve whether a user owns a badge or not. Works with players who have a private inventory.", inline=True)
    embedVar.add_field(name="isfriendswith {user1}, {user2}", value="Check if two players are friended.", inline=True)
    embedVar.add_field(name="group {groupId}", value="Get detailed group information from a Group ID.", inline=True)
    embedVar.add_field(name="isingroup {user}, {group}", value="Check if a player is in the specified group.", inline=True)
    embedVar.add_field(name="limited {limited name}/{limited acronym}", value="Returns a limited ID, the rap, and value of the specified limited.", inline=True)
    embedVar.add_field(name="getitemdetails {item}", value="Returns details about a catalog item.", inline=True)
    embedVar.add_field(name="getmembership {userId}/{username}", value="Check if a player has Premium or has had Builders Club.", inline=True)
    embedVar.add_field(name="checkusername {username}", value="Check if a username is available", inline=True)
    embedVar.set_footer(text=f"Version {shortHash}")
    await interaction.followup.send(embed=embedVar)

@client.tree.error
async def on_app_command_error(interaction: discord.Interaction,error: discord.app_commands.AppCommandError):
    if isinstance(error, discord.app_commands.CommandOnCooldown): await interaction.response.send_message(f"Your enthusiasm is greatly appreciated, but please slow down! Try again in {round(error.retry_after)} seconds.", ephemeral=True)
    else:
        await log_collector.fatal(f"Unexpected error occured during core command function: {error}")
        await interaction.followup.send(f"Whoops! Looks like we encountered an unexpected error. We've reported this to our dev team and we'll fix it shortly!", ephemeral=True)
        
@client.tree.command()
@discord.app_commands.checks.cooldown(5, 60, key=lambda i: (i.user.id))
async def userid(interaction: discord.Interaction, username: str):
    """Get a User ID from a username"""
    await interaction.response.defer(ephemeral=False)
    try:
        embed = discord.Embed(color=0xFF0000)
        if not (await validate_user(interaction, embed)): return
        try: user_id = await RoModules.convert_to_id(username)
        except Exception as e: 
            if (await handle_error(e, interaction, "userid", "User")): return
        if not (await validate_user(interaction, embed, user_id[0])): return
        if user_id[1] == user_id[2]: embed.title = f"{user_id[1]} {'<:RoWhoIsStaff:1186713381038719077>' if user_id[0] in staffIds else '<:verified:1186711315679563886>' if user_id[3] else ''}"
        else: embed.title = f"{user_id[1]} ({user_id[2]}) {'<:RoWhoIsStaff:1186713381038719077>' if user_id[0] in staffIds else '<:verified:1186711315679563886>' if user_id[3] else ''}"
        embed.description = f"**User ID:** `{user_id[0]}`"
        embed.url = f"https://www.roblox.com/users/{user_id[0]}/profile"
        user_thumbnail = await RoModules.get_player_headshot(user_id[0], "420x420")
        if user_thumbnail: embed.set_thumbnail(url=user_thumbnail)
        embed.color = 0x00FF00
        await interaction.followup.send(embed=embed)
    except Exception as e: await handle_error(e, interaction, "userid", "User")
        
@client.tree.command()
@discord.app_commands.checks.cooldown(5, 60, key=lambda i: (i.user.id))
async def username(interaction: discord.Interaction, userid: int):
    """Get a username from a User ID"""
    await interaction.response.defer(ephemeral=False)
    try:
        embed = discord.Embed(color=0xFF0000)
        if not (await validate_user(interaction, embed, userid)): return
        try: username = await RoModules.convert_to_username(userid)
        except Exception as e:
            if (await handle_error(e, interaction, "username", "User")): return
        if username[0] == username[1]: embed.title = f"{username[0]} {'<:RoWhoIsStaff:1186713381038719077>' if userid in staffIds else '<:verified:1186711315679563886>' if username[2] else ''}"
        else: embed.title = f"{username[0]} ({username[1]}) {'<:RoWhoIsStaff:1186713381038719077>' if userid in staffIds else '<:verified:1186711315679563886>' if username[2] else ''}"
        embed.description = f"**Username:** `{username[0]}`"
        embed.url = f"https://www.roblox.com/users/{userid}/profile"
        user_thumbnail = await RoModules.get_player_headshot(userid, "420x420")
        if user_thumbnail: embed.set_thumbnail(url=user_thumbnail)
        embed.color = 0x00FF00
        await interaction.followup.send(embed=embed)
    except Exception as e: await handle_error(e, interaction, "username", "User")

@client.tree.command()
@discord.app_commands.checks.cooldown(3, 60, key=lambda i: (i.user.id))
async def whois(interaction: discord.Interaction, user: str):
    """Get detailed profile information from a User ID/Username"""
    await interaction.response.defer(ephemeral=False)
    try:
        embed = discord.Embed(color=0xFF0000)
        if not (await validate_user(interaction, embed)): return
        userId = [int(user), None] if user.isdigit() else await RoModules.convert_to_id(user)
        if not (await validate_user(interaction, embed, userId[0])): return
        try: description, created, banned, name, displayname, verified = await RoModules.get_player_profile(userId[0])
        except Exception as e:
            if (await handle_error(e, interaction, "whois", "User")): return
        if banned or userId[0] == 1: tasks = [RoModules.nil_pointer(),RoModules.nil_pointer(),safe_wrapper(RoModules.get_player_thumbnail, userId[0], "420x420"),safe_wrapper(RoModules.last_online, userId[0]),safe_wrapper(RoModules.get_group_count, userId[0]),safe_wrapper(RoModules.get_socials, userId[0])]
        else: tasks = [safe_wrapper(RoModules.get_previous_usernames, userId[0]),safe_wrapper(RoModules.check_verification, userId[0]),safe_wrapper(RoModules.get_player_thumbnail, userId[0], "420x420"),safe_wrapper(RoModules.last_online, userId[0]),safe_wrapper(RoModules.get_group_count, userId[0]),safe_wrapper(RoModules.get_socials, userId[0])]
        previous_usernames, veriftype, user_thumbnail, unformattedLastOnline, groups, (friends, followers, following) = await asyncio.gather(*tasks)
        if banned or userId[0] == 1: veriftype, previous_usernames = None, []
        if user_thumbnail: embed.set_thumbnail(url=user_thumbnail)
        if banned == True: private_inventory = True 
        else: private_inventory = True
        last_online_formatted = await fancy_time(unformattedLastOnline)
        joined_timestamp = await fancy_time(created)
        total_rap, total_value, cursor = 0, 0, ""
        while not banned and userId[0] != 1:
            rap = await Roquest.Roquest("GET", "inventory", f"v1/users/{userId[0]}/assets/collectibles?limit=100&sortOrder=Asc&cursor={cursor}")
            if rap[0] == 403:
                private_inventory = True
                break
            else: private_inventory = False
            data = rap[1].get("data", [])
            if not data: break
            for item in data:
                assetId = str(item.get("assetId", 0))
                if assetId in RoliData['items']:
                    item_value = RoliData['items'][assetId][4]
                    if item_value is not None: total_value += item_value
                rap_value = item.get("recentAveragePrice", 0)
                if rap_value is not None:
                    total_rap += rap_value
            cursor = rap[1].get("nextPageCursor")
            if not cursor: break
        if name == displayname: embed.title = f"{name} {'<:RoWhoIsStaff:1186713381038719077>' if userId[0] in staffIds else '<:verified:1186711315679563886>' if verified else ''}"
        else: embed.title = f"{name} ({displayname}) {'<:RoWhoIsStaff:1186713381038719077>' if userId[0] in staffIds else '<:verified:1186711315679563886>' if verified else ''}"
        embed.color = 0x00ff00
        embed.url=f"https://www.roblox.com/users/{userId[0]}/profile" if not banned else None
        embed.add_field(name="User ID:", value=f"`{userId[0]}`", inline=True)
        embed.add_field(name="Account Status:", value="`Terminated`" if banned else "`Okay`" if not banned else "`N/A (*Nil*)`", inline=True)
        if previous_usernames:
            previous_usernames_str = ', '.join([f"`{username}`" for username in previous_usernames[:10]]) + (f", and {len(previous_usernames) - 10} more" if len(previous_usernames) > 10 else '')
            embed.add_field(name=f"Previous Usernames ({len(previous_usernames)}):", value=previous_usernames_str, inline=False)
        if veriftype is not None: embed.add_field(name="Verified Email:", value="`N/A (*Nil*)`" if veriftype == -1 else "`N/A (*-1*)`" if veriftype == 0 else "`Verified, hat present`" if veriftype == 1 else "`Verified, sign present`" if veriftype == 2 else "`Unverified`" if veriftype == 3 else "`Verified, sign & hat present`" if veriftype == 4 else "`N/A`", inline=True)
        if description: embed.add_field(name="Description:", value=f"`{description}`", inline=False)
        embed.add_field(name="Joined:", value=f"`{joined_timestamp}`", inline=True)
        embed.add_field(name="Last Online:", value=f"`{last_online_formatted}`", inline=True)
        if not private_inventory: 
            embed.add_field(name="Total RAP:", value=f"`{total_rap}`", inline=True)
            embed.add_field(name="Total Value:", value=f"`{total_value}`", inline=True)
        if not banned: embed.add_field(name="Privated Inventory:", value=f"`{private_inventory}`", inline=True)
        embed.add_field(name="Groups:", value=f"`{groups}`", inline=True)
        embed.add_field(name="Friends:", value=f"`{friends}`", inline=True)
        embed.add_field(name="Followers:", value=f"`{followers}`", inline=True)
        embed.add_field(name="Following:", value=f"`{following}`", inline=True)
        await interaction.followup.send(embed=embed)
    except Exception as e: await handle_error(e, interaction, "whois", "User")

@client.tree.command()
@discord.app_commands.checks.cooldown(3, 60, key=lambda i: (i.user.id))
async def ownsitem(interaction: discord.Interaction, user: str, item_id: int):
    """Check if a player owns a specific item"""
    await interaction.response.defer(ephemeral=False)
    embed = discord.Embed(color=0xFF0000)
    if not (await validate_user(interaction, embed)): return
    try:
        user_id = [int(user), None] if user.isdigit() else await RoModules.convert_to_id(user)
        if not (await validate_user(interaction, embed, user_id[0])): return
        if user_id[1] == None: user_id[1] = (await RoModules.get_player_profile(user_id[0]))[3]
        verifhat = await Roquest.Roquest("GET", "inventory", f"v1/users/{user_id[0]}/items/4/{item_id}")
        if verifhat[0] != 200:
            if 'errors' in verifhat[1]:
                if verifhat[1]['errors'][0]['message'] == "The specified user does not exist!":
                    embed.description = "User does not exist or has been banned."
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
                elif verifhat[0] in [404, 400]:
                    embed.description = "This item does not exist."
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
                else:
                    embed.description = verifhat[1]['errors'][0]['message']
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
            else:
                embed.description = "Whoops! An error occurred. Please try again later."
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
        if verifhat[1]["data"] and any("type" in item for item in verifhat[1]["data"]):
            item_name = verifhat[1]['data'][0]['name']
            total_items_owned = len(verifhat[1]['data'])
            uaid_list = [item["instanceId"] for item in verifhat[1]["data"][:50]]
            more_items = total_items_owned - 50
            thumbnail_url = await RoModules.get_item_thumbnail(item_id, "420x420")
            if thumbnail_url != -1: embed.set_thumbnail(url=thumbnail_url)
            embed.color = 0x00FF00
            embed.title = f"{user_id[1]} owns {total_items_owned} {item_name}{'s' if total_items_owned > 1 else ''}!"
            embed.description = "**UAIDs:**\n" + ', '.join([f"`{uaid}`" for uaid in map(str, uaid_list)])
            if more_items > 0: embed.description += f", and {more_items} more"
            await interaction.followup.send(embed=embed)
        else:
            embed.description = f"{(await RoModules.get_player_profile(user_id[0]))[3]} doesn't own the specified item!"
            await interaction.followup.send(embed=embed)
    except Exception as e: await handle_error(e, interaction, "ownsitem", "Item")

@client.tree.command()
@discord.app_commands.checks.cooldown(3, 60, key=lambda i: (i.user.id))
async def ownsbadge(interaction: discord.Interaction, user: str, badge_id: int):
    """Check if a player owns a specified badge and return it's award date"""
    await interaction.response.defer(ephemeral=False)
    embed = discord.Embed(color=0xFF0000)
    if not (await validate_user(interaction, embed)): return
    try:
        try: user_id = [int(user), None] if user.isdigit() else await RoModules.convert_to_id(user)
        except Exception as e: 
            if (await handle_error(e, interaction, "ownsbadge", "User")): return
        if not (await validate_user(interaction, embed, user_id[0])): return
        if user_id[1] == None: user_id[1] = (await RoModules.get_player_profile(user_id[0]))[3]
        try: verifhat = await Roquest.Roquest("GET", "badges", f"v1/users/{user_id[0]}/badges/awarded-dates?badgeIds={badge_id}")
        except Exception as e: 
            if (await handle_error(e, interaction, "ownsbadge", "Badge")): return
        if verifhat[1]["data"] and any("type" for item in verifhat[1]["data"][0]):
            awarded = verifhat[1]["data"][0]["awardedDate"]
            formatted_award = await fancy_time(awarded)
            thumbnail_url = await RoModules.get_badge_thumbnail(badge_id)
            if thumbnail_url not in [-1, -2]: embed.set_thumbnail(url=thumbnail_url)
            embed.color = 0x00FF00
            embed.title = f"{user_id[1]} owns this badge!"
            embed.description = f"Badge was awarded {formatted_award}"
            await interaction.followup.send(embed=embed)
        else:
            embed.description = f"{user_id[1]} doesn't own the specified badge!"
            await interaction.followup.send(embed=embed)
    except Exception as e: await handle_error(e, interaction, "ownsbadge", "Badge ID")

@client.tree.command()
@discord.app_commands.checks.cooldown(3, 60, key=lambda i: (i.user.id))
async def limited(interaction: discord.Interaction, limited: str):
    """Returns a limited ID, the rap, and value of a specified limited"""
    await interaction.response.defer(ephemeral=False)
    embed = discord.Embed(color=0xFF0000)
    if not (await validate_user(interaction, embed)): return
    try:
        try: limited_id, name, acronym, rap, value = await RoModules.get_rolidata_from_item(RoliData, limited)
        except Exception as e:  
            if (await handle_error(e, interaction, "limited", "Limited")): return
        if limited_id != -1:
            thumbnail_url = await RoModules.get_item_thumbnail(limited_id, "420x420")
            if thumbnail_url not in [-1, -2]: embed.set_thumbnail(url=thumbnail_url)
            embed.color = 0x00FF00
            embed.title = f"{name} ({acronym})" if acronym != "" else f"{name}"
            embed.url = f"https://www.roblox.com/catalog/{limited_id}/"
            embed.description = f"ID: `{limited_id}`\nRAP: `{rap}`\nValue: `{value}`"
            await interaction.followup.send(embed=embed)
        else:
            embed.description = f"Failed to find item! Make sure you spelled it correctly and used proper punctuation."
            await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as e: await handle_error(e, interaction, "limited", "Limited")

@client.tree.command()
@discord.app_commands.checks.cooldown(5, 60, key=lambda i: (i.user.id))
async def isfriendswith(interaction: discord.Interaction, user1: str, user2:str):
    """Check whether a user is friended to another user"""
    # Technically we only have to check through one player as it's a mutual relationship
    await interaction.response.defer(ephemeral=False)
    embed = discord.Embed(color=0xFF0000)
    if not (await validate_user(interaction, embed)): return
    try:
        user_id1 = [int(user1), None] if user1.isdigit() else await RoModules.convert_to_id(user1)
        if user2.isdigit(): user2 = int(user2) 
        if not (await validate_user(interaction, embed, user_id1[0])): return
        try: userfriends = await RoModules.get_friends(user_id1[0])
        except Exception as e: 
            if (await handle_error(e, interaction, "isfriendswith", "User")): return
        friended = False # Local variable 'friended' referenced before assignment 🤓
        if user_id1[1] == None: user_id1[1] = (await RoModules.get_player_profile(user_id1[0]))[3]
        for friends in userfriends['data']:
            if friends['id'] == user2 or friends['name'] == user2:
                if friends['id'] in optOut:
                    embed.description = "This user's friend has requested to opt-out of the RoWhoIs search."
                    await log_collector.warn(f"Opt-out user {user_id1[0]} was called by {interaction.user.id} and denied!")
                    await interaction.followup.send(embed=embed)
                    return
                friend_name = friends['name']
                friended = True
                break
            else: friended = False
        if friended:
            embed.color = 0x00FF00
            embed.description = (f"{user_id1[1]} is friends with {friend_name}!")
            await interaction.followup.send(embed=embed)
            return
        else:
            embed.description = (f"{user_id1[1]} does not have this user friended.")
            await interaction.followup.send(embed=embed)
            return
    except Exception as e: await handle_error(e, interaction, "isfriendswith", "User")
    
@client.tree.command()
@discord.app_commands.checks.cooldown(5, 60, key=lambda i: (i.user.id))
async def isingroup(interaction: discord.Interaction, user: str, group:int):
    """Check whether a user is in a group or not"""
    await interaction.response.defer(ephemeral=False)
    embed = discord.Embed(color=0xFF0000)
    if not (await validate_user(interaction, embed)): return
    try:
        try: user_id = [int(user), None] if user.isdigit() else await RoModules.convert_to_id(user)
        except Exception as e: 
            if (await handle_error(e, interaction, "isingroup", "User")): return
        if not (await validate_user(interaction, embed, user_id[0])): return
        try: 
            if user_id[1] == None: user_id[1] = (await RoModules.get_player_profile(user_id[0]))[3]
        except Exception as e: 
            if (await handle_error(e, interaction, "isingroup", "User")): return
        usergroups = await RoModules.get_groups(user_id[0])
        ingroup = False # Local variable 'ingroup' referenced before assignment 🤓
        if usergroups in [-2, -1]:
            await interaction.followup.send("Whoops! An error occurred. Please try again later.", ephemeral=True)
            return
        for groups in usergroups['data']:
            if groups['group']['id'] == group:
                ingroup = True
                groupname = groups['group']['name']
                grouprole = groups['role']['name']
                groupid = groups['group']['id']
                break
            else: ingroup = False
        if ingroup:
            thumbnail_url = await RoModules.get_group_emblem(groupid, "420x420")
            if thumbnail_url not in [-1, -2]: embed.set_thumbnail(url=thumbnail_url)
            embed.color = 0x00FF00
            embed.title = (f"{user_id[1]} is in group `{groupname}`!")
            embed.description = (f"Role: `{grouprole}`")
            await interaction.followup.send(embed=embed)
            return
        else:
            embed.description = (f"{user_id[1]} is not in the specified group.")
            await interaction.followup.send(embed=embed)
            return
    except Exception as e: await handle_error(e, interaction, "isingroup", "Group ID")

@client.tree.command()
@discord.app_commands.checks.cooldown(2, 60, key=lambda i: (i.user.id))
async def getclothingtexture(interaction: discord.Interaction, clothing_id: int):
    """Get the texture file of a clothing item"""
    await interaction.response.defer(ephemeral=False)
    embed = discord.Embed(color=0xFF0000)
    if not (await validate_user(interaction, embed)): return
    try:
        async def send_image(clothing_id:int):
            uploaded_image = discord.File(f'cache/clothing/{clothing_id}.png', filename=f"rowhois-{clothing_id}.png")
            await interaction.followup.send("", file=uploaded_image)
            return
        try:
            async with aiofiles.open(f'cache/clothing/{clothing_id}.png', 'rb') as clothing_texture: await send_image(clothing_id)
        except FileNotFoundError:
            try: initAsset = await Roquest.GetFileContent(clothing_id)
            except Exception as e: 
                if (await handle_error(e, interaction, "getclothingtexture", "Asset")): return
            if not initAsset:
                embed.description = "Failed to get clothing texture!"
                await interaction.followup.send(embed=embed)
                return
            initAssetContent = io.BytesIO(initAsset)
            initAssetContent = initAssetContent.read().decode()
            match = re.search(r'<url>.*id=(\d+)</url>', initAssetContent)
            if match:
                async with aiofiles.open(f'cache/clothing/{clothing_id}.png', 'wb') as cached_image:
                    downloadedAsset = await Roquest.GetFileContent(match.group(1))
                    if not downloadedAsset:
                        embed.description = "Failed to get clothing texture!"
                        await interaction.followup.send(embed=embed)
                        await cached_image.close()
                        return
                    await cached_image.write(downloadedAsset)
                    await cached_image.close()
                await send_image(clothing_id)
            else:
                embed.description = "Failed to get clothing texture!"
                await interaction.followup.send(embed=embed)
                return
    except UnicodeDecodeError as e:
        embed.description = "Invalid item type."
        await interaction.followup.send(embed=embed)
    except Exception as e: await handle_error(e, interaction, "getclothingtexture", "Clothing ID")

@client.tree.command()
@discord.app_commands.checks.cooldown(2, 60, key=lambda i: (i.user.id))
async def getitemdetails(interaction: discord.Interaction, item: int):
    """Get advanced details about a catalog item"""
    await interaction.response.defer(ephemeral=False)
    embed = discord.Embed(color=0xFF0000)
    if not (await validate_user(interaction, embed)): return
    try:
        data = await Roquest.Roquest("GET", "economy", f"v2/assets/{item}/details")
        if data[0] in [404, 400]:
            embed.description = "Item does not exist."
            await interaction.followup.send(embed=embed)
            return
        elif data[0] in [403, -1]:
            embed.description = "Whoops! We couldn't get this item. Try again later."
            await interaction.followup.send(embed=embed)
            return
        embed.url = f"https://www.roblox.com/catalog/{item}"
        if data[1]["CollectibleItemId"] != None: isCollectible = True
        else: isCollectible = False
        embed.title = f"{'<:Limited:1199463458316492850>' if data[1]['IsLimited'] else '<:LimitedU:1199463513505157240>' if data[1]['IsLimitedUnique'] else '<:Collectible:1199466929816084611>' if isCollectible else ''} {data[1]['Name']}"
        embed.add_field(name="Creator:", value=(f"`{data[1]['Creator']['Name']}` (`{data[1]['Creator']['Id']}`) {'<:RoWhoIsStaff:1186713381038719077>' if userid in staffIds else '<:verified:1186711315679563886>' if data[1]['Creator']['HasVerifiedBadge'] else ''}"))
        embed.add_field(name="Description:", value=f"`{data[1]['Description']}`" if data[1]['Description'] != "" else None, inline=False)
        embed.add_field(name="Created:", value=f"`{(await fancy_time(data[1]['Created']))}`", inline=True)
        embed.add_field(name="Updated:", value=f"`{(await fancy_time(data[1]['Updated']))}`", inline=True)
        if isCollectible:
            embed.add_field(name="Quantity:", value=f"`{data[1]['CollectiblesItemDetails']['TotalQuantity']}`", inline=True)
            if data[1]['CollectiblesItemDetails']['CollectibleLowestResalePrice'] is not None and data[1]['IsForSale']: embed.add_field(name="Lowest Price:", value=f"<:Robux:1199463545151168533> `{data[1]['CollectiblesItemDetails']['CollectibleLowestResalePrice']}`", inline=True)
            elif data[1]["IsForSale"]: embed.add_field(name="Lowest Price:", value=f"`No resellers`", inline=True)
        if data[1]["IsForSale"]:
            if (data[1]["Remaining"] is not None and data[1]["Remaining"] != 0): embed.add_field(name="Remaining:", value=f"`{data[1]['Remaining']}`", inline=True)
            if not (data[1]["IsLimited"] or data[1]["Remaining"] == 0 or isCollectible): embed.add_field(name="Price:", value=f"<:Robux:1199463545151168533> `{data[1]['PriceInRobux']}`", inline=True)
        thumbnail_url = await RoModules.get_item_thumbnail(item, "420x420")
        if thumbnail_url not in [-1, -2]: embed.set_thumbnail(url=thumbnail_url)
        embed.color = 0x00FF00
        await interaction.followup.send(embed=embed)
        return
    except Exception as e: await handle_error(e, interaction, "getitemdetails", "Item ID")

@client.tree.command()
@discord.app_commands.checks.cooldown(2, 60, key=lambda i: (i.user.id))
async def getmembership(interaction: discord.Interaction, user: str):
    """Checks whether a user has premium and if they had Builders Club"""
    await interaction.response.defer(ephemeral=False)
    embed = discord.Embed(color=0xFF0000)
    if not (await validate_user(interaction, embed)): return
    try:
        try: user_id = [int(user), None] if user.isdigit() else await RoModules.convert_to_id(user)
        except Exception as e:
            if (await handle_error(e, interaction, "getmembership", "User ID")): return
        if not (await validate_user(interaction, embed, user_id[0])): return
        try: userProfile = await RoModules.get_player_profile(user_id[0])
        except Exception as e:
             if (await handle_error(e, interaction, "getmembership", "User")): return
        if user_id[1] == None: user_id[1] = (userProfile[3])
        try: data = await RoModules.get_membership(user_id[0])
        except Exception as e:
            if (await handle_error(e, interaction, "getmembership", "User")): return
        if all(not data[i] for i in range(1, 5)): noTiers = True
        else: noTiers = False
        # We're gettin' shcwifty in here with these f-string expressions
        newline = '\n'
        embed.title = f"{user_id[1]}'s memberships:"
        embed.description = f"{('<:Premium:1207508505834168370> `Premium`' + newline) if data[0] else ''}{('<:BuildersClub:1207508440172208159> `Builders Club`' + newline) if data[1] else ''}{('<:TurboBuildersClub:1207508465329901630> `Turbo Builders Club`' + newline) if data[2] else ''}{('<:OutrageousBuildersClub:1207508480223617054> `Outrageous Builders Club`' + newline) if data[3] else ''}{(user_id[1] + ' has no memberships.') if noTiers else ''}"
        embed.color = 0x00FF00
        await interaction.followup.send(embed=embed)
        return
    except Exception as e: await handle_error(e, interaction, "getmembership", "User")

@client.tree.command()
@discord.app_commands.checks.cooldown(3, 60, key=lambda i: (i.user.id))
async def group(interaction: discord.Interaction, group:int):
    """Get detailed group information from a Group ID"""
    await interaction.response.defer(ephemeral=False)
    embed = discord.Embed(color=0xFF0000)
    if not (await validate_user(interaction, embed)): return
    try:
        try: groupInfo = await RoModules.get_group(group)
        except Exception as e:
            if (await handle_error(e, interaction, "group", "Group")): return
        groupThumbnail = await RoModules.get_group_emblem(group, "420x420")
        if groupThumbnail: embed.set_thumbnail(url=groupThumbnail)
        embed.title = f"{groupInfo[0]}{' <:verified:1186711315679563886>' if groupInfo[3] else ''}"
        embed.add_field(name="Group ID:", value=f"`{group}`")
        embed.add_field(name="Status:", value=f"`{'Locked' if groupInfo[8] else 'Okay'}`", inline=True)
        formattedTime = await fancy_time(groupInfo[2])
        embed.add_field(name="Created:", value=f"`{formattedTime}`", inline=True)
        if groupInfo[4][0] != False: embed.add_field(name="Owner:", value=f"`{groupInfo[4][0]}` (`{groupInfo[4][1]}`) {' <:verified:1186711315679563886>' if groupInfo[4][2] else ''}", inline=True)
        else: embed.add_field(name="Owner:", value=f"Nobody!", inline=True)
        embed.add_field(name="Members:", value=f"`{groupInfo[6]}`", inline=True)
        embed.add_field(name="Joinable:", value=f"`{'False' if groupInfo[8] else 'True' if groupInfo[7] else 'False'}`", inline=True)
        if groupInfo[5][0] != False and groupInfo[5][0] != "": embed.add_field(name="Shout:", value=f"`{groupInfo[5][0]}` -- `{groupInfo[5][1]}` (`{groupInfo[5][2]}`) {' <:verified:1186711315679563886>' if groupInfo[5][3] else ''}", inline=False)
        if groupInfo[1] != "": embed.add_field(name="Group Description:", value=f"`{groupInfo[1]}`", inline=False)
        embed.color = 0x00FF00
        await interaction.followup.send(embed=embed)
        return
    except Exception as e: await handle_error(e, interaction, "group", "Group ID")

@client.tree.command()
@discord.app_commands.checks.cooldown(4, 60, key=lambda i: (i.user.id))
async def checkusername(interaction: discord.Interaction, username:str):
    """Check if a username is available"""
    await interaction.response.defer(ephemeral=False)
    embed = discord.Embed(color=0xFF0000)
    if not (await validate_user(interaction, embed)): return
    try:
        try: usernameInfo = await RoModules.validate_username(username)
        except Exception as e: 
            if (await handle_error(e, interaction, "username", "Username")): return
        if usernameInfo[0] == 0: 
            embed.color = 0x00FF00
            embed.description = "Username is available!"
        elif usernameInfo[0] == 1: embed.description = "Username is taken."
        else: embed.description = f"Username not available.\n**Reason:** {usernameInfo[1]}"
        await interaction.followup.send(embed=embed)
    except Exception as e: await handle_error(e, interaction, "username", "Username")