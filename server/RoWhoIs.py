from server import Roquest, RoModules
from utils import logger, ErrorDict, gUtils, typedefs
import asyncio, discord, io, aiohttp, signal, datetime, inspect, time
from pathlib import Path
from typing import Any, Optional, Literal

def run(productionmode: bool, version: str, config) -> bool:
    """Runs the server"""
    try:
        global productionMode, staffIds, optOut, userBlocklist, shortHash, emojiTable, botToken, assetBlocklist, whoIsDonors
        emojiTable = {key: config['Emojis'][key] for key in config['Emojis']}
        botToken = {"topgg": config['Authentication']['topgg'], "dbl": config['Authentication']['dbl']}
        shortHash, productionMode = version, productionmode
        staffIds, optOut, userBlocklist, assetBlocklist, whoIsDonors = config['RoWhoIs']['admin_ids'], config['RoWhoIs']['opt_out'], config['RoWhoIs']['banned_users'], config['RoWhoIs']['banned_assets'], config['RoWhoIs']['donors']
        client.uptime = datetime.datetime.utcnow()
        if not productionMode: loop.run_until_complete(client.start(config['Authentication']['testing']))
        else: loop.run_until_complete(client.start(config['Authentication']['production']))
        return True
    except KeyError: raise ErrorDict.MissingRequiredConfigs

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
    global roliData, lastRoliUpdate
    while True:
        try:
            newData = await Roquest.RoliData()
            if newData is not None:
                lastRoliUpdate = datetime.datetime.utcnow()
                roliData = newData
            else: await log_collector.error("Failed to update Rolimons data.")
        except ErrorDict.UnexpectedServerResponseError: pass
        except Exception as e: await log_collector.error(f"Error updating Rolimons data: {e}")
        await asyncio.sleep(3600)

async def heartbeat() -> None:
    global heartBeat
    """Used for determining if Roblox is online"""
    while True:
        try: heartBeat = await Roquest.heartbeat()
        except Exception as e: await log_collector.error(f"Error in heartbeat: {e}")
        await asyncio.sleep(60)

async def validate_user(interaction: discord.Interaction, embed: discord.Embed, user_id: int = None, requires_entitlement: bool = False, requires_connection: bool = True, kind_upsell: bool = True) -> bool:
    """Validates if a user has sufficient access to a command. Used for blocklists and entitlement checks."""
    global optOut, userBlocklist
    if interaction.user.id in userBlocklist:
        await log_collector.warn(f"Blocklist user {interaction.user.id} attempted to call a command and was denied!")
        embed.description = "You have been permanently banned from using RoWhoIs. In accordance to our [Terms of Service](https://rowhois.com/terms-of-service/), we reserve the right to block any user from using our service."
    elif user_id and user_id in optOut:
        await log_collector.warn(f"Blocklist user {user_id} was requested by {interaction.user.id} and denied!")
        embed.description = "This user has requested to opt-out of RoWhoIs."
    elif not heartBeat and requires_connection:
        await log_collector.info("heartBeat is False, deflecting a command properly...")
        embed.description = "Roblox is currently experiencing downtime. Please try again later."
    elif len(interaction.entitlements) == 0 and productionMode and requires_entitlement:
        if not kind_upsell:
            await interaction.response.require_premium()
            return False
        embed.description = f"This advanced option requires RoWhoIs {emojiTable.get('subscription')}"
    else: return True
    embed.title = None
    embed.colour = 0xFF0000
    if interaction.response.is_done(): await interaction.followup.send(embed=embed, ephemeral=True)
    else: await interaction.response.send_message(embed=embed, ephemeral=True)
    return False

async def handle_error(error, interaction: discord.Interaction, command: str, shard_id: int, context: str = "Requested resource") -> bool:
    """Handles both user-facing and backend errors, even if they are undocumented."""
    embed = discord.Embed(color=0xFF0000)
    if isinstance(error, ErrorDict.DoesNotExistError): embed.description = f"{context} doesn't exist."
    elif isinstance(error, ErrorDict.MismatchedDataError): embed.description = f"{context} is invalid."
    elif isinstance(error, ErrorDict.RatelimitedError): embed.description = "RoWhoIs is experienceing unusually high demand. Please try again."
    elif isinstance(error, discord.errors.NotFound): return True
    else:
        if isinstance(error, ErrorDict.InvalidAuthorizationError): await Roquest.token_renewal()
        embed.description = "Whoops! An unknown error occurred. Please try again later."
        await log_collector.error(f"Error in the {command} command: {type(error)}, {error}", shard_id=shard_id)
    if interaction.response.is_done(): await interaction.followup.send(embed=embed, ephemeral=True)
    else: await interaction.response.send_message(embed=embed, ephemeral=True)
    return True

async def check_cooldown(interaction: discord.Interaction, intensity: str, cooldown_seconds: int = 60) -> bool:
    """Custom cooldown handler for user commands because discord.py's implementation of it sucked
    True = On cooldown, False = Not on cooldown
    """
    global userCooldowns
    try:
        currentTime = datetime.datetime.now()
        for userId in list(userCooldowns.keys()):
            for command in list(userCooldowns[userId].keys()):
                userCooldowns[userId][command] = [timestamp for timestamp in userCooldowns[userId][command] if currentTime - timestamp <= datetime.timedelta(seconds=cooldown_seconds)]
                if not userCooldowns[userId][command]: del userCooldowns[userId][command]
            if not userCooldowns[userId]: del userCooldowns[userId]
        userId = interaction.user.id
        commandName = inspect.stack()[1].function
        premiumCoolDict = {"extreme": 5, "high": 6, "medium": 7, "low": 8}
        stdCoolDict = {"extreme": 2, "high": 3, "medium": 4, "low": 5}
        if len(interaction.entitlements) >= 1 and productionMode or not productionMode: maxCommands = premiumCoolDict.get(intensity)
        else: maxCommands = stdCoolDict.get(intensity)
        if userId not in userCooldowns: userCooldowns[userId] = {}
        if commandName not in userCooldowns[userId]: userCooldowns[userId][commandName] = []
        recentTimestamps = [timestamp for timestamp in userCooldowns[userId][commandName] if currentTime - timestamp <= datetime.timedelta(seconds=cooldown_seconds)]
        if len(recentTimestamps) < maxCommands:
            recentTimestamps.append(currentTime)
            userCooldowns[userId][commandName] = recentTimestamps
            return False
        else:
            earliestTimestamp = min(recentTimestamps)
            remainingSeconds = max(0, round(((earliestTimestamp + datetime.timedelta(seconds=cooldown_seconds)) - currentTime).total_seconds()))
            await interaction.response.send_message(f"*Your enthusiasm is greatly appreciated, but please slow down! Try again in **{remainingSeconds}** seconds.*", ephemeral=True)
            return True
    except Exception as e:
        await log_collector.error(f"Error in cooldown handler: {e} | Command: {commandName} | User: {userId} | Returning False... ")
        return False

shardAnalytics = gUtils.ShardAnalytics(0, False)
log_collector = logger.AsyncLogCollector("logs/main.log")
client = RoWhoIs(intents=discord.Intents.default())
loop = asyncio.get_event_loop()
loop.create_task(update_rolidata())
loop.create_task(heartbeat())
loop.add_signal_handler(signal.SIGINT, lambda: asyncio.create_task(shutdown()))
userCooldowns = {}

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
    await log_collector.info(f"RoWhoIs has joined a new server. Total servers: {len(client.guilds)}. {'Updating registries...' if productionMode else ''}")
    if productionMode:
        try:
            async with aiohttp.ClientSession() as session:
                if botToken.get("topgg") != "":
                    async with session.post(f"https://top.gg/api/bots/{client.user.id}/stats", headers={"Authorization": botToken.get("topgg")}, json={"server_count": len(client.guilds)}): pass
                if botToken.get("dbl") != "":
                    async with session.post(f"https://discordbotlist.com/api/v1/bots/{client.user.id}/stats", headers={"Authorization": botToken.get("dbl")}, json={"guilds": len(client.guilds)}): pass
        except Exception as e: await log_collector.error(f"Failed to update registries. {e}")

@client.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    if isinstance(error, discord.app_commands.CommandInvokeError): await log_collector.critical(f"Interaction invoke error:{type(error)}, {error} invoked by {interaction.user.id}")
    else:
        await log_collector.critical(f"Unexpected error occured during core command function: {type(error)}, {error} invoked by {interaction.user.id}")
        await interaction.followup.send(f"Whoops! Looks like we encountered an unexpected error. We've reported this to our dev team and we'll fix it shortly!", ephemeral=True)

@client.tree.command()
async def help(interaction: discord.Interaction):
    """List all of the commands RoWhoIs supports & what they do"""
    if await check_cooldown(interaction, "low"): return
    embedVar = discord.Embed(title="RoWhoIs Commands", color=3451360)
    if not (await validate_user(interaction, embedVar, requires_connection=False)): return
    embedVar.add_field(name="whois", value="Get detailed profile information from a User ID/Username", inline=True)
    embedVar.add_field(name="clothingtexture", value="Retrieves the texture file for a 2D clothing asset", inline=True)
    embedVar.add_field(name="userid", value="Get a User ID based off a username", inline=True)
    embedVar.add_field(name="username", value="Get a username based off a User ID", inline=True)
    embedVar.add_field(name="ownsitem", value="Retrieve whether a user owns an item or not. Works with players who have a private inventory", inline=True)
    embedVar.add_field(name="ownsbadge", value="Retrieve whether a user owns a badge or not. Works with players who have a private inventory", inline=True)
    embedVar.add_field(name="isfriendswith", value="Check if two players are friended", inline=True)
    embedVar.add_field(name="group", value="Get detailed group information from a Group ID", inline=True)
    embedVar.add_field(name="groupclothing " + f"{emojiTable.get('subscription')}", value="Retrieves bulk clothing textures from a group", inline=True)
    embedVar.add_field(name="userclothing " + f"{emojiTable.get('subscription')}", value="Retrieves bulk clothing textures from a user", inline=True)
    embedVar.add_field(name="isingroup", value="Check if a player is in the specified group", inline=True)
    embedVar.add_field(name="limited", value="Returns a limited ID, the rap, and value of the specified limited", inline=True)
    embedVar.add_field(name="itemdetails", value="Returns details about a catalog item", inline=True)
    embedVar.add_field(name="membership", value="Check if a player has Premium or has had Builders Club", inline=True)
    embedVar.add_field(name="checkusername", value="Check if a username is available", inline=True)
    embedVar.add_field(name="robloxbadges", value="Shows what Roblox badges a player has", inline=True)
    embedVar.add_field(name="asset", value="Fetches an asset file from an asset ID. Not recommended for clothing textures", inline=True)
    embedVar.add_field(name="about", value="Shows a bit about RoWhoIs and advanced statistics", inline=True)
    embedVar.set_footer(text=f"{'Get RoWhoIs+ to use + commands' if len(interaction.entitlements) == 0 and productionMode else 'You have access to RoWhoIs+ features'}")
    await interaction.response.send_message(embed=embedVar)

@client.tree.command()
async def about(interaction: discord.Interaction):
    """Shows detailed information about RoWhoIs"""
    if await check_cooldown(interaction, "low"): return
    embed = discord.Embed(color=3451360)
    if not (await validate_user(interaction, embed, requires_connection=False)): return
    shard = await gUtils.shard_metrics(interaction)
    try:
        embed.title = "About RoWhoIs"
        embed.set_thumbnail(url="https://rowhois.com/rwi-pfp-anim.gif")
        embed.set_author(name="Made with <3 by aut.m (249681221066424321)", icon_url="https://rowhois.com/profile_picture.jpeg")
        embed.description = "RoWhoIs provides advanced information about Roblox users, groups, and assets. It's designed to be fast, reliable, and easy to use."
        embed.add_field(name="Version", value=f"`{shortHash}`", inline=True)
        uptime = datetime.datetime.utcnow() - client.uptime
        days, remainder = divmod(uptime.total_seconds(), 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, _ = divmod(remainder, 60)
        embed.add_field(name="Uptime", value=f"`{int(days)} day{'s' if int(days) != 1 else ''}, {int(hours)} hour{'s' if int(hours) != 1 else ''}, {int(minutes)} minute{'s' if int(minutes) != 1 else ''}`", inline=True)
        embed.add_field(name="Roblox Connection", value=f"{':green_circle: `Online' if heartBeat else ':red_circle: `Offline'}`", inline=True)
        embed.add_field(name="Last Rolimons Update", value=f"{await gUtils.fancy_time(lastRoliUpdate)}", inline=True)
        embed.add_field(name="Servers", value=f"`{len(client.guilds)}`", inline=True)
        embed.add_field(name="Users", value=f"`{sum(guild.member_count if guild.member_count is not None else 0 for guild in client.guilds)}`", inline=True)
        embed.add_field(name="Shards", value=f"`{client.shard_count}`", inline=True)
        embed.add_field(name="Shard ID", value=f"`{shard}`", inline=True)
        embed.add_field(name="Cache Size", value=f"`{round(sum(f.stat().st_size for f in Path('cache/').glob('**/*') if f.is_file()) / 1048576, 1)} MB`", inline=True)
        embed.add_field(name="RoWhoIs+", value=f"`{'Not Subscribed :(`' if len(interaction.entitlements) == 0 and productionMode else 'Subscribed` ' + emojiTable.get('subscription')}", inline=True)
        await interaction.response.send_message(embed=embed)
    except Exception as e: await handle_error(e, interaction, "userid", shard, "User")

@client.tree.command()
async def userid(interaction: discord.Interaction, username: str, download: bool = False):
    """Get a User ID from a username"""
    if await check_cooldown(interaction, "low"): return
    embed = discord.Embed(color=0xFF0000)
    if not (await validate_user(interaction, embed, requires_entitlement=download)): return
    shard = await gUtils.shard_metrics(interaction)
    try:
        user = await RoModules.convert_to_id(username, shard)
        if not (await validate_user(interaction, embed, user.id)): return
        bust, headshot = await asyncio.gather(RoModules.get_player_bust(user.id, "420x420", shard), RoModules.get_player_headshot(user.id,  shard))
        embed.set_thumbnail(url=bust)
        embed.set_author(name=f"{user.username} { '(' + user.nickname + ')' if user.username != user.nickname else ''}", icon_url=headshot, url=f"https://www.roblox.com/users/{user.id}/profile")
        embed.description = f"{emojiTable.get('staff') if user.id in staffIds else ''} {emojiTable.get('donor') if user.id in whoIsDonors else ''} {emojiTable.get('verified') if user.verified else ''}"
        embed.add_field(name="User ID:", value=f"`{user.id}`", inline=True)
        embed.colour = 0x00FF00
        if download:
            csv = "username, id, nickname, verified\n" + "\n".join([f"{user.username}, {user.id}, {user.nickname}, {user.verified}"])
            await interaction.response.send_message(embed=embed, file=discord.File(io.BytesIO(csv.encode()), filename=f"rowhois-userid-{user.id}.csv"))
        else: await interaction.response.send_message(embed=embed)
    except Exception as e: await handle_error(e, interaction, "userid", shard, "User")

@client.tree.command()
async def username(interaction: discord.Interaction, userid: int, download: bool = False):
    """Get a username from a User ID"""
    if await check_cooldown(interaction, "low"): return
    embed = discord.Embed(color=0xFF0000)
    if not (await validate_user(interaction, embed, userid, requires_entitlement=download)): return
    shard = await gUtils.shard_metrics(interaction)
    try:
        user = await RoModules.convert_to_username(userid, shard)
        bust, headshot = await asyncio.gather(RoModules.get_player_bust(user.id, "420x420", shard), RoModules.get_player_headshot(user.id, shard))
        embed.set_thumbnail(url=bust)
        embed.set_author(name=f"{user.username} { '(' + user.nickname + ')' if user.username != user.nickname else ''}", icon_url=headshot, url=f"https://www.roblox.com/users/{user.id}/profile")
        embed.description = f"{emojiTable.get('staff') if user.id in staffIds else ''} {emojiTable.get('donor') if user.id in whoIsDonors else ''} {emojiTable.get('verified') if user.verified else ''}"
        embed.add_field(name="Username:", value=f"`{user.username}`", inline=True)
        embed.colour = 0x00FF00
        if download:
            csv = "username, id, nickname, verified\n" + "\n".join([f"{user.username}, {user.id}, {user.nickname}, {user.verified}"])
            await interaction.response.send_message(embed=embed, file=discord.File(io.BytesIO(csv.encode()), filename=f"rowhois-userid-{user.id}"))
        else: await interaction.response.send_message(embed=embed)
    except Exception as e: await handle_error(e, interaction, "username", shard, "User")

@client.tree.command()
async def whois(interaction: discord.Interaction, user: str, download: bool = False):
    """Get detailed profile information from a User ID/Username"""
    if await check_cooldown(interaction, "high"): return
    embed = discord.Embed(color=0xFF0000)
    if not (await validate_user(interaction, embed, requires_entitlement=download)): return
    await interaction.response.defer(ephemeral=False)
    shard = await gUtils.shard_metrics(interaction)
    try:
        user = await RoModules.handle_usertype(user, shard)
        if not (await validate_user(interaction, embed, user.id)): return
        user.description, user.joined, user.banned = (await RoModules.get_player_profile(user.id, shard))[:3]
        if user.banned or user.id == 1: tasks = [RoModules.nil_pointer(), RoModules.nil_pointer(), gUtils.safe_wrapper(RoModules.get_player_thumbnail, user.id, "420x420", shard), gUtils.safe_wrapper(RoModules.last_online, user.id, shard), gUtils.safe_wrapper(RoModules.get_groups, user.id, shard), gUtils.safe_wrapper(RoModules.get_socials, user.id, shard), gUtils.safe_wrapper(RoModules.get_player_headshot, user.id, shard)]
        else: tasks = [gUtils.safe_wrapper(RoModules.get_previous_usernames, user.id, shard), gUtils.safe_wrapper(RoModules.check_verification, user.id, shard), gUtils.safe_wrapper(RoModules.get_player_thumbnail, user.id, "420x420", shard), gUtils.safe_wrapper(RoModules.last_online, user.id, shard), gUtils.safe_wrapper(RoModules.get_groups, user.id, shard), gUtils.safe_wrapper(RoModules.get_socials, user.id, shard), gUtils.safe_wrapper(RoModules.get_player_headshot, user.id, shard)]
        previousUsernames, veriftype, userThumbnail, user.online, groups, (user.friends, user.followers, user.following), userHeadshot = await asyncio.gather(*tasks) # If it shows an error in your IDE, it's lying, all values are unpacked
        embed.description = f"{emojiTable.get('staff') if user.id in staffIds else ''} {emojiTable.get('donor') if user.id in whoIsDonors else ''} {emojiTable.get('verified') if user.verified else ''}"
        embed.set_thumbnail(url=userThumbnail)
        embed.set_author(name=f"{user.username} {'(' + user.nickname + ')' if user.nickname != user.username else ''}", url=f"https://www.roblox.com/users/{user.id}/profile", icon_url=userHeadshot)
        if user.banned or user.id == 1: veriftype, previousUsernames = None, []
        lastOnlineFormatted, joinedTimestamp = await asyncio.gather(gUtils.fancy_time(user.online), gUtils.fancy_time(user.joined))
        embed.colour = 0x00ff00
        embed.url = f"https://www.roblox.com/users/{user.id}/profile" if not user.banned else None
        embed.add_field(name="User ID:", value=f"`{user.id}`", inline=True)
        embed.add_field(name="Account Status:", value="`Terminated`" if user.banned else "`Okay`" if not user.banned else "`N/A (*Nil*)`", inline=True)
        if previousUsernames:
            formattedUsernames = ', '.join([f"`{username}`" for username in previousUsernames[:10]]) + (f", and {len(previousUsernames) - 10} more" if len(previousUsernames) > 10 else '')
            embed.add_field(name=f"Previous Usernames ({len(previousUsernames)}):", value=formattedUsernames, inline=False)
        if veriftype is not None: embed.add_field(name="Verified Email:", value="`N/A (*Nil*)`" if veriftype == -1 else "`N/A (*-1*)`" if veriftype == 0 else "`Verified, hat present`" if veriftype == 1 else "`Verified, sign present`" if veriftype == 2 else "`Unverified`" if veriftype == 3 else "`Verified, sign & hat present`" if veriftype == 4 else "`N/A`", inline=True)
        if user.description: embed.add_field(name="Description:", value=f"```{user.description.replace('```', '')}```", inline=False)
        embed.add_field(name="Joined:", value=f"{joinedTimestamp}", inline=True)
        embed.add_field(name="Last Online:", value=f"{lastOnlineFormatted}", inline=True)
        embed.add_field(name="Groups:", value=f"`{len(groups['data'])}`", inline=True)
        embed.add_field(name="Friends:", value=f"`{user.friends}`", inline=True)
        embed.add_field(name="Followers:", value=f"`{user.followers}`", inline=True)
        embed.add_field(name="Following:", value=f"`{user.following}`", inline=True)
        privateInventory, isEdited, nlChar = None, False, "\n"
        if previousUsernames: whoData = "id, username, nickname, verified, rowhois_staff, account_status, joined, last_online, verified_email, groups, friends, followers, following, previous_usernames, description\n" + ''.join([f"{user.id}, {user.username}, {user.nickname}, {user.verified}, {user.id in staffIds}, {'Terminated' if user.banned else 'Okay' if not user.banned else 'None'}, {user.joined}, {user.online}, {'None' if veriftype == -1 else 'None' if veriftype == 0 else 'Hat' if veriftype == 1 else 'Sign' if veriftype == 2 else 'Unverified' if veriftype == 3 else 'Both' if veriftype == 4 else 'None'}, {len(groups['data'])}, {user.friends}, {user.followers}, {user.following}, {name}, {user.description.replace(',', '').replace(nlChar, '     ')  if user.description else 'None'}{nlChar}" for name in previousUsernames])
        else: whoData = f"id, username, nickname, verified, rowhois_staff, account_status, joined, last_online, verified_email, groups, friends, followers, following, previous_usernames, description\n{user.id}, {user.username}, {user.nickname}, {user.verified}, {user.id in staffIds}, {'Terminated' if user.banned else 'Okay' if not user.banned else 'None'}, {user.joined}, {user.online}, {'None' if veriftype == -1 else 'None' if veriftype == 0 else 'Hat' if veriftype == 1 else 'Sign' if veriftype == 2 else 'Unverified' if veriftype == 3 else 'Both' if veriftype == 4 else 'None'}, {len(groups['data'])}, {user.friends}, {user.followers}, {user.following}, None, {user.description.replace(',', '').replace(nlChar, '     ') if user.description else 'None'}\n"
        whoData = (discord.File(io.BytesIO(whoData.encode()), filename=f"rowhois-rowhois-{user.id}.csv"))
        if not user.banned and user.id != 1:
            isEdited, iniTS = True, time.time()
            if download: await interaction.followup.send(embed=embed, file=whoData)
            else: await interaction.followup.send(embed=embed)
            try: privateInventory, totalRap, totalValue, limiteds = await RoModules.get_limiteds(user.id, roliData, shard) # VERY slow when user has a lot of limiteds
            except Exception: totalRap, totalValue = "Failed to fetch", "Failed to fetch"
            embed.add_field(name="Privated Inventory:", value=f"`{privateInventory if privateInventory is not None else 'Failed to fetch'}`", inline=True)
            if not privateInventory:
                embed.add_field(name="Total RAP:", value=f"`{totalRap}`", inline=True)
                embed.add_field(name="Total Value:", value=f"`{totalValue}`", inline=True)
        if download and not isEdited: await interaction.followup.send(embed=embed, file=whoData)
        elif isEdited:
            time_diff = time.time() - iniTS
            if time_diff < 0.75: await asyncio.sleep(0.75 - time_diff) # 0.75 to prevent ratelimiting by Discord when inv takes no time to calc
            await interaction.edit_original_response(embed=embed)
        else: await interaction.followup.send(embed=embed)
    except Exception as e: await handle_error(e, interaction, "whois", shard, "User")
@client.tree.command()
async def ownsitem(interaction: discord.Interaction, user: str, item: int, download: bool = False):
    """Check if a player owns a specific item"""
    if await check_cooldown(interaction, "medium"): return
    embed = discord.Embed(color=0xFF0000)
    if not (await validate_user(interaction, embed, userid, requires_entitlement=download)): return
    shard = await gUtils.shard_metrics(interaction)
    try:
        try:
            user = await RoModules.handle_usertype(user, shard)
            if not (await validate_user(interaction, embed, user.id)): return
        except Exception as e:
            if await handle_error(e, interaction, "ownsitem", shard, "User"): return
        data = await RoModules.owns_item(user.id, item, shard)
        if data[0] is None:
            if data[2] == "The specified user does not exist!": embed.description = "User does not exist or has been banned."
            elif data[2] == "The specified Asset does not exist!": embed.description = "Item does not exist."
            else: embed.description = f"Failed to retrieve data: {data[2]}"
            await interaction.followup.send(embed=embed)
            return
        if data[0]:
            embed.set_thumbnail(url=await RoModules.get_item_thumbnail(item, "420x420", shard))
            embed.colour = 0x00FF00
            embed.title = f"{user.username} owns {data[1]} {data[2]}{'s' if data[1] > 1 else ''}!"
            displayUAIDs = data[3][:100]
            embed.description = "**UAIDs:**\n" + ', '.join([f"`{uaid}`" for uaid in map(str, displayUAIDs)])
            remainingCount = max(0, data[1] - 100)
            if remainingCount > 0: embed.description += f", and {remainingCount} more."
        else: embed.description = f"{user.username} doesn't own this item!"
        if download:
            if data[0]: csv = "username, id, item, owned, uaid\n" + "\n".join([f"{user.username}, {user.id}, {item}, {bool(data[0])}, {uaid}" for uaid in data[3]])
            else: csv = f"username, id, item, owned, uaid\n{user.username}, {user.id}, {item}, {bool(data[0])}, None"
            await interaction.response.send_message(embed=embed, file=discord.File(io.BytesIO(csv.encode()), filename=f"rowhois-ownsitem-{user.id}.csv"))
        else: await interaction.response.send_message(embed=embed)
    except Exception as e: await handle_error(e, interaction, "ownsitem", shard, "Item")

@client.tree.command()
async def ownsbadge(interaction: discord.Interaction, user: str, badge: int, download: bool = False):
    """Check if a player owns a specified badge and return it's award date"""
    if await check_cooldown(interaction, "low"): return
    embed = discord.Embed(color=0xFF0000)
    if not (await validate_user(interaction, embed, userid, requires_entitlement=download)): return
    shard = await gUtils.shard_metrics(interaction)
    try:
        user = await RoModules.handle_usertype(user, shard)
        if not (await validate_user(interaction, embed, user.id)): return
        ownsBadge = await RoModules.owns_badge(user.id, badge, shard)
        if ownsBadge[0]:
            embed.set_thumbnail(url=await RoModules.get_badge_thumbnail(badge, shard))
            embed.colour = 0x00FF00
            embed.title = f"{user.username} owns this badge!"
            embed.description = f"Badge was awarded {await gUtils.fancy_time(ownsBadge[1])}"
        else: embed.description = f"{user.username} doesn't own the specified badge!"
        if download:
            if ownsBadge[0]: csv = "username, id, badge, owned, awarded\n" + "\n".join([f"{user.username}, {user.id}, {badge}, {ownsBadge[0]}, {ownsBadge[1]}"])
            else: csv = f"username, id, badge, owned, awarded\n{user.username}, {user.id}, {badge}, {ownsBadge[0]}, None"
            await interaction.response.send_message(embed=embed, file=discord.File(io.BytesIO(csv.encode()), filename=f"rowhois-ownsbadge-{user.id}.csv"))
        else: await interaction.response.send_message(embed=embed)
    except Exception as e: await handle_error(e, interaction, "ownsbadge", shard, "Badge")

@client.tree.command()
async def limited(interaction: discord.Interaction, limited: str, download: bool = False):
    """Returns a limited ID, the rap, and value of a specified limited"""
    if await check_cooldown(interaction, "medium"): return
    embed = discord.Embed(color=0xFF0000)
    if not (await validate_user(interaction, embed, userid, requires_entitlement=download)): return
    shard = await gUtils.shard_metrics(interaction)
    try:
        limited_id, name, acronym, rap, value, demand, trend, projected, rare = await RoModules.get_rolidata_from_item(roliData, limited)
        embed.set_thumbnail(url=await RoModules.get_item_thumbnail(limited_id, "420x420", shard))
        embed.colour = 0x00FF00
        embed.title = f"{name} ({acronym})" if acronym != "" else f"{name}"
        embed.url = f"https://www.roblox.com/catalog/{limited_id}/"
        embed.add_field(name="Limited ID:", value=f"`{limited_id}`", inline=True)
        embed.add_field(name="RAP:", value=f"`{rap}`", inline=True)
        embed.add_field(name="Value:", value=f"`{value}`", inline=True)
        embed.add_field(name="Demand:", value=f"`{demand}`", inline=True)
        embed.add_field(name="Trend:", value=f"`{trend}`", inline=True)
        embed.add_field(name="Projected:", value=f"`{projected}`", inline=True)
        embed.add_field(name="Rare:", value=f"`{rare}`", inline=True)
        if download:
            csv = "id, name, acronym, rap, value, demand, trend, projected, rare\n" + "\n".join([f"{limited_id}, {name.replace(',', '')}, {acronym.replace(',', '') if acronym else 'None'}, {rap}, {value}, {demand}, {trend}, {projected}, {rare}"])
            await interaction.response.send_message(embed=embed, file=discord.File(io.BytesIO(csv.encode()), filename=f"rowhois-limited-{limited_id if limited_id is not None else 'search'}.csv"))
        else: await interaction.response.send_message(embed=embed)
    except Exception as e: await handle_error(e, interaction, "limited", shard, "Limited")

@client.tree.command()
async def isfriendswith(interaction: discord.Interaction, user1: str, user2: str):
    """Check whether a user is friended to another user"""
    # Technically we only have to check through one player as it's a mutual relationship
    if await check_cooldown(interaction, "low"): return
    embed = discord.Embed(color=0xFF0000)
    if not (await validate_user(interaction, embed)): return
    shard = await gUtils.shard_metrics(interaction)
    try:
        user1 = await RoModules.handle_usertype(user1, shard)
        if not (await validate_user(interaction, embed, user1.id)): return
        if user2.isdigit(): user2 = int(user2)
        userfriends = await RoModules.get_friends(user1.id, shard)
        friended = False
        for friends in userfriends['data']:
            friendName = str(friends['name']).lower() if not str(friends['name']).isdigit() else str(friends['name'])
            secondUser = str(user2).lower() if not str(user2).isdigit() else user2
            if friends['id'] == secondUser or friendName == secondUser:
                if friends['id'] in optOut:
                    embed.description = "This user's friend has requested to opt-out of the RoWhoIs search."
                    await log_collector.warn(f"Opt-out user {friends['id']} was called by {interaction.user.id} and denied!")
                    await interaction.followup.send(embed=embed)
                    return
                friend_name, friended = friends['name'], True
                break
            else: friended = False
        if friended:
            embed.colour = 0x00FF00
            embed.description = f"{user1.username} is friends with {friend_name}!"
            await interaction.followup.send(embed=embed)
            return
        else:
            embed.description = f"{user1.username} does not have this user friended."
            await interaction.response.send_message(embed=embed)
    except Exception as e: await handle_error(e, interaction, "isfriendswith", shard, "User")

@client.tree.command()
async def isingroup(interaction: discord.Interaction, user: str, group: int):
    """Check whether a user is in a group or not"""
    if await check_cooldown(interaction, "low"): return
    embed = discord.Embed(color=0xFF0000)
    if not (await validate_user(interaction, embed)): return
    shard = await gUtils.shard_metrics(interaction)
    try:
        try:
            user = await RoModules.handle_usertype(user, shard)
        except Exception as e:
            if await handle_error(e, interaction, "isingroup", shard, "User"): return
        if not (await validate_user(interaction, embed, user.id)): return
        usergroups = await RoModules.get_groups(user.id, shard)
        ingroup = False
        for groups in usergroups['data']:
            if groups['group']['id'] == group:
                ingroup = True
                groupname = groups['group']['name']
                grouprole = groups['role']['name']
                groupid = groups['group']['id']
                break
            else: ingroup = False
        if ingroup:
            embed.set_thumbnail(url=await RoModules.get_group_emblem(groupid, "420x420", shard))
            embed.colour = 0x00FF00
            embed.title = f"{user.username} is in group `{groupname}`!"
            embed.description = f"Role: `{grouprole}`"
        else: embed.description = f"{user.username} is not in this group."
        await interaction.response.send_message(embed=embed)
    except Exception as e: await handle_error(e, interaction, "isingroup", shard, "Group")

@client.tree.command()
async def clothingtexture(interaction: discord.Interaction, clothing_id: int):
    """Get the texture file of a clothing item"""
    if await check_cooldown(interaction, "extreme"): return
    embed = discord.Embed(color=0xFF0000)
    if not (await validate_user(interaction, embed)): return
    await interaction.response.defer(ephemeral=False)
    if clothing_id in assetBlocklist:
        embed.description = "The asset creator has requested for this asset to be removed from RoWhoIs."
        await interaction.followup.send(embed=embed)
        return
    shard = await gUtils.shard_metrics(interaction)
    try:
        try: clothing_id = await RoModules.fetch_asset(clothing_id, shard)
        except ErrorDict.AssetNotAvailable:
            embed.description = "Cannot fetch moderated assets."
            await interaction.followup.send(embed=embed)
            return
        uploaded_image = discord.File(f'cache/clothing/{clothing_id}.png', filename=f"rowhois-{clothing_id}.png")
        await interaction.followup.send("", file=uploaded_image)
    except Exception as e: await handle_error(e, interaction, "getclothingtexture", shard, "Clothing ID")

@client.tree.command()
async def itemdetails(interaction: discord.Interaction, item: int, download: bool = False):
    """Get advanced details about a catalog item"""
    if await check_cooldown(interaction, "high"): return
    embed = discord.Embed(color=0xFF0000)
    if not (await validate_user(interaction, embed, requires_entitlement=download)): return
    shard = await gUtils.shard_metrics(interaction)
    try:
        data = await RoModules.get_item(item, shard)
        embed.url = f"https://www.roblox.com/catalog/{item}"
        if data["CollectibleItemId"] is not None: isCollectible = True
        else: isCollectible = False
        embed.title = f"{emojiTable.get('limited') if data['IsLimited'] else emojiTable.get('limitedu') if data['IsLimitedUnique'] else emojiTable.get('collectible') if isCollectible else ''} {data['Name']}"
        embed.add_field(name="Creator:", value=f"`{data['Creator']['Name']}` (`{data['Creator']['CreatorTargetId']}`) {emojiTable.get('staff') if userid in staffIds else emojiTable.get('verified') if data['Creator']['HasVerifiedBadge'] else ''}")
        if data['Description'] != "": embed.add_field(name="Description:", value=f"```{data['Description'].replace('```', '')}```", inline=False)
        embed.add_field(name="Created:", value=f"{(await gUtils.fancy_time(data['Created']))}", inline=True)
        embed.add_field(name="Updated:", value=f"{(await gUtils.fancy_time(data['Updated']))}", inline=True)
        if isCollectible:
            embed.add_field(name="Quantity:", value=f"`{data['CollectiblesItemDetails']['TotalQuantity']}`", inline=True)
            if data['CollectiblesItemDetails']['CollectibleLowestResalePrice'] is not None and data['IsForSale']: embed.add_field(name="Lowest Price:", value=f"{emojiTable.get('robux')} `{data['CollectiblesItemDetails']['CollectibleLowestResalePrice']}`", inline=True)
            elif data["IsForSale"]: embed.add_field(name="Lowest Price:", value=f"`No resellers`", inline=True)
        if data["IsForSale"]:
            if data["Remaining"] is not None and data["Remaining"] != 0: embed.add_field(name="Remaining:", value=f"`{data['Remaining']}`", inline=True)
            if not (data["IsLimited"] or data["Remaining"] == 0 or isCollectible): embed.add_field(name="Price:", value=f"{emojiTable.get('robux')} `{data['PriceInRobux']}`", inline=True)
        embed.set_thumbnail(url=await RoModules.get_item_thumbnail(item, "420x420", shard))
        embed.colour = 0x00FF00
        if download:
            nlChar = "\n"
            csv = "id, name, creator_name, creator_id, verified, created, updated, is_limited, is_limited_unique, is_collectible, quantity, lowest_price, remaining, price, description\n" + f"{item}, {data['Name'].replace(',', '')}, {data['Creator']['Name']}, {data['Creator']['CreatorTargetId']}, {data['Creator']['HasVerifiedBadge']}, {data['Created']}, {data['Updated']}, {data['IsLimited']}, {data['IsLimitedUnique']}, {isCollectible}, {data['CollectiblesItemDetails']['TotalQuantity'] if isCollectible else 'None'}, {data['CollectiblesItemDetails']['CollectibleLowestResalePrice'] if isCollectible else 'None'}, {data['Remaining'] if data['Remaining'] is not None else 'None'}, {data['PriceInRobux'] if not (data['IsLimited'] or data['Remaining'] == 0 or isCollectible) else 'None'}, {data['Description'].replace(',', '').replace(nlChar, '    ') if data['Description'] != '' else 'None'}"
            await interaction.response.send_message(embed=embed, file=discord.File(io.BytesIO(csv.encode()), filename=f"rowhois-itemdetails-{item}.csv"))
        else: await interaction.response.send_message(embed=embed)
    except Exception as e: await handle_error(e, interaction, "getitemdetails", shard, "Item")

@client.tree.command()
async def membership(interaction: discord.Interaction, user: str):
    """Checks whether a user has premium and if they had Builders Club"""
    if await check_cooldown(interaction, "high"): return
    embed = discord.Embed(color=0xFF0000)
    shard = await gUtils.shard_metrics(interaction)
    if not (await validate_user(interaction, embed)): return
    try:
        user = await RoModules.handle_usertype(user, shard)
        if not (await validate_user(interaction, embed, user.id)): return
        data = await RoModules.get_membership(user.id, shard)
        if all(not data[i] for i in range(1, 4)): noTiers = True
        else: noTiers = False
        newline = '\n'
        embed.title = f"{user.username}'s memberships:"
        embed.description = f"{(emojiTable.get('premium') + ' `Premium`' + newline) if data[0] else ''}{(emojiTable.get('bc') + ' `Builders Club`' + newline) if data[1] else ''}{(emojiTable.get('tbc') + '`Turbo Builders Club`' + newline) if data[2] else ''}{(emojiTable.get('obc') + ' `Outrageous Builders Club`' + newline) if data[3] else ''}{(str(user.username) + ' has no memberships.') if noTiers and not data[0] else ''}"
        embed.colour = 0x00FF00
        await interaction.response.send_message(embed=embed)
    except Exception as e: await handle_error(e, interaction, "getmembership", shard, "User")

@client.tree.command()
async def group(interaction: discord.Interaction, group: int, download: bool = False):
    """Get detailed group information from a Group ID"""
    if await check_cooldown(interaction, "medium"): return
    embed = discord.Embed(color=0xFF0000)
    if not (await validate_user(interaction, embed, requires_entitlement=download)): return
    shard = await gUtils.shard_metrics(interaction)
    try:
        groupInfo = await RoModules.get_group(group, shard)
        groupThumbnail = await RoModules.get_group_emblem(group, "420x420", shard)
        if groupThumbnail: embed.set_thumbnail(url=groupThumbnail)
        embed.title = f"{groupInfo[0]}{(' ' + emojiTable.get('verified')) if groupInfo[3] else ''}"
        embed.add_field(name="Group ID:", value=f"`{group}`")
        embed.add_field(name="Status:", value=f"`{'Locked' if groupInfo[8] else 'Okay'}`", inline=True)
        embed.add_field(name="Created:", value=f"{await gUtils.fancy_time(groupInfo[2])}", inline=True)
        if all(groupInfo[4][:1]): embed.add_field(name="Owner:", value=f"`{groupInfo[4][0]}` (`{groupInfo[4][1]}`) {(' ' + emojiTable.get('verified')) if groupInfo[4][2] else ''}", inline=True)
        else: embed.add_field(name="Owner:", value=f"Nobody!", inline=True)
        embed.add_field(name="Members:", value=f"`{groupInfo[6]}`", inline=True)
        embed.add_field(name="Joinable:", value=f"`{'False' if groupInfo[8] else 'True' if groupInfo[7] else 'False'}`", inline=True)
        if groupInfo[5] is not None:
            if groupInfo[5][0] != "": embed.add_field(name="Shout:", value=f"`{groupInfo[5][0]}` -- `{groupInfo[5][1]}` (`{groupInfo[5][2]}`) {('' + emojiTable.get('verified')) if groupInfo[5][3] else ''}", inline=False)
        if groupInfo[1] != "": embed.add_field(name="Group Description:", value=f"```{groupInfo[1].replace('```', '')}```", inline=False)
        embed.colour = 0x00FF00
        if download:
            nlChar = "\n"
            csv = "id, name, owner, created, members, joinable, locked, shout, shout_author, shout_author_id, shout_verified, description\n" + f"{group}, {groupInfo[0]}, {groupInfo[4][0] if groupInfo[4] is not None else 'None'}, {groupInfo[2]}, {groupInfo[6]}, {groupInfo[7]}, {groupInfo[8]}, {groupInfo[5][0] if groupInfo[5] is not None else 'None'}, {groupInfo[5][1] if groupInfo[5] is not None else 'None'}, {groupInfo[5][2] if groupInfo[5] is not None else 'None'}, {groupInfo[5][3] if groupInfo[5] is not None else 'None'}, {groupInfo[1].replace(',', '').replace(nlChar, '     ') if groupInfo[1] else 'None'}"
            await interaction.response.send_message(embed=embed, file=discord.File(io.BytesIO(csv.encode()), filename=f"rowhois-group-{group}.csv"))
        else: await interaction.response.send_message(embed=embed)
    except Exception as e: await handle_error(e, interaction, "group", shard, "Group")

@client.tree.command()
async def checkusername(interaction: discord.Interaction, username: str, download: bool = False):
    """Check if a username is available"""
    if await check_cooldown(interaction, "medium"): return
    embed = discord.Embed(color=0xFF0000)
    if not (await validate_user(interaction, embed, requires_entitlement=download)): return
    shard = await gUtils.shard_metrics(interaction)
    try:
        usernameInfo = await RoModules.validate_username(username, shard)
        if usernameInfo[0] == 0:
            embed.colour = 0x00FF00
            embed.description = "Username is available!"
        elif usernameInfo[0] == 1: embed.description = "Username is taken."
        else: embed.description = f"Username not available.\n**Reason:** {usernameInfo[1]}"
        if download:
            csv = "username, code\n" + "\n".join([f"{username.replace(',', '')}, {usernameInfo[0]}"])
            await interaction.response.send_message(embed=embed, file=discord.File(io.BytesIO(csv.encode()), filename=f"rowhois-checkusername.csv"))
        else: await interaction.response.send_message(embed=embed)
    except Exception as e: await handle_error(e, interaction, "username", shard, "Username")

@client.tree.command()
async def robloxbadges(interaction: discord.Interaction, user: str):
    """Check what Roblox badges a player has"""
    if await check_cooldown(interaction, "high"): return
    embed = discord.Embed(color=0xFF0000)
    if not (await validate_user(interaction, embed)): return
    shard = await gUtils.shard_metrics(interaction)
    try:
        user = await RoModules.handle_usertype(user, shard)
        if not (await validate_user(interaction, embed, user.id)): return
        badges = await RoModules.roblox_badges(user.id, shard)
        if len(badges[0]) <= 0:
            embed.description = "This user has no Roblox badges."
            await interaction.followup.send(embed=embed)
            return
        descriptor = ""
        for badge in badges[0]:
            badge_name = badges[1].get(badge)
            if badge_name: descriptor += f"{emojiTable.get(str(badge_name).lower())} `{badge_name}`\n"
        if descriptor == "":  descriptor = "This user has no Roblox badges."
        embed.set_thumbnail(url=await RoModules.get_player_bust(user.id, "420x420", shard))
        embed.colour = 0x00FF00
        embed.title = f"{user.username}'s Roblox Badges:"
        embed.description = descriptor
        await interaction.response.send_message(embed=embed)
    except Exception as e: await handle_error(e, interaction, "robloxbadges", shard, "User")

@client.tree.command()
async def groupclothing(interaction: discord.Interaction, group: int, page: int = 1):
    """Retrieves bulk clothing texture files from a group"""
    if await check_cooldown(interaction, "extreme"): return
    embed = discord.Embed(color=0xFF0000)
    if not (await validate_user(interaction, embed, requires_entitlement=True, kind_upsell=False)): return
    await interaction.response.defer(ephemeral=False)
    shard = await gUtils.shard_metrics(interaction)
    try:
        try:
            groupAssets, pagination = await RoModules.get_creator_assets(group, "Group", page, shard)
            if pagination != page:
                embed.description = "Invalid page number."
                await interaction.followup.send(embed=embed)
                return
            if not groupAssets:
                embed.description = "This group has no clothing assets."
                await interaction.followup.send(embed=embed)
                return
            tasks, files = [], []
            for asset in groupAssets: tasks.append(gUtils.safe_wrapper(RoModules.fetch_asset, asset, shard))
            try: clothing = await asyncio.gather(*tasks)
            except Exception as e:
                if await handle_error(e, interaction, "groupclothing", shard, "Group ID"): return
            for asset in clothing:
                if isinstance(asset, int) and asset not in assetBlocklist: files.append(discord.File(f'cache/clothing/{asset}.png', filename=f"rowhois-groupclothing-{asset}.png"))
            if not files:
                embed.description = "No clothing assets were found."
                await interaction.followup.send(embed=embed)
                return
            await interaction.followup.send("", files=files)
        except Exception as e:
            if await handle_error(e, interaction, "groupclothing", shard, "Group ID"): return
    except Exception as e: await handle_error(e, interaction, "groupclothing", shard, "Group ID")

@client.tree.command()
async def userclothing(interaction: discord.Interaction, user: str, page: int = 1):
    """Retrieves bulk clothing texture files from a user"""
    if await check_cooldown(interaction, "extreme"): return
    embed = discord.Embed(color=0xFF0000)
    if not (await validate_user(interaction, embed, requires_entitlement=True, kind_upsell=False)): return
    await interaction.response.defer(ephemeral=False)
    shard = await gUtils.shard_metrics(interaction)
    try:
        user = await RoModules.handle_usertype(user, shard)
    except Exception as e:
        if await handle_error(e, interaction, "userclothing", shard, "User"): return
    try:
        userAssets, pagination = await RoModules.get_creator_assets(user.id, "User", page, shard)
        if pagination != page or page < 1:
            embed.description = "Invalid page number."
            await interaction.followup.send(embed=embed)
            return
        if not userAssets:
            embed.description = "This user has no clothing assets."
            await interaction.followup.send(embed=embed)
            return
        tasks, files = [], []
        for asset in userAssets: tasks.append(gUtils.safe_wrapper(RoModules.fetch_asset, asset, shard))
        try: clothing = await asyncio.gather(*tasks)
        except Exception as e:
            if await handle_error(e, interaction, "userclothing", shard, "User"): return
        for asset in clothing:
            if isinstance(asset, int) and asset not in assetBlocklist: files.append(discord.File(f'cache/clothing/{asset}.png', filename=f"rowhois-userclothing-{asset}.png"))
        if not files:
            embed.description = "No clothing assets were found."
            await interaction.followup.send(embed=embed)
            return
        await interaction.followup.send("", files=files)
    except Exception as e: await handle_error(e, interaction, "userclothing", shard, "User")

@client.tree.command()
async def asset(interaction: discord.Interaction, asset: int, filetype: Literal["rbxm", "png", "obj", "mesh", "rbxmx", "rbxl", "rbxlx", "mp4"], version: int = None):
    """Retrieve asset files"""
    if await check_cooldown(interaction, "extreme"): return
    embed = discord.Embed(color=0xFF0000)
    if not (await validate_user(interaction, embed)): return
    await interaction.response.defer(ephemeral=False)
    shard = await gUtils.shard_metrics(interaction)
    try:
        if asset in assetBlocklist:
            embed.description = "The asset creator has requested for this asset to be removed from RoWhoIs."
            await interaction.followup.send(embed=embed)
            return
        try: asset = await RoModules.fetch_asset(asset, shard, location="asset", version=version, filetype=filetype if filetype is not None else 'rbxm')
        except ErrorDict.AssetNotAvailable:
            embed.description = "Cannot fetch moderated assets."
            await interaction.followup.send(embed=embed)
            return
        if not asset:
            embed.description = "This asset does not exist."
            await interaction.followup.send(embed=embed)
            return
        uploaded_file = discord.File(f"cache/asset/{str(asset) + '-' + str(version) if version is not None else str(asset)}.{filetype if filetype is not None else 'rbxm'}", filename=f"rowhois-{str(asset) + '-' + str(version) if version is not None else str(asset)}.{filetype if filetype is not None else ''}")
        await interaction.followup.send("", file=uploaded_file)
    except Exception as e: await handle_error(e, interaction, "asset", shard, "Asset ID or Version")
