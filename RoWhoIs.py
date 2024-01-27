import asyncio, discord, json, aiofiles, re, io, subprocess
import Roquest, RoModules
from secret import RWI
from logger import AsyncLogCollector
from datetime import datetime

log_collector = AsyncLogCollector("logs/RoWhoIs.log")
opt_out, RoliData, staff_ids, user_blocklist = [], [], [], []
log_config_updates, testing_mode = None, None

with open('config.json', 'r') as file: config = json.load(file) # Must be ran sync on init
testing_mode = config.get("RoWhoIs", {}).get("testing", False)

class RoWhoIs(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = discord.app_commands.CommandTree(self)
    async def setup_hook(self): await self.tree.sync(guild=None)

async def get_version():
    try:
        short_commit_id = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).strip()
        return short_commit_id.decode('utf-8')
    except subprocess.CalledProcessError as e:
        log_collector.error(f"Error getting short commit ID: {e}")
        return 0

async def load_configs():
    message_shown = False
    while True:
        try:
            with open('config.json', 'r') as file: config = json.load(file)
            log_config_updates = config.get("RoWhoIs", {}).get("log_config_updates", False)
            testing_mode = config.get("RoWhoIs", {}).get("testing", False)
            if not log_config_updates and not message_shown: await log_collector.info("In config.json: log_config_updates set to False. Successful configuration updates will not be logged.")
            opt_out.extend([id for module_data in config.values() if 'opt_out' in module_data for id in module_data['opt_out']])
            user_blocklist.extend([id for module_data in config.values() if 'banned_users' in module_data for id in module_data['banned_users']])
            staff_ids.extend([id for module_data in config.values() if 'admin_ids' in module_data for id in module_data['admin_ids']])
            if log_config_updates and not message_shown: await log_collector.info("Opt-out IDs updated successfully.")
            if log_config_updates and not message_shown: await log_collector.info("User blocklist updated successfully.")
            if testing_mode and not message_shown: await log_collector.warn("Currently running in testing mode.")
            elif not testing_mode and not message_shown: await log_collector.warn("Currently running in production mode.")
            if log_config_updates == False: message_shown = True
            await asyncio.sleep(3600)
        except Exception as e:
            await log_collector.error(f"Failed to update RoWhoIs configuration: {e}")
            await asyncio.sleep(10)

async def update_rolidata():
    global RoliData
    while True:
        try:
            RoliData = await Roquest.RoliData()
            if RoliData != -1: 
                if log_config_updates: await log_collector.info("Rolimons data updated successfully.")
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
        await log_collector.error(f"Error formatting time: {e}")
        return last_online_timestamp
    
async def validate_user(interaction, embed, code):
    if code == -1:
        embed.description = "User doesn't exist."
        await interaction.followup.send(embed=embed, ephemeral=True)
        return False
    elif code == -2:
        embed.description = "Whoops! An error occurred. Please try again later."
        await interaction.followup.send(embed=embed, ephemeral=True)
        return False
    elif code in opt_out:
        embed.description = "This user has requested to opt-out of the RoWhoIs search."
        await log_collector.warn(f"Opt-out user {code} was called by {interaction.user.id} and denied!")
        await interaction.followup.send(embed=embed, ephemeral=True)
        return False
    else: return True

async def check_user(interaction, embed):
    if interaction.user.id in user_blocklist:
        embed.description = "You have been permanently banned from using RoWhoIs. In accordance to our [Terms of Service](https://www.robloxians.com/Terms-Of-Service/), we reserve the right to block any user from using our service."
        await log_collector.warn(f"Blocklist user {interaction.user.id} attempted to call a command and was denied!")
        await interaction.followup.send(embed=embed, ephemeral=True)
        return False
    else: return True

async def handle_unknown_error(error, interaction, command:str):
    embed = discord.Embed(color=0xFF0000)
    await log_collector.error(f"Error in the {command} command: {error}")
    embed.description = "Whoops! An unknown error occurred. Please try again later."
    await interaction.followup.send(embed=embed, ephemeral=True)
    return

client = RoWhoIs(intents=discord.Intents.default())
loop = asyncio.get_event_loop()
loop.create_task(update_rolidata())
loop.create_task(load_configs())

@client.event
async def on_ready():
    await log_collector.info(f'RoWhoIs initialized! Running on version {(await get_version())}')
    await log_collector.info(f'Logged in as {client.user} (ID: {client.user.id})')
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="over Robloxia"))

@client.tree.command()
@discord.app_commands.checks.cooldown(3, 60, key=lambda i: (i.user.id))
async def help(interaction: discord.Interaction):
    """List all of the commands RoWhoIs supports & what they do"""
    await interaction.response.defer(ephemeral=False)
    embedVar = discord.Embed(title="RoWhoIs Commands", color=discord.Color.from_rgb(135, 136, 138))
    if not (await check_user(interaction, embedVar)): return
    embedVar.add_field(name="whois {UserId}/{username}", value="Get detailed profile information from a User ID/Username.", inline=True)
    embedVar.add_field(name="getclothingtexture {itemId}", value="Retrieves the texture file for a 2D clothing asset.", inline=True)
    embedVar.add_field(name="userid {Username}", value="Get a User ID based off a username.", inline=True)
    embedVar.add_field(name="ownsitem {UserId}/{username}, {itemId}", value="Retrieve whether a user owns an item or not. Works with players who have a private inventory.", inline=True)
    embedVar.add_field(name="ownsbadge {UserId}/{username}, {badgeId}", value="Retrieve whether a user owns a badge or not. Works with players who have a private inventory.", inline=True)
    embedVar.add_field(name="isfriendswith {user1}, {user2}", value="Check if two players are friended.", inline=True)
    embedVar.add_field(name="isingroup {user}, {group}", value="Check if a player is in the specified group.", inline=True)
    embedVar.add_field(name="limited {limited name}/{limited acronym}", value="Returns a limited ID, the rap, and value of the specified limited.", inline=True)
    embedVar.add_field(name="getitemdetails {item}", value="Returns details about a catalog item.", inline=True)
    embedVar.set_footer(text=f"Version {(await get_version())}")
    await interaction.followup.send(embed=embedVar)

@client.tree.error
async def on_app_command_error(interaction: discord.Interaction,error: discord.app_commands.AppCommandError):
    if isinstance(error, discord.app_commands.CommandOnCooldown):
        await interaction.response.send_message(f"Your enthusiasm is greatly appreciated, but please slow down! Try again in {round(error.retry_after)} seconds.", ephemeral=True)
    else:
        await log_collector.fatal(f"Unexpected error occured during core command function: {error}")
        await interaction.response.send_message(f"Whoops! Looks like we encountered an unexpected error. We've reported this to our dev team and we'll fix it shortly!", ephemeral=True)
        
@client.tree.command()
@discord.app_commands.checks.cooldown(5, 60, key=lambda i: (i.user.id))
async def userid(interaction: discord.Interaction, username: str):
    """Get a User ID from a username."""
    await interaction.response.defer(ephemeral=False)
    try:
        embed = discord.Embed(color=0xFF0000)
        if not (await check_user(interaction, embed)): return
        user_id = await RoModules.convert_to_id(username)
        if not (await validate_user(interaction, embed, user_id[0])): return
        if user_id[1] == user_id[2]: embed.title = f"{user_id[1]} {'<:RoWhoIsStaff:1186713381038719077>' if user_id[0] in staff_ids else '<:verified:1186711315679563886>' if user_id[3] else ''}"
        else: embed.title = f"{user_id[1]} ({user_id[2]}) {'<:RoWhoIsStaff:1186713381038719077>' if user_id[0] in staff_ids else '<:verified:1186711315679563886>' if user_id[3] else ''}"
        embed.description = f"**User ID:** `{user_id[0]}`"
        embed.url = f"https://www.roblox.com/users/{user_id[0]}/profile"
        user_thumbnail = await RoModules.get_player_headshot(user_id[0], "420x420")
        if user_thumbnail: embed.set_thumbnail(url=user_thumbnail)
        embed.color = 0x00FF00
        await interaction.followup.send(embed=embed)
    except Exception as e: await handle_unknown_error(e, interaction, "userid")
        
@client.tree.command()
@discord.app_commands.checks.cooldown(5, 60, key=lambda i: (i.user.id))
async def username(interaction: discord.Interaction, userid: int):
    """Get a username from a User ID."""
    await interaction.response.defer(ephemeral=False)
    try:
        embed = discord.Embed(color=0xFF0000)
        if not (await check_user(interaction, embed)): return
        if not (await validate_user(interaction, embed, userid)): return
        username = await RoModules.convert_to_username(userid)
        if username[0] == username[1]: embed.title = f"{username[0]} {'<:RoWhoIsStaff:1186713381038719077>' if userid in staff_ids else '<:verified:1186711315679563886>' if username[2] else ''}"
        else: embed.title = f"{username[0]} ({username[1]}) {'<:RoWhoIsStaff:1186713381038719077>' if userid in staff_ids else '<:verified:1186711315679563886>' if username[2] else ''}"
        embed.description = f"**Username:** `{username[0]}`"
        embed.url = f"https://www.roblox.com/users/{userid}/profile"
        user_thumbnail = await RoModules.get_player_headshot(userid, "420x420")
        if user_thumbnail: embed.set_thumbnail(url=user_thumbnail)
        embed.color = 0x00FF00
        await interaction.followup.send(embed=embed)
    except Exception as e: await handle_unknown_error(e, interaction, "username")

@client.tree.command()
@discord.app_commands.checks.cooldown(3, 60, key=lambda i: (i.user.id))
async def whois(interaction: discord.Interaction, user: str):
    """Get detailed profile information from a User ID/Username"""
    await interaction.response.defer(ephemeral=False)
    try:
        embed = discord.Embed(color=0xFF0000)
        if not (await check_user(interaction, embed)): return
        user_id = [int(user), None] if user.isdigit() else await RoModules.convert_to_id(user)
        if not (await validate_user(interaction, embed, user_id[0])): return
        description, created, banned, name, displayname,verified = await RoModules.get_player_profile(user_id[0])
        if created == -2:
            embed.description = "Whoops! An error occurred. Please try again later."
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        elif created == -1:
            embed.description = "User doesn't exist."
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        user_thumbnail = await RoModules.get_player_thumbnail(user_id[0], "420x420") # Otherwise causes issues with response sent without user_thumbnail
        if user_thumbnail: embed.set_thumbnail(url=user_thumbnail)
        if banned == True: private_inventory = True 
        else: private_inventory = True
        veriftype = await RoModules.check_verification(user_id[0]) if not banned and user_id[0] != 1 else None
        last_online_formatted = await fancy_time(await RoModules.last_online(user_id[0]))
        joined_timestamp = await fancy_time(created)
        previous_usernames = await RoModules.get_previous_usernames(user_id[0]) if not banned else []
        groups = await RoModules.get_group_count(user_id[0])
        friends, followers, following = await RoModules.get_socials(user_id[0])
        total_rap, total_value, cursor = 0, 0, ""
        while not banned and user_id[0] != 1:
            rap = await Roquest.Roquest("GET", f"https://inventory.roblox.com/v1/users/{user_id[0]}/assets/collectibles?limit=100&sortOrder=Asc&cursor={cursor}")
            if rap == 403:
                private_inventory = True
                break
            else: private_inventory = False
            data = rap.get("data", [])
            if not data: break
            for item in data:
                assetId = str(item.get("assetId", 0))
                if assetId in RoliData['items']:
                    item_value = RoliData['items'][assetId][4]
                    if item_value is not None: total_value += item_value
                rap_value = item.get("recentAveragePrice", 0)
                if rap_value is not None:
                    total_rap += rap_value
            cursor = rap.get("nextPageCursor")
            if not cursor: break
        if name == displayname: embed.title = f"{name} {'<:RoWhoIsStaff:1186713381038719077>' if user_id[0] in staff_ids else '<:verified:1186711315679563886>' if verified else ''}"
        else: embed.title = f"{name} ({displayname}) {'<:RoWhoIsStaff:1186713381038719077>' if user_id[0] in staff_ids else '<:verified:1186711315679563886>' if verified else ''}"
        embed.color = 0x00ff00
        embed.url=f"https://www.roblox.com/users/{user_id[0]}/profile" if not banned else None
        embed.add_field(name="User ID:", value=f"`{user_id[0]}`", inline=True)
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
        embed.add_field(name="Groups:", value=f"`{groups}`" if veriftype not in [-1, -2] else "Failed to fetch.", inline=True)
        embed.add_field(name="Friends:", value=f"`{friends}`" if friends not in [-1, -2] else "Failed to fetch.", inline=True)
        embed.add_field(name="Followers:", value=f"`{followers}`" if followers not in [-1, -2] else "Failed to fetch.", inline=True)
        embed.add_field(name="Following:", value=f"`{following}`" if following not in [-1, -2] else "Failed to fetch.", inline=True)
        await interaction.followup.send(embed=embed)
    except Exception as e: await handle_unknown_error(e, interaction, "whois")

@client.tree.command()
@discord.app_commands.checks.cooldown(3, 60, key=lambda i: (i.user.id))
async def ownsitem(interaction: discord.Interaction, user: str, item_id: int):
    """Check if a player owns a specific item."""
    await interaction.response.defer(ephemeral=False)
    embed = discord.Embed(color=0xFF0000)
    if not (await check_user(interaction, embed)): return
    try:
        user_id = [int(user), None] if user.isdigit() else await RoModules.convert_to_id(user)
        if not (await validate_user(interaction, embed, user_id[0])): return
        if user_id[1] == None: user_id[1] = (await RoModules.get_player_profile(user_id[0]))[3]
        verifhat = await Roquest.Roquest("GET", f"https://inventory.roblox.com/v1/users/{user_id[0]}/items/4/{item_id}")
        if verifhat in [-1, -2]:
            embed.description = "Whoops! An error occurred. Please try again later."
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        if verifhat in [404, 400]:
            embed.description = "This item does not exist."
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        if verifhat["data"] and any("type" in item for item in verifhat["data"]):
            item_name = verifhat["data"][0]["name"]
            total_items_owned = len(verifhat["data"])
            uaid_list = [item["instanceId"] for item in verifhat["data"][:50]]
            more_items = total_items_owned - 50
            thumbnail_url = await RoModules.get_item_thumbnail(item_id, "420x420")
            if thumbnail_url != -1: embed.set_thumbnail(url=thumbnail_url)
            embed.color = 0x00FF00
            embed.title = f"{user_id[1]} owns {total_items_owned} {item_name}{'s' if total_items_owned > 1 else ''}!"
            embed.description = "**UAIDs:**\n" + ', '.join([f"`{uaid}`" for uaid in map(str, uaid_list)])
            if more_items > 0:
                embed.description += f", and {more_items} more"
            await interaction.followup.send(embed=embed)
        else:
            embed.description = f"{(await RoModules.get_player_profile(user_id[0]))[3]} doesn't own the specified item!"
            await interaction.followup.send(embed=embed)
    except Exception as e: await handle_unknown_error(e, interaction, "ownsitem")

@client.tree.command()
@discord.app_commands.checks.cooldown(3, 60, key=lambda i: (i.user.id))
async def ownsbadge(interaction: discord.Interaction, user: str, badge_id: int):
    """Check if a player owns a specified badge and return it's award date."""
    await interaction.response.defer(ephemeral=False)
    embed = discord.Embed(color=0xFF0000)
    if not (await check_user(interaction, embed)): return
    try:
        user_id = [int(user), None] if user.isdigit() else await RoModules.convert_to_id(user)
        if not (await validate_user(interaction, embed, user_id[0])): return
        if user_id[1] == None: user_id[1] = (await RoModules.get_player_profile(user_id[0]))[3]
        verifhat = await Roquest.Roquest("GET", f"https://badges.roblox.com/v1/users/{user_id[0]}/badges/awarded-dates?badgeIds={badge_id}")
        if verifhat in [-1, -2]:
            embed.description = "Whoops! An error occurred. Please try again later."
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        if verifhat in [404, 400]:
            embed.description = "This badge does not exist."
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        if verifhat["data"] and any("type" for item in verifhat["data"][0]):
            awarded = verifhat["data"][0]["awardedDate"]
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
    except Exception as e: await handle_unknown_error(e, interaction, "ownsbadge")

@client.tree.command()
@discord.app_commands.checks.cooldown(3, 60, key=lambda i: (i.user.id))
async def limited(interaction: discord.Interaction, limited: str):
    """Returns a limited ID, the rap, and value of a specified limited."""
    await interaction.response.defer(ephemeral=False)
    embed = discord.Embed(color=0xFF0000)
    if not (await check_user(interaction, embed)): return
    try:
        limited_id, name, acronym, rap, value = await RoModules.get_rolidata_from_item(RoliData, limited)
        if limited_id != -1:
            thumbnail_url = await RoModules.get_item_thumbnail(limited_id, "420x420")
            if thumbnail_url not in [-1, -2]: embed.set_thumbnail(url=thumbnail_url)
            embed.color = 0x00FF00
            embed.title = f"{name} ({acronym})" if acronym != "" else f"{name}"
            embed.description = f"ID: `{limited_id}`\nRAP: `{rap}`\nValue: `{value}`"
            await interaction.followup.send(embed=embed)
        else:
            embed.description = f"Failed to find item! Make sure you spelled it correctly and used proper punctuation."
            await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as e: await handle_unknown_error(e, interaction, "limited")

@client.tree.command()
@discord.app_commands.checks.cooldown(5, 60, key=lambda i: (i.user.id))
async def isfriendswith(interaction: discord.Interaction, user1: str, user2:str):
    """Check whether a user is friended to another user"""
    # Technically we only have to check through one player as it's a mutual relationship
    await interaction.response.defer(ephemeral=False)
    embed = discord.Embed(color=0xFF0000)
    if not (await check_user(interaction, embed)): return
    try:
        user_id1 = [int(user1), None] if user1.isdigit() else await RoModules.convert_to_id(user1)
        if user2.isdigit(): user2 = int(user2) 
        if not (await validate_user(interaction, embed, user_id1[0])): return
        userfriends = await RoModules.get_friends(user_id1[0])
        if userfriends == -2:
            embed.description = "Whoops! An error occured. Please try again later."
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        elif userfriends in [-1, 400]:
            embed.description = "This user does not exist."
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        friended = False # Local variable 'friended' referenced before assignment 🤓
        if user_id1[1] == None: user_id1[1] = (await RoModules.get_player_profile(user_id1[0]))[3]
        for friends in userfriends['data']:
            if friends['id'] == user2 or friends['name'] == user2:
                if friends['id'] in opt_out:
                    embed.description = "Their friend has requested to opt-out of the RoWhoIs search."
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
    except Exception as e: await handle_unknown_error(e, interaction, "isfriendswith")
    
@client.tree.command()
@discord.app_commands.checks.cooldown(5, 60, key=lambda i: (i.user.id))
async def isingroup(interaction: discord.Interaction, user: str, group:int):
    """Check whether a user is in a group or not"""
    await interaction.response.defer(ephemeral=False)
    embed = discord.Embed(color=0xFF0000)
    if not (await check_user(interaction, embed)): return
    try:
        user_id = [int(user), None] if user.isdigit() else await RoModules.convert_to_id(user)
        if not (await validate_user(interaction, embed, user_id[0])): return
        if user_id[1] == None: user_id[1] = (await RoModules.get_player_profile(user_id[0]))[3]
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
    except Exception as e: await handle_unknown_error(e, interaction, "isingroup")

@client.tree.command()
@discord.app_commands.checks.cooldown(2, 60, key=lambda i: (i.user.id))
async def getclothingtexture(interaction: discord.Interaction, clothing_id: int):
    """Get the texture file of a clothing item"""
    await interaction.response.defer(ephemeral=False)
    embed = discord.Embed(color=0xFF0000)
    if not (await check_user(interaction, embed)): return
    try:
        async def send_image(clothing_id:int):
            uploaded_image = discord.File(f'cache/clothing/{clothing_id}.png', filename="image.png")
            await interaction.followup.send("", file=uploaded_image)
            return
        try:
            async with aiofiles.open(f'cache/clothing/{clothing_id}.png', 'rb') as clothing_texture: await send_image(clothing_id)
        except FileNotFoundError:
            initAsset = await Roquest.GetFileContent(clothing_id)
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
    except Exception as e: await handle_unknown_error(e, interaction, "getclothingtexture")

@client.tree.command()
@discord.app_commands.checks.cooldown(2, 60, key=lambda i: (i.user.id))
async def getitemdetails(interaction: discord.Interaction, item: int):
    """Get advanced details about a catalog item."""
    await interaction.response.defer(ephemeral=False)
    embed = discord.Embed(color=0xFF0000)
    if not (await check_user(interaction, embed)): return
    try:
        data = await Roquest.Roquest("GET", f"https://economy.roblox.com/v2/assets/{item}/details")
        if data in [404, 400]:
            embed.description = "Item does not exist."
            await interaction.followup.send(embed=embed)
            return
        elif data in [403, -1]:
            embed.description = "Whoops! We couldn't get this item. Try again later."
            await interaction.followup.send(embed=embed)
            return
        embed.url = f"https://www.roblox.com/catalog/{item}"
        if data["CollectibleItemId"] != None: isCollectible = True
        else: isCollectible = False
        embed.title = f"{'<:Limited:1199463458316492850>' if data['IsLimited'] else '<:LimitedU:1199463513505157240>' if data['IsLimitedUnique'] else '<:Collectible:1199466929816084611>' if isCollectible else ''} {data['Name']}"
        embed.add_field(name="Creator:", value=(f"`{data['Creator']['Name']}` (`{data['Creator']['Id']}`) {'<:RoWhoIsStaff:1186713381038719077>' if userid in staff_ids else '<:verified:1186711315679563886>' if data['Creator']['HasVerifiedBadge'] else ''}"))
        embed.add_field(name="Description:", value=f"`{data['Description']}`" if data['Description'] != "" else None, inline=False)
        embed.add_field(name="Created:", value=f"`{(await fancy_time(data['Created']))}`", inline=True)
        embed.add_field(name="Updated:", value=f"`{(await fancy_time(data['Updated']))}`", inline=True)
        if isCollectible:
            embed.add_field(name="Quantity:", value=f"`{data['CollectiblesItemDetails']['TotalQuantity']}`", inline=True)
            if data['CollectiblesItemDetails']['CollectibleLowestResalePrice'] is not None and data['IsForSale']: embed.add_field(name="Lowest Price:", value=f"<:Robux:1199463545151168533> `{data['CollectiblesItemDetails']['CollectibleLowestResalePrice']}`", inline=True)
            elif data["IsForSale"]: embed.add_field(name="Lowest Price:", value=f"`No resellers`", inline=True)
        if data["IsForSale"]:
            if (data["Remaining"] is not None and data["Remaining"] != 0): embed.add_field(name="Remaining:", value=f"`{data['Remaining']}`", inline=True)
            if not (data["IsLimited"] or data["Remaining"] == 0 or isCollectible): embed.add_field(name="Price:", value=f"<:Robux:1199463545151168533> `{data['PriceInRobux']}`", inline=True)
        thumbnail_url = await RoModules.get_item_thumbnail(item, "420x420")
        if thumbnail_url not in [-1, -2]: embed.set_thumbnail(url=thumbnail_url)
        embed.color = 0x00FF00
        await interaction.followup.send(embed=embed)
        return
    except Exception as e: await handle_unknown_error(e, interaction, "getitemdetails")

if testing_mode:loop.run_until_complete(client.start(RWI.TESTING))
else: loop.run_until_complete(client.start(RWI.PRODUCTION))