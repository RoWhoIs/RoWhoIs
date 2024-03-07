from server import Roquest, RoModules
import asyncio, discord, aiofiles, re, io, aiohttp, signal, datetime
from utils import logger, ErrorDict
from typing import Any


def run(productionmode: bool, version: str, config) -> None:
    """Runs the server."""
    try:
        global productionMode, staffIds, optOut, userBlocklist, shortHash, emojiTable, botToken
        emojiTable = {key: config['Emojis'][key] for key in config['Emojis']}
        botToken = {"topgg": config['Authentication']['topgg'], "dbl": config['Authentication']['dbl']}
        shortHash = version
        productionMode = productionmode
        staffIds = config['RoWhoIs']['admin_ids']
        optOut = config['RoWhoIs']['opt_out']
        userBlocklist = config['RoWhoIs']['banned_users']
        if not productionMode: loop.run_until_complete(client.start(config['Authentication']['testing']))
        else: loop.run_until_complete(client.start(config['Authentication']['production']))
    except KeyError: raise ErrorDict.MissingRequiredConfigs

class ShardAnalytics:
    def __init__(self, shard_count: int, init_shown: bool): self.shard_count, self.init_shown = shard_count, init_shown

shardAnalytics = ShardAnalytics(0, False)
log_collector = logger.AsyncLogCollector("logs/main.log")

class RoWhoIs(discord.AutoShardedClient):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = discord.app_commands.CommandTree(self)
    async def setup_hook(self): await self.tree.sync(guild=None)

async def shutdown() -> None:
    """Closes the client and cancels all tasks in the loop"""
    await log_collector.info("Gracefully shutting down RoWhoIs...")
    await discord.AutoShardedClient.close(client)
    for task in asyncio.all_tasks(loop): task.cancel()
    loop.stop()

async def update_rolidata() -> None:
    """Fetches Rolimons limited data"""
    global roliData
    while True:
        try:
            newData = await Roquest.RoliData()
            if newData is not None: roliData = newData
            else: await log_collector.error("Failed to update Rolimons data.")
        except ErrorDict.UnexpectedServerResponseError: pass
        except Exception as e: await log_collector.error(f"Error updating Rolimons data: {e}")
        await asyncio.sleep(3600)

async def update_followers() -> None:
    """Fetches the creator of RoWhoIs' followers, for use in an easter egg."""
    global autmnFollowers
    autmnFollowers = [] # Prevents 429 init errors
    while True:
        try:
            newData = (await Roquest.Followers())['followerIds']
            if newData is not None: autmnFollowers = newData
        except ErrorDict.UnexpectedServerResponseError: pass
        except Exception as e: 
            await log_collector.error(f"Error updating Robloxians data: {e}")
            pass
        await asyncio.sleep(60)

async def fancy_time(last_online_timestamp: str) -> str:
    """Converts a datetime string to a human-readable, relative format"""
    try:
        try: lastOnlineDatetime = datetime.datetime.strptime(last_online_timestamp, "%Y-%m-%dT%H:%M:%S.%fZ")
        except ValueError:
            try: lastOnlineDatetime = datetime.datetime.strptime(last_online_timestamp, "%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                data = str(last_online_timestamp)
                lastOnlineDatetime = datetime.datetime.strptime(data[:-7] + 'Z', "%Y-%m-%dT%H:%M:%S.%fZ").replace(microsecond=int(data[-7:-1]))
        timeDifference = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - lastOnlineDatetime
        timeUnits = [("year", 12, timeDifference.days // 365), ("month", 1, timeDifference.days // 30),  ("week", 7, timeDifference.days // 7), ("day", 1, timeDifference.days), ("hour", 60, timeDifference.seconds // 3600), ("minute", 60, timeDifference.seconds // 60), ("second", 1, timeDifference.seconds)]
        for unit, _, value in timeUnits:
            if value > 0:
                lastOnlineFormatted = f"{value} {unit + 's' if value != 1 else unit} ago"
                break
        else: lastOnlineFormatted = f"{timeDifference.seconds} {'second' if timeDifference.seconds == 1 else 'seconds'} ago"
        lastOnlineFormatted += f" ({lastOnlineDatetime.strftime('%m/%d/%Y %H:%M:%S')})"
        return lastOnlineFormatted
    except Exception as e:
        await log_collector.error(f"Error formatting time: {e} | Returning fallback data: {last_online_timestamp}")
        return last_online_timestamp

async def validate_user(interaction: discord.Interaction, embed: discord.Embed, user_id: int = None) -> bool:
    """Check a Discord or Roblox user ID against blocklists."""
    global optOut, userBlocklist
    if interaction.user.id in userBlocklist:
        await log_collector.warn(f"Blocklist user {interaction.user.id} attempted to call a command and was denied!")
        embed.description = "You have been permanently banned from using RoWhoIs. In accordance to our [Terms of Service](https://www.robloxians.com/Terms-Of-Service/), we reserve the right to block any user from using our service."
    elif user_id and user_id in optOut:
        await log_collector.warn(f"Blocklist user {user_id} was requested by {interaction.user.id} and denied!")
        embed.description = "This user has requested to opt-out of RoWhoIs."
    else: return True
    embed.title = None
    embed.colour = 0xFF0000
    await interaction.followup.send(embed=embed, ephemeral=True)
    return False

async def handle_error(error, interaction: discord.Interaction, command: str, shard_id: int, context: str = "Requested resource") -> bool:
    """Handles both user-facing and backend errors, even if they are undocumented."""
    embed = discord.Embed(color=0xFF0000)
    if isinstance(error, ErrorDict.DoesNotExistError): embed.description = f"{context} doesn't exist."
    elif isinstance(error, ErrorDict.MismatchedDataError): embed.description = f"{context} is invalid."
    elif isinstance(error, ErrorDict.RatelimitedError): embed.description = "RoWhoIs is experienceing unusually high demand. Please try again."
    else: 
        if isinstance(error, ErrorDict.InvalidAuthorizationError): await Roquest.token_renewal()
        embed.description = "Whoops! An unknown error occurred. Please try again later."
        await log_collector.error(f"Error in the {command} command: {error}", shard_id=shard_id)
    await interaction.followup.send(embed=embed, ephemeral=True)
    return True

async def safe_wrapper(task, *args):
    """Allows asyncio.gather to continue even if a thread throws an exception"""
    try: return await task(*args)
    except Exception as e: return e


client = RoWhoIs(intents=discord.Intents.default())
loop = asyncio.get_event_loop()
loop.create_task(update_rolidata())
loop.create_task(update_followers())
loop.add_signal_handler(signal.SIGINT, lambda: asyncio.create_task(shutdown()))

@client.event
async def on_ready():
    global shardAnalytics
    if not shardAnalytics.init_shown: await log_collector.info(f"RoWhoIs initialized! Logged in as {client.user} (ID: {client.user.id}) under {client.shard_count} shard{'s.' if client.shard_count >= 2 else ''}")
    shardAnalytics.init_shown, shardAnalytics.shard_count = True, client.shard_count

@client.event
async def on_shard_connect(shard_id):
    global shardAnalytics
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="over Robloxia"), shard_id=shard_id)
    if shardAnalytics.shard_count != len(client.shards):
        await log_collector.info(f"Connected. Now operating under {len(client.shards)} shard{'s.' if len(client.shards) >= 2 else '.'}", shard_id=shard_id)
        shardAnalytics.shard_count = len(client.shards)
    else: await log_collector.info(f"Connected.", shard_id=shard_id)
    return

@client.event
async def on_shard_resumed(shard_id):
    if shardAnalytics.shard_count != len(client.shards): await log_collector.info(f"Resumed. Now operating under {len(client.shards)} shard{'s.' if len(client.shards) >= 2 else '.'}", shard_id=shard_id)
    else: await log_collector.info(f"Resumed.", shard_id=shard_id)
    return

@client.event
async def on_shard_disconnect(shard_id):
    global shardAnalytics
    if shardAnalytics.shard_count != len(client.shard_count):
        await log_collector.info(f"Disconnected. Now operating under {len(client.shards)} shard{'s.' if len(client.shards) >= 2 else '.'}", shard_id=shard_id)
        shardAnalytics.shard_count = len(client.shards)
    else: await log_collector.info(f"Disconnected.", shard_id=shard_id)
    return

@client.event
async def on_guild_join(guild):
    if productionMode:
        try:
            await log_collector.info(f"RoWhoIs has joined a new server. Total servers: {len(client.guilds)}. Updating registries...")
            async with aiohttp.ClientSession() as session:
                if botToken.get("topgg") != "":
                    async with session.post(f"https://top.gg/api/bots/{client.user.id}/stats", headers={"Authorization": botToken.get("topgg")}, json={"server_count": len(client.guilds)}): pass
                if botToken.get("dbl") != "":
                    async with session.post(f"https://discordbotlist.com/api/v1/bots/{client.user.id}/stats", headers={"Authorization": botToken.get("dbl")}, json={"guilds": len(client.guilds)}): pass
        except Exception as e: await log_collector.error(f"Failed to update registries. {e}")

@client.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    if isinstance(error, discord.app_commands.CommandInvokeError): await log_collector.critical(f"Interaction invoke error: {error} invoked by {interaction.user.id}")
    elif isinstance(error, discord.app_commands.CommandOnCooldown): await interaction.response.send_message(f"Your enthusiasm is greatly appreciated, but please slow down! Try again in {round(error.retry_after)} seconds.", ephemeral=True)
    else:
        await log_collector.critical(f"Unexpected error occured during core command function: {error} invoekd by {interaction.user.id}")
        await interaction.followup.send(f"Whoops! Looks like we encountered an unexpected error. We've reported this to our dev team and we'll fix it shortly!", ephemeral=True)

@client.tree.command()
@discord.app_commands.checks.cooldown(3, 60, key=lambda i: i.user.id)
async def help(interaction: discord.Interaction):
    """List all of the commands RoWhoIs supports & what they do"""
    await interaction.response.defer(ephemeral=False)
    embedVar = discord.Embed(title="RoWhoIs Commands", color=discord.Color.from_rgb(135, 136, 138))
    if not (await validate_user(interaction, embedVar)): return
    embedVar.add_field(name="whois {User}", value="Get detailed profile information from a User ID/Username.", inline=True)
    embedVar.add_field(name="clothingtexture {itemId}", value="Retrieves the texture file for a 2D clothing asset.", inline=True)
    embedVar.add_field(name="userid {Username}", value="Get a User ID based off a username.", inline=True)
    embedVar.add_field(name="username {UserId}", value="Get a username based off a User ID.", inline=True)
    embedVar.add_field(name="ownsitem {User}, {itemId}", value="Retrieve whether a user owns an item or not. Works with players who have a private inventory.", inline=True)
    embedVar.add_field(name="ownsbadge {User}, {badgeId}", value="Retrieve whether a user owns a badge or not. Works with players who have a private inventory.", inline=True)
    embedVar.add_field(name="isfriendswith {User1}, {User2}", value="Check if two players are friended.", inline=True)
    embedVar.add_field(name="group {groupId}", value="Get detailed group information from a Group ID.", inline=True)
    embedVar.add_field(name="isingroup {user}, {group}", value="Check if a player is in the specified group.", inline=True)
    embedVar.add_field(name="limited {limited name}/{limited acronym}", value="Returns a limited ID, the rap, and value of the specified limited.", inline=True)
    embedVar.add_field(name="itemdetails {item}", value="Returns details about a catalog item.", inline=True)
    embedVar.add_field(name="membership {User}", value="Check if a player has Premium or has had Builders Club.", inline=True)
    embedVar.add_field(name="checkusername {username}", value="Check if a username is available", inline=True)
    embedVar.add_field(name="robloxbadges {user}", value="Shows what Roblox badges a player has", inline=True)
    embedVar.set_footer(text=f"Version {shortHash} | Made with <3 by autumnfication")
    await interaction.followup.send(embed=embedVar)

@client.tree.command()
@discord.app_commands.checks.cooldown(5, 60, key=lambda i: i.user.id)
async def userid(interaction: discord.Interaction, username: str):
    """Get a User ID from a username"""
    await interaction.response.defer(ephemeral=False)
    try:
        embed = discord.Embed(color=0xFF0000)
        if not (await validate_user(interaction, embed)): return
        try: user_id = await RoModules.convert_to_id(username, interaction.guild.shard_id)
        except Exception as e: 
            if await handle_error(e, interaction, "userid", interaction.guild.shard_id, "User"): return
        if not (await validate_user(interaction, embed, user_id[0])): return
        if user_id[1] == user_id[2]: embed.title = f"{user_id[1]} {emojiTable.get('staff') if user_id[0] in staffIds else emojiTable.get('verified') if user_id[3] else ''}"
        else: embed.title = f"{user_id[1]} ({user_id[2]}) {emojiTable.get('staff') if user_id[0] in staffIds else emojiTable.get('verified') if user_id[3] else ''}"
        embed.description = f"**User ID:** `{user_id[0]}`"
        embed.url = f"https://www.roblox.com/users/{user_id[0]}/profile"
        user_thumbnail = await RoModules.get_player_headshot(user_id[0], "420x420", interaction.guild.shard_id)
        if user_thumbnail: embed.set_thumbnail(url=user_thumbnail)
        embed.colour = 0x00FF00
        await interaction.followup.send(embed=embed)
    except Exception as e: await handle_error(e, interaction, "userid", interaction.guild.shard_id, "User")

@client.tree.command()
@discord.app_commands.checks.cooldown(5, 60, key=lambda i: i.user.id)
async def username(interaction: discord.Interaction, userid: int):
    """Get a username from a User ID"""
    await interaction.response.defer(ephemeral=False)
    try:
        embed = discord.Embed(color=0xFF0000)
        if not (await validate_user(interaction, embed, userid)): return
        try: username = await RoModules.convert_to_username(userid, interaction.guild.shard_id)
        except Exception as e:
            if await handle_error(e, interaction, "username", interaction.guild.shard_id,  "User"): return
        if username[0] == username[1]: embed.title = f"{username[0]} {emojiTable.get('staff') if userid in staffIds else emojiTable.get('verified') if username[2] else ''}"
        else: embed.title = f"{username[0]} ({username[1]}) {emojiTable.get('staff') if userid in staffIds else emojiTable.get('verified') if username[2] else ''}"
        embed.description = f"**Username:** `{username[0]}`"
        embed.url = f"https://www.roblox.com/users/{userid}/profile"
        user_thumbnail = await RoModules.get_player_headshot(userid, "420x420", interaction.guild.shard_id)
        if user_thumbnail: embed.set_thumbnail(url=user_thumbnail)
        embed.colour = 0x00FF00
        await interaction.followup.send(embed=embed)
    except Exception as e: await handle_error(e, interaction, "username", interaction.guild.shard_id, "User")

@client.tree.command()
@discord.app_commands.checks.cooldown(3, 60, key=lambda i: i.user.id)
async def whois(interaction: discord.Interaction, user: str):
    """Get detailed profile information from a User ID/Username"""
    await interaction.response.defer(ephemeral=False)
    try:
        embed = discord.Embed(color=0xFF0000)
        if not (await validate_user(interaction, embed)): return
        userId = [int(user), None] if user.isdigit() else (await RoModules.convert_to_id(user, interaction.guild.shard_id))[:2]
        if not (await validate_user(interaction, embed, userId[0])): return
        try: description, created, banned, name, displayname, verified = await RoModules.get_player_profile(userId[0], interaction.guild.shard_id)
        except Exception as e:
            if await handle_error(e, interaction, "whois", interaction.guild.shard_id, "User"): return
        if banned or userId[0] == 1: tasks = [RoModules.nil_pointer(), RoModules.nil_pointer(), safe_wrapper(RoModules.get_player_thumbnail, userId[0], "420x420", interaction.guild.shard_id), safe_wrapper(RoModules.last_online, userId[0], interaction.guild.shard_id), safe_wrapper(RoModules.get_groups, userId[0], interaction.guild.shard_id), safe_wrapper(RoModules.get_socials, userId[0], interaction.guild.shard_id)]
        else: tasks = [safe_wrapper(RoModules.get_previous_usernames, userId[0], interaction.guild.shard_id), safe_wrapper(RoModules.check_verification, userId[0], interaction.guild.shard_id), safe_wrapper(RoModules.get_player_thumbnail, userId[0], "420x420", interaction.guild.shard_id), safe_wrapper(RoModules.last_online, userId[0], interaction.guild.shard_id), safe_wrapper(RoModules.get_groups, userId[0], interaction.guild.shard_id), safe_wrapper(RoModules.get_socials, userId[0], interaction.guild.shard_id)]
        previousUsernames, veriftype, userThumbnail, unformattedLastOnline, groups, (friends, followers, following) = await asyncio.gather(*tasks) # If it shows an error in your IDE, it's lying, all values are unpacked
        groups = len(groups['data'])
        embed.set_thumbnail(url=userThumbnail)
        if banned or userId[0] == 1: veriftype, previousUsernames = None, []
        lastOnlineFormatted, joinedTimestamp = await asyncio.gather(fancy_time(unformattedLastOnline), fancy_time(created))
        if name == displayname: embed.title = f"{name} {emojiTable.get('staff') if userId[0] in staffIds else emojiTable.get('verified') if verified else ''}"
        else: embed.title = f"{name} ({displayname}) {emojiTable.get('staff') if userId[0] in staffIds else emojiTable.get('verified') if verified else ''}"
        embed.colour = 0x00ff00
        embed.url = f"https://www.roblox.com/users/{userId[0]}/profile" if not banned else None
        embed.add_field(name="User ID:", value=f"`{userId[0]}`", inline=True)
        embed.add_field(name="Account Status:", value="`Terminated`" if banned else "`Okay`" if not banned else "`N/A (*Nil*)`", inline=True)
        if previousUsernames:
            formattedUsernames = ', '.join([f"`{username}`" for username in previousUsernames[:10]]) + (f", and {len(previousUsernames) - 10} more" if len(previousUsernames) > 10 else '')
            embed.add_field(name=f"Previous Usernames ({len(previousUsernames)}):", value=formattedUsernames, inline=False)
        if veriftype is not None: embed.add_field(name="Verified Email:", value="`N/A (*Nil*)`" if veriftype == -1 else "`N/A (*-1*)`" if veriftype == 0 else "`Verified, hat present`" if veriftype == 1 else "`Verified, sign present`" if veriftype == 2 else "`Unverified`" if veriftype == 3 else "`Verified, sign & hat present`" if veriftype == 4 else "`N/A`", inline=True)
        if description: embed.add_field(name="Description:", value=f"`{description}`", inline=False)
        embed.add_field(name="Joined:", value=f"`{joinedTimestamp}`", inline=True)
        embed.add_field(name="Last Online:", value=f"`{lastOnlineFormatted}`", inline=True)
        embed.add_field(name="Groups:", value=f"`{groups}`", inline=True)
        embed.add_field(name="Friends:", value=f"`{friends}`", inline=True)
        embed.add_field(name="Followers:", value=f"`{followers}`", inline=True)
        embed.add_field(name="Following:", value=f"`{following}`", inline=True)
        if userId[0] == 5192280939: embed.set_footer(text="Follow this person for a surprise on your whois profile")
        if userId[0] in autmnFollowers: embed.set_footer(text="This user is certifiably pog")
        privateInventory, isEdited = True, False
        if not banned and userId[0] != 1:
            isEdited = True
            embed.description = "***Currently calculating more statistics...***"
            messageId = (await interaction.followup.send(embed=embed)).id
            try: privateInventory, totalRap, totalValue, _ = await RoModules.get_limiteds(userId[0], roliData, interaction.guild.shard_id) # VERY slow when user has a lot of limiteds
            except Exception: privateInventory, totalRap, totalValue = False, "Failed to fetch", "Failed to fetch"
        if not privateInventory:
            embed.add_field(name="Total RAP:", value=f"`{totalRap}`", inline=True)
            embed.add_field(name="Total Value:", value=f"`{totalValue}`", inline=True)
        if not banned: embed.add_field(name="Privated Inventory:", value=f"`{privateInventory}`", inline=True)
        embed.description = None
        if isEdited: await interaction.followup.edit_message(messageId, embed=embed)
        else: await interaction.followup.send(embed=embed)
    except Exception as e: await handle_error(e, interaction, "whois", interaction.guild.shard_id, "User")

@client.tree.command()
@discord.app_commands.checks.cooldown(3, 60, key=lambda i: i.user.id)
async def ownsitem(interaction: discord.Interaction, user: str, item_id: int):
    """Check if a player owns a specific item"""
    await interaction.response.defer(ephemeral=False)
    embed = discord.Embed(color=0xFF0000)
    if not (await validate_user(interaction, embed)): return
    try:
        try:
            user_id = [int(user), None] if user.isdigit() else (await RoModules.convert_to_id(user, interaction.guild.shard_id))[:2]
            if not (await validate_user(interaction, embed, user_id[0])): return
            if user_id[1] is None: user_id[1] = (await RoModules.convert_to_username(user_id[0], interaction.guild.shard_id))[0]
        except Exception as e:
            if await handle_error(e, interaction, "ownsitem", interaction.guild.shard_id, "User"): return
        try: data = await RoModules.owns_item(user_id[0], item_id, interaction.guild.shard_id)
        except Exception as e:
            if await handle_error(e, interaction, "ownsitem", interaction.guild.shard_id, "Item"): return
        if data[0] is None:
            if data[2] == "The specified user does not exist!": embed.description = "User does not exist or has been banned."
            elif data[2] == "The specified Asset does not exist!": embed.description = "Item does not exist."
            else: embed.description = f"Failed to retrieve data: {data[2]}"
            await interaction.followup.send(embed=embed)
            return
        if data[0]:
            embed.set_thumbnail(url=await RoModules.get_item_thumbnail(item_id, "420x420", interaction.guild.shard_id))
            embed.colour = 0x00FF00
            embed.title = f"{user_id[1]} owns {data[1]} {data[2]}{'s' if data[1] > 1 else ''}!"
            uaids_to_display = data[3][:100]
            embed.description = "**UAIDs:**\n" + ', '.join([f"`{uaid}`" for uaid in map(str, uaids_to_display)])
            remaining_count = max(0, data[1] - 100)
            if remaining_count > 0: embed.description += f", and {remaining_count} more."
            await interaction.followup.send(embed=embed)
        else:
            embed.description = f"{user_id[1]} doesn't own this item!"
            await interaction.followup.send(embed=embed)
    except Exception as e: await handle_error(e, interaction, "ownsitem", interaction.guild.shard_id, "Item")

@client.tree.command()
@discord.app_commands.checks.cooldown(3, 60, key=lambda i: i.user.id)
async def ownsbadge(interaction: discord.Interaction, user: str, badge: int):
    """Check if a player owns a specified badge and return it's award date"""
    await interaction.response.defer(ephemeral=False)
    embed = discord.Embed(color=0xFF0000)
    if not (await validate_user(interaction, embed)): return
    try:
        try:
            user_id = [int(user), None] if user.isdigit() else (await RoModules.convert_to_id(user, interaction.guild.shard_id))[:2]
            if user_id[1] is None: user_id[1] = (await RoModules.convert_to_username(user_id[0], interaction.guild.shard_id))[0]
        except Exception as e:
            if await handle_error(e, interaction, "ownsbadge", interaction.guild.shard_id, "User"): return
        if not (await validate_user(interaction, embed, user_id[0])): return
        try: ownsBadge = await RoModules.owns_badge(user_id[0], badge, interaction.guild.shard_id)
        except Exception as e: 
            if await handle_error(e, interaction, "ownsbadge", interaction.guild.shard_id, "Badge"): return
        if ownsBadge[0]:
            embed.set_thumbnail(url=await RoModules.get_badge_thumbnail(badge, interaction.guild.shard_id))
            embed.colour = 0x00FF00
            embed.title = f"{user_id[1]} owns this badge!"
            embed.description = f"Badge was awarded `{await fancy_time(ownsBadge[1])}`"
            await interaction.followup.send(embed=embed)
        else:
            embed.description = f"{user_id[1]} doesn't own the specified badge!"
            await interaction.followup.send(embed=embed)
    except Exception as e: await handle_error(e, interaction, "ownsbadge", interaction.guild.shard_id, "Badge")

@client.tree.command()
@discord.app_commands.checks.cooldown(3, 60, key=lambda i: i.user.id)
async def limited(interaction: discord.Interaction, limited: str):
    """Returns a limited ID, the rap, and value of a specified limited"""
    await interaction.response.defer(ephemeral=False)
    embed = discord.Embed(color=0xFF0000)
    if not (await validate_user(interaction, embed)): return
    try:
        try: limited_id, name, acronym, rap, value = await RoModules.get_rolidata_from_item(roliData, limited)
        except Exception as e:  
            if await handle_error(e, interaction, "limited", interaction.guild.shard_id, "Limited"): return
        if limited_id != -1:
            embed.set_thumbnail(url=await RoModules.get_item_thumbnail(limited_id, "420x420", interaction.guild.shard_id))
            embed.colour = 0x00FF00
            embed.title = f"{name} ({acronym})" if acronym != "" else f"{name}"
            embed.url = f"https://www.roblox.com/catalog/{limited_id}/"
            embed.description = f"ID: `{limited_id}`\nRAP: `{rap}`\nValue: `{value}`"
            await interaction.followup.send(embed=embed)
        else:
            embed.description = f"Failed to find item! Make sure you spelled it correctly and used proper punctuation."
            await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as e: await handle_error(e, interaction, "limited", interaction.guild.shard_id, "Limited")

@client.tree.command()
@discord.app_commands.checks.cooldown(5, 60, key=lambda i: i.user.id)
async def isfriendswith(interaction: discord.Interaction, user1: str, user2: str):
    """Check whether a user is friended to another user"""
    # Technically we only have to check through one player as it's a mutual relationship
    await interaction.response.defer(ephemeral=False)
    embed = discord.Embed(color=0xFF0000)
    if not (await validate_user(interaction, embed)): return
    try:
        try: user_id1 = [int(user1), None] if user1.isdigit() else (await RoModules.convert_to_id(user1, interaction.guild.shard_id))[:2]
        except Exception as e:
            if await handle_error(e, interaction, "isfriendswith", interaction.guild.shard_id, "User"): return
        if user2.isdigit(): user2 = int(user2)
        if not (await validate_user(interaction, embed, user_id1[0])): return
        try: userfriends = await RoModules.get_friends(user_id1[0], interaction.guild.shard_id)
        except Exception as e: 
            if await handle_error(e, interaction, "isfriendswith", interaction.guild.shard_id, "User"): return
        friended = False
        if user_id1[1] is None: user_id1[1] = (await RoModules.convert_to_username(user_id1[0], interaction.guild.shard_id))[0]
        for friends in userfriends['data']:
            friendName = str(friends['name']).lower() if not str(friends['name']).isdigit() else str(friends['name'])
            secondUser = str(user2).lower() if not str(user2).isdigit() else user2
            if friends['id'] == secondUser or friendName == secondUser:
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
            embed.colour = 0x00FF00
            embed.description = f"{user_id1[1]} is friends with {friend_name}!"
            await interaction.followup.send(embed=embed)
            return
        else:
            embed.description = f"{user_id1[1]} does not have this user friended."
            await interaction.followup.send(embed=embed)
    except Exception as e: await handle_error(e, interaction, "isfriendswith", interaction.guild.shard_id, "User")

@client.tree.command()
@discord.app_commands.checks.cooldown(5, 60, key=lambda i: i.user.id)
async def isingroup(interaction: discord.Interaction, user: str, group: int):
    """Check whether a user is in a group or not"""
    await interaction.response.defer(ephemeral=False)
    embed = discord.Embed(color=0xFF0000)
    if not (await validate_user(interaction, embed)): return
    try:
        try: user_id = [int(user), None] if user.isdigit() else (await RoModules.convert_to_id(user, interaction.guild.shard_id))[:2]
        except Exception as e: 
            if await handle_error(e, interaction, "isingroup", interaction.guild.shard_id, "User"): return
        if not (await validate_user(interaction, embed, user_id[0])): return
        try: 
            if user_id[1] is None: user_id[1] = (await RoModules.convert_to_username(user_id[0], interaction.guild.shard_id))[0]
        except Exception as e: 
            if await handle_error(e, interaction, "isingroup", interaction.guild.shard_id, "User"): return
        usergroups = await RoModules.get_groups(user_id[0], interaction.guild.shard_id)
        ingroup = False
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
            embed.set_thumbnail(url=await RoModules.get_group_emblem(groupid, "420x420", interaction.guild.shard_id))
            embed.colour = 0x00FF00
            embed.title = f"{user_id[1]} is in group `{groupname}`!"
            embed.description = f"Role: `{grouprole}`"
            await interaction.followup.send(embed=embed)
            return
        else:
            embed.description = f"{user_id[1]} is not in this group."
            await interaction.followup.send(embed=embed)
    except Exception as e: await handle_error(e, interaction, "isingroup", interaction.guild.shard_id, "Group ID")

@client.tree.command()
@discord.app_commands.checks.cooldown(2, 60, key=lambda i: i.user.id)
async def clothingtexture(interaction: discord.Interaction, clothing_id: int):
    """Get the texture file of a clothing item"""
    await interaction.response.defer(ephemeral=False)
    embed = discord.Embed(color=0xFF0000)
    if not (await validate_user(interaction, embed)): return
    try:
        async def send_image(clothing_id: int):
            uploaded_image = discord.File(f'cache/clothing/{clothing_id}.png', filename=f"rowhois-{clothing_id}.png")
            await interaction.followup.send("", file=uploaded_image)
            return
        try:
            async with aiofiles.open(f'cache/clothing/{clothing_id}.png', 'rb'): await send_image(clothing_id)
        except FileNotFoundError:
            try: initAsset = await Roquest.GetFileContent(clothing_id, shard_id=interaction.guild.shard_id)
            except ErrorDict.AssetNotAvailable:
                embed.description = "Cannot fetch moderated assets."
                await interaction.followup.send(embed=embed)
                return
            except Exception as e:
                if await handle_error(e, interaction, "getclothingtexture", interaction.guild.shard_id, "Asset"): return
            if not initAsset:
                embed.description = "Failed to get clothing texture!"
                await interaction.followup.send(embed=embed)
                return
            initAssetContent = io.BytesIO(initAsset)
            initAssetContent = initAssetContent.read().decode()
            match = re.search(r'<url>.*id=(\d+)</url>', initAssetContent)
            if match:
                async with aiofiles.open(f'cache/clothing/{clothing_id}.png', 'wb') as cached_image:
                    try: downloadedAsset = await Roquest.GetFileContent(match.group(1), shard_id=interaction.guild.shard_id)
                    except ErrorDict.AssetNotAvailable:
                        embed.description = "Cannot fetch moderated assets."
                        await interaction.followup.send(embed=embed)
                        await cached_image.close()
                        return
                    except Exception as e:
                        if await handle_error(e, interaction, "getclothingtexture", interaction.guild.shard_id, "Asset"):
                            await cached_image.close()
                            return
                    if not downloadedAsset or len(downloadedAsset) < 512: # Not likely to trigger, prevents caching malformed images
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
    except UnicodeDecodeError:
        embed.description = "Invalid item type."
        await interaction.followup.send(embed=embed)
    except Exception as e: await handle_error(e, interaction, "getclothingtexture", interaction.guild.shard_id, "Clothing ID")

@client.tree.command()
@discord.app_commands.checks.cooldown(2, 60, key=lambda i: i.user.id)
async def itemdetails(interaction: discord.Interaction, item: int):
    """Get advanced details about a catalog item"""
    await interaction.response.defer(ephemeral=False)
    embed = discord.Embed(color=0xFF0000)
    if not (await validate_user(interaction, embed)): return
    try:
        try: data = await RoModules.get_item(item, interaction.guild.shard_id)
        except Exception as e:
            if await handle_error(e, interaction, "getitemdetails", interaction.guild.shard_id, "Item"): return
        embed.url = f"https://www.roblox.com/catalog/{item}"
        if data["CollectibleItemId"] is not None: isCollectible = True
        else: isCollectible = False
        embed.title = f"{emojiTable.get('limited') if data['IsLimited'] else emojiTable.get('limitedu') if data['IsLimitedUnique'] else emojiTable.get('collectible') if isCollectible else ''} {data['Name']}"
        embed.add_field(name="Creator:", value=f"`{data['Creator']['Name']}` (`{data['Creator']['CreatorTargetId']}`) {emojiTable.get('staff') if userid in staffIds else emojiTable.get('verified') if data['Creator']['HasVerifiedBadge'] else ''}")
        if data['Description'] != "": embed.add_field(name="Description:", value=f"`{data['Description']}`", inline=False)
        embed.add_field(name="Created:", value=f"`{(await fancy_time(data['Created']))}`", inline=True)
        embed.add_field(name="Updated:", value=f"`{(await fancy_time(data['Updated']))}`", inline=True)
        if isCollectible:
            embed.add_field(name="Quantity:", value=f"`{data['CollectiblesItemDetails']['TotalQuantity']}`", inline=True)
            if data['CollectiblesItemDetails']['CollectibleLowestResalePrice'] is not None and data['IsForSale']: embed.add_field(name="Lowest Price:", value=f"{emojiTable.get('robux')} `{data['CollectiblesItemDetails']['CollectibleLowestResalePrice']}`", inline=True)
            elif data["IsForSale"]: embed.add_field(name="Lowest Price:", value=f"`No resellers`", inline=True)
        if data["IsForSale"]:
            if data["Remaining"] is not None and data["Remaining"] != 0: embed.add_field(name="Remaining:", value=f"`{data['Remaining']}`", inline=True)
            if not (data["IsLimited"] or data["Remaining"] == 0 or isCollectible): embed.add_field(name="Price:", value=f"{emojiTable.get('robux')} `{data['PriceInRobux']}`", inline=True)
        embed.set_thumbnail(url=await RoModules.get_item_thumbnail(item, "420x420", interaction.guild.shard_id))
        embed.colour = 0x00FF00
        await interaction.followup.send(embed=embed)
    except Exception as e: await handle_error(e, interaction, "getitemdetails", interaction.guild.shard_id, "Item ID")

@client.tree.command()
@discord.app_commands.checks.cooldown(2, 60, key=lambda i: i.user.id)
async def membership(interaction: discord.Interaction, user: str):
    """Checks whether a user has premium and if they had Builders Club"""
    await interaction.response.defer(ephemeral=False)
    embed = discord.Embed(color=0xFF0000)
    if not (await validate_user(interaction, embed)): return
    try:
        try: user_id = [int(user), None] if user.isdigit() else (await RoModules.convert_to_id(user, interaction.guild.shard_id))[:2]
        except Exception as e:
            if await handle_error(e, interaction, "getmembership", interaction.guild.shard_id, "User ID"): return
        if not (await validate_user(interaction, embed, user_id[0])): return
        try: userProfile = await RoModules.get_player_profile(user_id[0], interaction.guild.shard_id)
        except Exception as e:
            if await handle_error(e, interaction, "getmembership", interaction.guild.shard_id, "User"): return
        if user_id[1] is None: user_id[1] = (userProfile[3])
        try: data = await RoModules.get_membership(user_id[0], interaction.guild.shard_id)
        except Exception as e:
            if await handle_error(e, interaction, "getmembership", interaction.guild.shard_id, "User"): return
        if all(not data[i] for i in range(1, 4)): noTiers = True
        else: noTiers = False
        newline = '\n'
        embed.title = f"{user_id[1]}'s memberships:"
        embed.description = f"{(emojiTable.get('premium') + ' `Premium`' + newline) if data[0] else ''}{(emojiTable.get('bc') + ' `Builders Club`' + newline) if data[1] else ''}{(emojiTable.get('tbc') + '`Turbo Builders Club`' + newline) if data[2] else ''}{(emojiTable.get('obc') + ' `Outrageous Builders Club`' + newline) if data[3] else ''}{(str(user_id[1]) + ' has no memberships.') if noTiers else ''}"
        embed.colour = 0x00FF00
        await interaction.followup.send(embed=embed)
    except Exception as e: await handle_error(e, interaction, "getmembership", interaction.guild.shard_id, "User")

@client.tree.command()
@discord.app_commands.checks.cooldown(3, 60, key=lambda i: i.user.id)
async def group(interaction: discord.Interaction, group: int):
    """Get detailed group information from a Group ID"""
    await interaction.response.defer(ephemeral=False)
    embed = discord.Embed(color=0xFF0000)
    if not (await validate_user(interaction, embed)): return
    try:
        try: groupInfo = await RoModules.get_group(group, interaction.guild.shard_id)
        except Exception as e:
            if await handle_error(e, interaction, "group", interaction.guild.shard_id, "Group"): return
        groupThumbnail = await RoModules.get_group_emblem(group, "420x420", interaction.guild.shard_id)
        if groupThumbnail: embed.set_thumbnail(url=groupThumbnail)
        embed.title = f"{groupInfo[0]}{(' ' + emojiTable.get('verified')) if groupInfo[3] else ''}"
        embed.add_field(name="Group ID:", value=f"`{group}`")
        embed.add_field(name="Status:", value=f"`{'Locked' if groupInfo[8] else 'Okay'}`", inline=True)
        embed.add_field(name="Created:", value=f"`{await fancy_time(groupInfo[2])}`", inline=True)
        if groupInfo[4] is not None: embed.add_field(name="Owner:", value=f"`{groupInfo[4][0]}` (`{groupInfo[4][1]}`) {(' ' + emojiTable.get('verified')) if groupInfo[4][2] else ''}", inline=True)
        else: embed.add_field(name="Owner:", value=f"Nobody!", inline=True)
        embed.add_field(name="Members:", value=f"`{groupInfo[6]}`", inline=True)
        embed.add_field(name="Joinable:", value=f"`{'False' if groupInfo[8] else 'True' if groupInfo[7] else 'False'}`", inline=True)
        if groupInfo[5] is not None:
            if groupInfo[5][0] != "": embed.add_field(name="Shout:", value=f"`{groupInfo[5][0]}` -- `{groupInfo[5][1]}` (`{groupInfo[5][2]}`) {('' + emojiTable.get('verified')) if groupInfo[5][3] else ''}", inline=False)
        if groupInfo[1] != "": embed.add_field(name="Group Description:", value=f"`{groupInfo[1]}`", inline=False)
        embed.colour = 0x00FF00
        await interaction.followup.send(embed=embed)
    except Exception as e: await handle_error(e, interaction, "group", interaction.guild.shard_id, "Group ID")

@client.tree.command()
@discord.app_commands.checks.cooldown(4, 60, key=lambda i: i.user.id)
async def checkusername(interaction: discord.Interaction, username: str):
    """Check if a username is available"""
    await interaction.response.defer(ephemeral=False)
    embed = discord.Embed(color=0xFF0000)
    if not (await validate_user(interaction, embed)): return
    try:
        try: usernameInfo = await RoModules.validate_username(username, interaction.guild.shard_id)
        except Exception as e: 
            if await handle_error(e, interaction, "username", interaction.guild.shard_id, "Username"): return
        if usernameInfo[0] == 0: 
            embed.colour = 0x00FF00
            embed.description = "Username is available!"
        elif usernameInfo[0] == 1: embed.description = "Username is taken."
        else: embed.description = f"Username not available.\n**Reason:** {usernameInfo[1]}"
        await interaction.followup.send(embed=embed)
    except Exception as e: await handle_error(e, interaction, "username", interaction.guild.shard_id, "Username")

@client.tree.command()
@discord.app_commands.checks.cooldown(3, 60, key=lambda i: i.user.id)
async def robloxbadges(interaction: discord.Interaction, user: str):
    """Check what Roblox badges a player has"""
    await interaction.response.defer(ephemeral=False)
    embed = discord.Embed(color=0xFF0000)
    if not (await validate_user(interaction, embed)): return
    try:
        try: 
            user_id = [int(user), None] if user.isdigit() else (await RoModules.convert_to_id(user, interaction.guild.shard_id))[:2]
            if user_id[1] is None: user_id[1] = (await RoModules.convert_to_username(user_id[0], interaction.guild.shard_id))[0]
        except Exception as e:
            if await handle_error(e, interaction, "robloxbadges", interaction.guild.shard_id, "User"): return
        if not (await validate_user(interaction, embed, user_id[0])): return
        try: badges = await RoModules.roblox_badges(user_id[0], interaction.guild.shard_id)
        except Exception as e:
            if await handle_error(e, interaction, "robloxbadges", interaction.guild.shard_id, "User"): return
        if len(badges[0]) <= 0:
            embed.description = "This user has no Roblox badges."
            await interaction.followup.send(embed=embed)
            return
        descriptor = ""
        for badge in badges[0]:
            badge_name = badges[1].get(badge)
            if badge_name: descriptor += f"{emojiTable.get(str(badge_name).lower())} `{badge_name}`\n"
        if descriptor == "":  descriptor = "This user has no Roblox badges."
        embed.set_thumbnail(url=await RoModules.get_player_headshot(user_id[0], "420x420", interaction.guild.shard_id))
        embed.colour = 0x00FF00
        embed.title = f"{user_id[1]}'s Roblox Badges:"
        embed.description = descriptor
        await interaction.followup.send(embed=embed)
    except Exception as e: await handle_error(e, interaction, "robloxbadges", interaction.guild.shard_id, "User")
