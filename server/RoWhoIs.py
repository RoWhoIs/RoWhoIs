from server import Roquest, RoModules, app_commands, globals
from utils import logger, ErrorDict, gUtils, typedefs
import asyncio, hikari, io, aiohttp, inspect, time, json, aioconsole
from pathlib import Path
from typing import Any, Optional, Literal


def load_config():
    global staffIds, optOut, userBlocklist, emojiTable, assetBlocklist, whoIsDonors, productionMode, botToken
    with open('config.json', 'r') as configfile:
        config = json.load(configfile)
        configfile.close()
    productionMode, staffIds, optOut, userBlocklist, assetBlocklist, whoIsDonors = config['RoWhoIs']['production_mode'], config['RoWhoIs']['admin_ids'], config['RoWhoIs']['opt_out'], config['RoWhoIs']['banned_users'], config['RoWhoIs']['banned_assets'], config['RoWhoIs']['donors']
    botToken = {"topgg": config['Authentication']['topgg'], "dbl": config['Authentication']['dbl']}
    emojiTable = {key: config['Emojis'][key] for key in config['Emojis']}
    app_commands.init(productionmode=productionMode, optout=optOut, userblocklist=userBlocklist, emojitable=emojiTable)
    return config

def run(version: str) -> bool:
    """Runs the server"""
    try:
        global shortHash, uptime
        shortHash = version
        config_d = load_config()
        loop.create_task(input_listener())
        uptime = time.time()
        globals.init()
        client.run(close_loop=False, shard_count=config_d['RoWhoIs']['shards'])
        return True
    except KeyError: raise ErrorDict.MissingRequiredConfigs
    except asyncio.exceptions.CancelledError: return True
    except KeyboardInterrupt: return True

class RoWhoIs(hikari.GatewayBot):
    def __init__(self, *, intents: hikari.Intents):
        config = load_config()
        super().__init__(intents=intents, token=config['Authentication']['production' if productionMode else 'testing'], banner=None)

client = RoWhoIs(intents=hikari.Intents.ALL_UNPRIVILEGED)
shardAnalytics = gUtils.ShardAnalytics(0, False)
log_collector = logger.AsyncLogCollector("logs/main.log")
loop = asyncio.get_event_loop()

@client.listen(hikari.InteractionCreateEvent)
async def wrapped_on_interaction_create(event: hikari.InteractionCreateEvent): await app_commands.interaction_runner(event)

@client.listen(hikari.StartedEvent)
async def start(event: hikari.StartedEvent):
    await log_collector.info(f"Initialized! Syncing global command tree", initiator="RoWhoIs.start")
    await app_commands.sync_app_commands(client)
@client.listen(hikari.ShardConnectedEvent)
async def connect(event: hikari.ShardConnectedEvent):
    await log_collector.info(f"Shard {event.shard.id} connected to gateway", initiator="RoWhoIs.connect")
    await client.update_presence(activity=hikari.Activity(type=hikari.ActivityType.WATCHING, name="over Robloxia"), status=hikari.Status.ONLINE)


async def input_listener() -> None:
    """Allows for in-terminal commands while the server is running"""
    while True:
        try:
            command = await aioconsole.ainput("")
            if command == "help": print("Commands: down, up, shards, servers, users, cache, cflush, lflush, flush, reload")
            if command == "down": raise KeyboardInterrupt
            if command == "up": await log_collector.info(f"Uptime: {await gUtils.ret_uptime(uptime)}", initiator="RoWhoIs.input_listener")
            if command == "shards": await log_collector.info(f"Shards: {client.shard_count}", initiator="RoWhoIs.input_listener")
            if command == "servers": await log_collector.info(f"Servers: {len(client.cache.get_guilds_view())}", initiator="RoWhoIs.input_listener")
            if command == "users": await log_collector.info(f"Users: {sum(client.cache.get_guild(guild_id).member_count if client.cache.get_guild(guild_id).member_count is not None else 0 for guild_id in client.cache.get_guilds_view())}", initiator="RoWhoIs.input_listener")
            if command == "cache": await log_collector.info(f"Cache Size: {round(sum(f.stat().st_size for f in Path('cache/').glob('**/*') if f.is_file()) / 1048576, 1)} MB", initiator="RoWhoIs.input_listener")
            if command == "cflush":
                if Path("cache/cursors.json").is_file(): Path("cache/cursors.json").unlink()
                await log_collector.info("Cursor Cache flushed", initiator="RoWhoIs.input_listener")
            if command == "lflush":
                for file in Path("logs/").glob("**/*"):
                    if file.is_file() and file.name != "main.log": file.unlink()
                await log_collector.info("Logs flushed", initiator="RoWhoIs.input_listener")
            if command == "flush":
                for file in Path("cache/").glob("**/*"):
                    if file.is_file(): file.unlink()
                await log_collector.info("Cache flushed", initiator="RoWhoIs.input_listener")
            if command == "reload":
                load_config()
                await log_collector.info("Configuration reloaded", initiator="RoWhoIs.input_listener")
        except Exception as e:
            if not isinstance(e, RuntimeError): await log_collector.error(f"Error in input listener: {type(e)}, {e}", initiator="RoWhoIs.input_listener") # RTE happens when invalid config, usually
            else: return False

@client.listen(hikari.GuildJoinEvent)
async def guild_join(event: hikari.GuildJoinEvent):
    await log_collector.info(f"RoWhoIs has joined a new server. Total servers: {len(client.cache.get_guilds_view())}. {'Updating registries...' if productionMode else ''}", initiator="RoWhoIs.guild_join")
    if productionMode:
        try:
            async with aiohttp.ClientSession() as session:
                if botToken.get("topgg") != "":
                    async with session.post(f"https://top.gg/api/bots/{client.get_me().id}/stats", headers={"Authorization": botToken.get("topgg")}, json={"server_count": len(client.cache.get_guilds_view()), "shard_count": client.shard_count}): pass
                if botToken.get("dbl") != "":
                    async with session.post(f"https://discordbotlist.com/api/v1/bots/{client.get_me().id}/stats", headers={"Authorization": botToken.get("dbl")}, json={"guilds": len(client.cache.get_guilds_view())}): pass
        except Exception as e: await log_collector.error(f"Failed to update registries. {e}", initiator="RoWhoIs.guild_join")

@app_commands.Command(context="Command", intensity="low", requires_connection=False)
async def help(interaction: hikari.CommandInteraction):
    """List all of the commands RoWhoIs supports & what they do"""
    embed = hikari.Embed(title="RoWhoIs Commands", color=3451360)
    embed.add_field(name="whois", value="Get detailed profile information from a User ID/Username", inline=True)
    embed.add_field(name="clothingtexture", value="Retrieves the texture file for a 2D clothing asset", inline=True)
    embed.add_field(name="userid", value="Get a User ID based off a username", inline=True)
    embed.add_field(name="username", value="Get a username based off a User ID", inline=True)
    embed.add_field(name="ownsitem", value="Retrieve whether a user owns an item or not. Works with players who have a private inventory", inline=True)
    embed.add_field(name="ownsbadge", value="Retrieve whether a user owns a badge or not. Works with players who have a private inventory", inline=True)
    embed.add_field(name="isfriendswith", value="Check if two players are friended", inline=True)
    embed.add_field(name="game", value="Get detailed game information from a Game ID", inline=True)
    embed.add_field(name="group", value="Get detailed group information from a Group ID", inline=True)
    embed.add_field(name="groupclothing " + f"{emojiTable.get('subscription')}", value="Retrieves bulk clothing textures from a group", inline=True)
    embed.add_field(name="userclothing " + f"{emojiTable.get('subscription')}", value="Retrieves bulk clothing textures from a user", inline=True)
    embed.add_field(name="isingroup", value="Check if a player is in the specified group", inline=True)
    embed.add_field(name="limited", value="Returns a limited ID, the rap, and value of the specified limited", inline=True)
    embed.add_field(name="itemdetails", value="Returns details about a catalog item", inline=True)
    embed.add_field(name="membership", value="Check if a player has Premium or has had Builders Club", inline=True)
    embed.add_field(name="checkusername", value="Check if a username is available", inline=True)
    embed.add_field(name="asset", value="Fetches an asset file from an asset ID. Not recommended for clothing textures", inline=True)
    embed.add_field(name="about", value="Shows a bit about RoWhoIs and advanced statistics", inline=True)
    embed.set_footer(text="You have access to RoWhoIs+ features" if not productionMode or interaction.entitlements else "Get RoWhoIs+ to use + commands")
    await interaction.create_initial_response(response_type=hikari.ResponseType.MESSAGE_CREATE, embed=embed)

@app_commands.Command(context="Command", intensity="low", requires_connection=False)
async def about(interaction: hikari.CommandInteraction):
    """Shows detailed information about RoWhoIs"""
    embed = hikari.Embed(color=3451360)
    shard = await gUtils.shard_metrics(interaction)
    embed.title = "About RoWhoIs"
    embed.set_thumbnail(hikari.files.URL("https://rowhois.com/rwi-pfp-anim.gif"))
    embed.set_author(name="Made with <3 by aut.m (249681221066424321)", icon=hikari.files.URL("https://rowhois.com/profile_picture.jpeg"))
    embed.description = "RoWhoIs provides advanced information about Roblox users, groups, and assets. It's designed to be fast, reliable, and easy to use."
    embed.add_field(name="Version", value=f"`{shortHash}`", inline=True)
    embed.add_field(name="Uptime", value=f"`{await gUtils.ret_uptime(uptime)}`", inline=True)
    embed.add_field(name="Roblox Connection", value=f"{':green_circle: `Online' if globals.heartBeat else ':red_circle: `Offline'}`", inline=True)
    embed.add_field(name="Last Rolimons Update", value=f"{await gUtils.fancy_time(globals.lastRoliUpdate)}", inline=True)
    embed.add_field(name="Servers", value=f"`{len(client.cache.get_guilds_view())}`", inline=True)
    embed.add_field(name="Users", value=f"`{sum(client.cache.get_guild(guild_id).member_count if client.cache.get_guild(guild_id).member_count is not None else 0 for guild_id in client.cache.get_guilds_view())}`", inline=True)
    embed.add_field(name="Shards", value=f"`{client.shard_count}`", inline=True)
    embed.add_field(name="Shard ID", value=f"`{shard}`", inline=True)
    embed.add_field(name="Cache Size", value=f"`{round(sum(f.stat().st_size for f in Path('cache/').glob('**/*') if f.is_file()) / 1048576, 1)} MB`", inline=True)
    embed.add_field(name="RoWhoIs+", value=f"`{'Subscribed` ' + emojiTable.get('subscription')}" if not productionMode or interaction.entitlements else '`Not Subscribed :(`', inline=True)
    await interaction.create_initial_response(response_type=hikari.ResponseType.MESSAGE_CREATE, embed=embed)

@app_commands.Command(context="User", intensity="low")
async def userid(interaction: hikari.CommandInteraction, username: str, download: bool = False):
    """Get a User ID from a username"""
    if not (await app_commands.interaction_permissions_check(interaction, requires_entitlements=download)): return
    embed = hikari.Embed(color=0xFF0000)
    shard = await gUtils.shard_metrics(interaction)
    user = await RoModules.convert_to_id(username, shard)
    if not (await app_commands.interaction_permissions_check(interaction, user_id=user.id)): return
    bust, headshot = await asyncio.gather(RoModules.get_player_bust(user.id, "420x420", shard), RoModules.get_player_headshot(user.id,  shard))
    embed.set_thumbnail(hikari.URL(bust))
    embed.set_author(name=f"{user.username} { '(' + user.nickname + ')' if user.username != user.nickname else ''}", icon=headshot, url=f"https://www.roblox.com/users/{user.id}/profile")
    embed.description = f"{emojiTable.get('staff') if user.id in staffIds else ''} {emojiTable.get('donor') if user.id in whoIsDonors else ''} {emojiTable.get('verified') if user.verified else ''}"
    embed.add_field(name="User ID:", value=f"`{user.id}`", inline=True)
    embed.colour = 0x00FF00
    if download: csv = "username, id, nickname, verified\n" + "\n".join([f"{user.username}, {user.id}, {user.nickname}, {user.verified}"])
    await interaction.create_initial_response(response_type=hikari.ResponseType.MESSAGE_CREATE, embed=embed, attachment=hikari.File(io.BytesIO(csv.encode()) if download else hikari.undefined.UNDEFINED, filename=f"rowhois-userid-{user.id}.csv") if download else hikari.undefined.UNDEFINED)

@app_commands.Command(context="User", intensity="low")
async def username(interaction: hikari.CommandInteraction, userid: int, download: bool = False):
    """Get a username from a User ID"""
    if not (await app_commands.interaction_permissions_check(interaction, user_id=userid, requires_entitlements=download)): return
    embed = hikari.Embed(color=0xFF0000)
    shard = await gUtils.shard_metrics(interaction)
    user = await RoModules.convert_to_username(userid, shard)
    bust, headshot = await asyncio.gather(RoModules.get_player_bust(user.id, "420x420", shard), RoModules.get_player_headshot(user.id, shard))
    embed.set_thumbnail(hikari.URL(bust))
    embed.set_author(name=f"{user.username} { '(' + user.nickname + ')' if user.username != user.nickname else ''}", icon=headshot, url=f"https://www.roblox.com/users/{user.id}/profile")
    embed.description = f"{emojiTable.get('staff') if user.id in staffIds else ''} {emojiTable.get('donor') if user.id in whoIsDonors else ''} {emojiTable.get('verified') if user.verified else ''}"
    embed.add_field(name="Username:", value=f"`{user.username}`", inline=True)
    embed.colour = 0x00FF00
    if download: csv = "username, id, nickname, verified\n" + "\n".join([f"{user.username}, {user.id}, {user.nickname}, {user.verified}"])
    await interaction.create_initial_response(response_type=hikari.ResponseType.MESSAGE_CREATE, embed=embed, attachment=hikari.File(io.BytesIO(csv.encode()) if download else hikari.undefined.UNDEFINED, filename=f"rowhois-username-{user.id}.csv") if download else hikari.undefined.UNDEFINED)

@app_commands.Command(context="User", intensity="high")
async def whois(interaction: hikari.CommandInteraction, user: str, download: bool = False):
    """Get detailed profile information from a User ID/Username"""
    if not (await app_commands.interaction_permissions_check(interaction, requires_entitlements=download)): return
    embed = hikari.Embed(color=0xFF0000)
    shard = await gUtils.shard_metrics(interaction)
    if not str(user).isdigit(): user = await RoModules.convert_to_id(user, shard)
    else: user = typedefs.User(id=int(user))
    await interaction.create_initial_response(response_type=hikari.ResponseType.DEFERRED_MESSAGE_CREATE)
    if not (await app_commands.interaction_permissions_check(interaction, user_id=user.id)): return
    user, groups, usernames, robloxbadges, email_verification = await RoModules.get_full_player_profile(user.id, shard)
    embed.set_thumbnail(user.thumbnail)
    embed.set_author(name=f"@{user.username} { '(' + user.nickname + ')' if user.username != user.nickname else ''}", icon=user.headshot, url=f"https://www.roblox.com/users/{user.id}/profile" if not user.banned else '')
    embed.description = f"{emojiTable.get('staff') if user.id in staffIds else ''} {emojiTable.get('donor') if user.id in whoIsDonors else ''} {emojiTable.get('verified') if user.verified else ''}"
    embed.add_field(name="User ID", value=f"`{user.id}`", inline=True)
    embed.add_field(name="Account Status", value=f"{'`Banned`' if user.banned else '`Okay`'}", inline=True)
    if robloxbadges[0]: embed.add_field(name="Badges", value=f"{''.join([f'{emojiTable.get(str(robloxbadges[1].get(badge)).lower())}' for badge in robloxbadges[0]])}", inline=True)
    if not user.banned:
        embed.add_field(name="Email", value=f"`{'Unverified' if email_verification == 3 else 'Verified'}{', Hat & Sign' if email_verification == 4 else ', Sign' if email_verification == 2 else ', Hat' if email_verification == 1 else ', Hat & Sign' if email_verification != 3 else ''}`", inline=True)
        if usernames: embed.add_field(name=f"Previous Usernames ({len(usernames)})", value=', '.join([f'`{name}`' for name in usernames[:10]]) + (f", and {len(usernames[10:])} more" if len(usernames) > 10 else ""), inline=True)
    embed.add_field(name="Joined", value=f"{await gUtils.fancy_time(user.joined)}", inline=True)
    embed.add_field(name="Last Online", value=f"{await gUtils.fancy_time(user.online)}", inline=True)
    embed.add_field(name="Friends", value=f"`{user.friends}`", inline=True)
    embed.add_field(name="Followers", value=f"`{user.followers}`", inline=True)
    embed.add_field(name="Following", value=f"`{user.following}`", inline=True)
    embed.add_field(name="Groups", value=f"`{groups}`", inline=True)
    if user.description is not None and user.description != '': embed.add_field(name="Description", value=f"```{user.description.replace('```', '') if user.description else 'None'}```", inline=False)
    embed.colour = 0x00FF00
    nlChar = "\n"
    if download:
        if isinstance(usernames, list) and usernames: whoData = "id, username, nickname, verified, rowhois_staff, account_status, joined, last_online, verified_email, groups, friends, followers, following, previous_usernames, description\n" + ''.join([f"{user.id}, {user.username}, {user.nickname}, {user.verified}, {user.id in staffIds}, {'Terminated' if user.banned else 'Okay' if not user.banned else 'None'}, {user.joined}, {user.online}, {('None' if email_verification == -1 else 'None' if email_verification == 0 else 'Hat' if email_verification == 1 else 'Sign' if email_verification == 2 else 'Unverified' if email_verification == 3 else 'Both' if email_verification == 4 else 'None') if str(email_verification).isdigit() else 'None'}, {groups}, {user.friends}, {user.followers}, {user.following}, {name}, {user.description.replace(',', '').replace(nlChar, '     ') if user.description else 'None'}\n" for name in usernames])
        elif user.banned: whoData = f"id, username, nickname, verified, rowhois_staff, account_status, joined, last_online, groups, friends, followers, following, description\n{user.id}, {user.username}, {user.nickname}, {user.verified}, {user.id in staffIds}, {'Terminated' if user.banned else 'Okay' if not user.banned else 'None'}, {user.joined}, {user.online}, {groups}, {user.friends}, {user.followers}, {user.following}, None, None\n"
        else: whoData = f"id, username, nickname, verified, rowhois_staff, account_status, joined, last_online, verified_email, groups, friends, followers, following, previous_usernames, description\n{user.id}, {user.username}, {user.nickname}, {user.verified}, {user.id in staffIds}, {'Terminated' if user.banned else 'Okay' if not user.banned else 'None'}, {user.joined}, {user.online}, {('None' if email_verification == -1 else 'None' if email_verification == 0 else 'Hat' if email_verification == 1 else 'Sign' if email_verification == 2 else 'Unverified' if email_verification == 3 else 'Both' if email_verification == 4 else 'None') if str(email_verification).isdigit() else 'None'}, {groups}, {user.friends}, {user.followers}, {user.following}, None, {user.description.replace(',', '').replace(nlChar, '     ') if user.description else 'None'}\n"
    initialResponse = time.time()
    await interaction.edit_initial_response(embed=embed, attachments=[await gUtils.write_volatile_cache(f'rowhois-{user.id}.csv', whoData)] if download else hikari.undefined.UNDEFINED)
    if not user.banned and user.id != 1:
        privateInventory, rap, value, items = await RoModules.get_limiteds(user.id, globals.roliData, shard)
        embed.add_field(name="Private Inventory", value=f"`{privateInventory}`", inline=True)
        if not privateInventory:
            embed.add_field(name="RAP", value=f"`{rap}`", inline=True)
            embed.add_field(name="Value", value=f"`{value}`", inline=True)
            if download: limData = f"owner_id, item_id\n" + ''.join([f"{user.id}, {item}{nlChar}" for item in items])
        if (time.time() - initialResponse) < 1: await asyncio.sleep(1 - (time.time() - initialResponse))
        await interaction.edit_initial_response(embed=embed, attachments=[await gUtils.write_volatile_cache(f'rowhois-limiteds-{user.id}.csv', limData), await gUtils.write_volatile_cache(f'rowhois-{user.id}.csv', whoData)] if download else hikari.undefined.UNDEFINED)

@app_commands.Command(context="Item", intensity="medium")
async def ownsitem(interaction: hikari.CommandInteraction, user: str, item: int, download: bool = False):
    """Check if a player owns a specific item"""
    if not (await app_commands.interaction_permissions_check(interaction, requires_entitlements=download)): return
    embed = hikari.Embed(color=0xFF0000)
    shard = await gUtils.shard_metrics(interaction)
    try: user = await RoModules.handle_usertype(user, shard)
    except Exception as e:
        if await app_commands.handle_error(e, interaction, "ownsitem", shard, "User"): return
    if not (await app_commands.interaction_permissions_check(interaction, user_id=user.id)): return
    data = await RoModules.owns_item(user.id, item, shard)
    if data[0] is None:
        if data[2] == "The specified user does not exist!": embed.description = "User does not exist or has been banned."
        elif data[2] == "The specified Asset does not exist!": embed.description = "Item does not exist."
        else: embed.description = f"Failed to retrieve data: {data[2]}"
        await interaction.create_initial_response(response_type=hikari.ResponseType.MESSAGE_CREATE, embed=embed)
        return
    if data[0]:
        embed.set_thumbnail(hikari.URL(await RoModules.get_item_thumbnail(item, "420x420", shard)))
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
    await interaction.create_initial_response(response_type=hikari.ResponseType.MESSAGE_CREATE, embed=embed, attachment=hikari.File(io.BytesIO(csv.encode()) if download else hikari.undefined.UNDEFINED, filename=f"rowhois-ownsitem-{user.id}.csv") if download else hikari.undefined.UNDEFINED)

@app_commands.Command(context="Badge", intensity="low")
async def ownsbadge(interaction: hikari.CommandInteraction, user: str, badge: int, download: bool = False):
    """Check if a player owns a specified badge and return it's award date"""
    if not (await app_commands.interaction_permissions_check(interaction, requires_entitlements=download)): return
    embed = hikari.Embed(color=0xFF0000)
    shard = await gUtils.shard_metrics(interaction)
    try: user = await RoModules.handle_usertype(user, shard)
    except Exception as e:
        if await app_commands.handle_error(e, interaction, "ownsbadge", shard, "User"): return
    if not (await app_commands.interaction_permissions_check(interaction, user_id=user.id)): return
    ownsBadge = await RoModules.owns_badge(user.id, badge, shard)
    if ownsBadge[0]:
        embed.set_thumbnail(hikari.URL(await RoModules.get_badge_thumbnail(badge, shard)))
        embed.colour = 0x00FF00
        embed.title = f"{user.username} owns this badge!"
        embed.description = f"Badge was awarded {await gUtils.fancy_time(ownsBadge[1])}"
    else: embed.description = f"{user.username} doesn't own the specified badge!"
    if download:
        if ownsBadge[0]: csv = "username, id, badge, owned, awarded\n" + "\n".join([f"{user.username}, {user.id}, {badge}, {ownsBadge[0]}, {ownsBadge[1]}"])
        else: csv = f"username, id, badge, owned, awarded\n{user.username}, {user.id}, {badge}, {ownsBadge[0]}, None"
    await interaction.create_initial_response(response_type=hikari.ResponseType.MESSAGE_CREATE, embed=embed, attachment=hikari.File(io.BytesIO(csv.encode()) if download else hikari.undefined.UNDEFINED, filename=f"rowhois-ownsbadge-{user.id}.csv") if download else hikari.undefined.UNDEFINED)

@app_commands.Command(context="Limited", intensity="medium")
async def limited(interaction: hikari.CommandInteraction, limited: str, download: bool = False):
    """Returns a limited ID, the rap, and value of a specified limited"""
    if not (await app_commands.interaction_permissions_check(interaction, requires_entitlements=download)): return
    embed = hikari.Embed(color=0xFF0000)
    shard = await gUtils.shard_metrics(interaction)
    limited_id, name, acronym, rap, value, demand, trend, projected, rare = await RoModules.get_rolidata_from_item(globals.roliData, limited)
    embed.set_thumbnail(hikari.URL(await RoModules.get_item_thumbnail(limited_id, "420x420", shard)))
    embed.colour = 0x00FF00
    embed.title = f"{name} ({acronym})" if acronym != "" else f"{name}"
    embed.url = f"https://www.roblox.com/catalog/{limited_id}/"
    embed.add_field(name="Limited ID", value=f"`{limited_id}`", inline=True)
    embed.add_field(name="RAP", value=f"`{rap}`", inline=True)
    embed.add_field(name="Value", value=f"`{value}`", inline=True)
    embed.add_field(name="Demand", value=f"`{demand}`", inline=True)
    embed.add_field(name="Trend", value=f"`{trend}`", inline=True)
    embed.add_field(name="Projected", value=f"`{projected}`", inline=True)
    embed.add_field(name="Rare", value=f"`{rare}`", inline=True)
    if download: csv = "id, name, acronym, rap, value, demand, trend, projected, rare\n" + "\n".join([f"{limited_id}, {name.replace(',', '')}, {acronym.replace(',', '') if acronym else 'None'}, {rap}, {value}, {demand}, {trend}, {projected}, {rare}"])
    await interaction.create_initial_response(response_type=hikari.ResponseType.MESSAGE_CREATE, embed=embed, attachment=hikari.File(io.BytesIO(csv.encode()) if download else hikari.undefined.UNDEFINED, filename=f"rowhois-limited-{limited_id if limited_id is not None else 'search'}.csv") if download else hikari.undefined.UNDEFINED)

@app_commands.Command(context="User", intensity="low")
async def isfriendswith(interaction: hikari.CommandInteraction, user1: str, user2: str):
    """Check whether a user is friended to another user"""
    # Technically we only have to check through one player as it's a mutual relationship
    embed = hikari.Embed(color=0xFF0000)
    shard = await gUtils.shard_metrics(interaction)
    user1 = await RoModules.handle_usertype(user1, shard)
    if not (await app_commands.interaction_permissions_check(interaction, user_id=user1.id)): return
    if user2.isdigit(): user2 = int(user2)
    userfriends = await RoModules.get_friends(user1.id, shard)
    friended = False
    for friends in userfriends['data']:
        friendName = str(friends['name']).lower() if not str(friends['name']).isdigit() else str(friends['name'])
        secondUser = str(user2).lower() if not str(user2).isdigit() else user2
        if friends['id'] == secondUser or friendName == secondUser:
            if friends['id'] in optOut:
                embed.description = "This user's friend has requested to opt-out of the RoWhoIs search."
                await log_collector.warn(f"Opt-out user {friends['id']} was called by {interaction.user.id} and denied!", initiator="RoWhoIs.isfriendswith")
                await interaction.create_initial_response(response_type=hikari.ResponseType.MESSAGE_CREATE, embed=embed)
                return
            friend_name, friended = friends['name'], True
            break
        else: friended = False
    if friended:
        embed.colour = 0x00FF00
        embed.description = f"{user1.username} is friends with {friend_name}!"
    else: embed.description = f"{user1.username} does not have this user friended."
    await interaction.create_initial_response(response_type=hikari.ResponseType.MESSAGE_CREATE, embed=embed)

@app_commands.Command(context="Group", intensity="low")
async def isingroup(interaction: hikari.CommandInteraction, user: str, group: int):
    """Check whether a user is in a group or not"""
    embed = hikari.Embed(color=0xFF0000)
    shard = await gUtils.shard_metrics(interaction)
    try: user = await RoModules.handle_usertype(user, shard)
    except Exception as e:
        if await app_commands.handle_error(e, interaction, "isingroup", shard, "User"): return
    if not (await app_commands.interaction_permissions_check(interaction, user_id=user.id)): return
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
        embed.set_thumbnail(hikari.URL(await RoModules.get_group_emblem(groupid, "420x420", shard)))
        embed.colour = 0x00FF00
        embed.title = f"{user.username} is in group `{groupname}`!"
        embed.description = f"Role: `{grouprole}`"
    else: embed.description = f"{user.username} is not in this group."
    await interaction.create_initial_response(response_type=hikari.ResponseType.MESSAGE_CREATE, embed=embed)

@app_commands.Command(context="Clothing Asset", intensity="extreme")
async def clothingtexture(interaction: hikari.CommandInteraction, clothing_id: int):
    """Get the texture file of a clothing item"""
    embed = hikari.Embed(color=0xFF0000)
    await interaction.create_initial_response(response_type=hikari.ResponseType.DEFERRED_MESSAGE_CREATE)
    if clothing_id in assetBlocklist:
        embed.description = "The asset creator has requested for this asset to be removed from RoWhoIs."
        await interaction.edit_initial_response(embed=embed, content="")
        return
    shard = await gUtils.shard_metrics(interaction)
    try: clothing_id = await RoModules.fetch_asset(clothing_id, shard)
    except ErrorDict.AssetNotAvailable:
        embed.description = "Cannot fetch moderated assets."
        await interaction.edit_initial_response(embed=embed, content="")
        return
    uploaded_image = hikari.File(f'cache/clothing/{clothing_id}.png', filename=f"rowhois-{clothing_id}.png")
    await interaction.edit_initial_response(attachment=uploaded_image, content="")

@app_commands.Command(context="Item", intensity="high")
async def itemdetails(interaction: hikari.CommandInteraction, item: int, download: bool = False):
    """Get advanced details about a catalog item"""
    if not (await app_commands.interaction_permissions_check(interaction, requires_entitlements=download)): return
    embed = hikari.Embed(color=0xFF0000)
    shard = await gUtils.shard_metrics(interaction)
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
    embed.set_thumbnail(hikari.URL(await RoModules.get_item_thumbnail(item, "420x420", shard)))
    embed.colour = 0x00FF00
    if download:
        nlChar = "\n"
        csv = "id, name, creator_name, creator_id, verified, created, updated, is_limited, is_limited_unique, is_collectible, quantity, lowest_price, remaining, price, description\n" + f"{item}, {data['Name'].replace(',', '')}, {data['Creator']['Name']}, {data['Creator']['CreatorTargetId']}, {data['Creator']['HasVerifiedBadge']}, {data['Created']}, {data['Updated']}, {data['IsLimited']}, {data['IsLimitedUnique']}, {isCollectible}, {data['CollectiblesItemDetails']['TotalQuantity'] if isCollectible else 'None'}, {data['CollectiblesItemDetails']['CollectibleLowestResalePrice'] if isCollectible else 'None'}, {data['Remaining'] if data['Remaining'] is not None else 'None'}, {data['PriceInRobux'] if not (data['IsLimited'] or data['Remaining'] == 0 or isCollectible) else 'None'}, {data['Description'].replace(',', '').replace(nlChar, '    ') if data['Description'] != '' else 'None'}"
    await interaction.create_initial_response(response_type=hikari.ResponseType.MESSAGE_CREATE, embed=embed, attachment=hikari.File(io.BytesIO(csv.encode()) if download else hikari.undefined.UNDEFINED, filename=f"rowhois-itemdetails-{item}.csv") if download else hikari.undefined.UNDEFINED)

@app_commands.Command(context="User", intensity="high")
async def membership(interaction: hikari.CommandInteraction, user: str):
    """Checks whether a user has premium and if they had Builders Club"""
    embed = hikari.Embed(color=0xFF0000)
    shard = await gUtils.shard_metrics(interaction)
    user = await RoModules.handle_usertype(user, shard)
    if not (await app_commands.interaction_permissions_check(interaction, user_id=user.id)): return
    try: data = await RoModules.get_membership(user.id, shard)
    except ErrorDict.DoesNotExistError:
        embed.description = "User does not exist or has been banned."
        await interaction.create_initial_response(response_type=hikari.ResponseType.MESSAGE_CREATE, embed=embed)
        return
    if all(not data[i] for i in range(1, 4)): noTiers = True
    else: noTiers = False
    newline = '\n'
    embed.title = f"{user.username}'s memberships:"
    embed.description = f"{(emojiTable.get('premium') + ' `Premium`' + newline) if data[0] else ''}{(emojiTable.get('bc') + ' `Builders Club`' + newline) if data[1] else ''}{(emojiTable.get('tbc') + '`Turbo Builders Club`' + newline) if data[2] else ''}{(emojiTable.get('obc') + ' `Outrageous Builders Club`' + newline) if data[3] else ''}{(str(user.username) + ' has no memberships.') if noTiers and not data[0] else ''}"
    embed.colour = 0x00FF00
    await interaction.create_initial_response(response_type=hikari.ResponseType.MESSAGE_CREATE, embed=embed)

@app_commands.Command(context="Group", intensity="medium")
async def group(interaction: hikari.CommandInteraction, group: int, download: bool = False):
    """Get detailed group information from a Group ID"""
    if not (await app_commands.interaction_permissions_check(interaction, requires_entitlements=download)): return
    embed = hikari.Embed(color=0xFF0000)
    shard = await gUtils.shard_metrics(interaction)
    groupInfo = await RoModules.get_group(group, shard)
    embed.set_thumbnail(hikari.URL(await RoModules.get_group_emblem(group, "420x420", shard)))
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
    await interaction.create_initial_response(response_type=hikari.ResponseType.MESSAGE_CREATE, embed=embed, attachment=hikari.File(io.BytesIO(csv.encode()) if download else hikari.undefined.UNDEFINED, filename=f"rowhois-group-{group}.csv") if download else hikari.undefined.UNDEFINED)

@app_commands.Command(context="Username", intensity="medium")
async def checkusername(interaction: hikari.CommandInteraction, username: str, download: bool = False):
    """Check if a username is available"""
    if not (await app_commands.interaction_permissions_check(interaction, requires_entitlements=download)): return
    embed = hikari.Embed(color=0xFF0000)
    shard = await gUtils.shard_metrics(interaction)
    usernameInfo = await RoModules.validate_username(username, shard)
    if usernameInfo[0] == 0:
        embed.colour = 0x00FF00
        embed.description = "Username is available!"
    elif usernameInfo[0] == 1: embed.description = "Username is taken."
    else: embed.description = f"Username not available.\n**Reason:** {usernameInfo[1]}"
    if download: csv = "username, code\n" + "\n".join([f"{username.replace(',', '')}, {usernameInfo[0]}"])
    await interaction.create_initial_response(response_type=hikari.ResponseType.MESSAGE_CREATE, embed=embed, attachment=await gUtils.write_volatile_cache(f"checkusername-{username}.csv", csv) if download else hikari.undefined.UNDEFINED)

@app_commands.Command(context="Group", intensity="extreme", requires_entitlement=True, kind_upsell=False)
async def groupclothing(interaction: hikari.CommandInteraction, group: int, page: int = 1):
    """Retrieves bulk clothing texture files from a group"""
    embed = hikari.Embed(color=0xFF0000)
    await interaction.create_initial_response(response_type=hikari.ResponseType.DEFERRED_MESSAGE_CREATE)
    shard = await gUtils.shard_metrics(interaction)
    groupAssets, pagination = await RoModules.get_creator_assets(group, "Group", page, shard)
    if pagination != page:
        embed.description = "Invalid page number."
        await interaction.edit_initial_response(embed=embed)
        return
    if not groupAssets:
        embed.description = "This group has no clothing assets."
        await interaction.edit_initial_response(embed=embed)
        return
    tasks, files = [], []
    for asset in groupAssets: tasks.append(gUtils.safe_wrapper(RoModules.fetch_asset, asset, shard))
    try: clothing = await asyncio.gather(*tasks)
    except Exception as e:
        if await app_commands.handle_error(e, interaction, "groupclothing", shard, "Group ID"): return
    for asset in clothing:
        if isinstance(asset, int):
            if asset not in assetBlocklist: files.append(hikari.File(f'cache/clothing/{asset}.png', filename=f"rowhois-groupclothing-{asset}.png"))
            else: embed.description = "One or more assets in this search have been requested to be removed by the creator."
    if not files: embed.description = "No clothing assets were found."
    await interaction.edit_initial_response(embed=embed if embed.description else hikari.undefined.UNDEFINED, attachments=files)

@app_commands.Command(context="User", intensity="extreme", requires_entitlement=True, kind_upsell=False)
async def userclothing(interaction: hikari.CommandInteraction, user: str, page: int = 1):
    """Retrieves bulk clothing texture files from a user"""
    embed = hikari.Embed(color=0xFF0000)
    await interaction.create_initial_response(response_type=hikari.ResponseType.DEFERRED_MESSAGE_CREATE)
    shard = await gUtils.shard_metrics(interaction)
    try:
        user = await RoModules.handle_usertype(user, shard)
    except Exception as e:
        if await app_commands.handle_error(e, interaction, "userclothing", shard, "User"): return
    if not (await app_commands.interaction_permissions_check(interaction, user_id=user.id)): return
    userAssets, pagination = await RoModules.get_creator_assets(user.id, "User", page, shard)
    if pagination != page or page < 1:
        embed.description = "Invalid page number."
        await interaction.edit_initial_response(embed=embed)
        return
    if not userAssets:
        embed.description = "This user has no clothing assets."
        await interaction.edit_initial_response(embed=embed)
        return
    tasks, files = [], []
    for asset in userAssets: tasks.append(gUtils.safe_wrapper(RoModules.fetch_asset, asset, shard))
    try: clothing = await asyncio.gather(*tasks)
    except Exception as e:
        if await app_commands.handle_error(e, interaction, "userclothing", shard, "User"): return
    for asset in clothing:
        if isinstance(asset, int):
            if asset not in assetBlocklist: files.append(hikari.File(f'cache/clothing/{asset}.png', filename=f"rowhois-userclothing-{asset}.png"))
            else: embed.description = "One or more assets in this search have been requested to be removed by the creator."
    if not files: embed.description = "No clothing assets were found."
    await interaction.edit_initial_response(embed=embed if embed.description else hikari.undefined.UNDEFINED, attachments=files)

@app_commands.Command(context="Asset", intensity="extreme")
async def asset(interaction: hikari.CommandInteraction, asset: int, filetype: Literal["rbxm", "png", "obj", "mesh", "rbxmx", "rbxl", "rbxlx", "mp4"], version: int = None):
    """Retrieve asset files"""
    embed = hikari.Embed(color=0xFF0000)
    await interaction.create_initial_response(response_type=hikari.ResponseType.DEFERRED_MESSAGE_CREATE)
    if asset in assetBlocklist:
        embed.description = "The asset creator has requested for this asset to be removed from RoWhoIs."
        await interaction.edit_initial_response(embed=embed)
        return
    try: asset = await RoModules.fetch_asset(asset, await gUtils.shard_metrics(interaction), location="asset", version=version, filetype=filetype)
    except ErrorDict.AssetNotAvailable:
        embed.description = "Cannot fetch moderated assets."
        await interaction.edit_initial_response(embed=embed)
        return
    if not asset:
        embed.description = "This asset does not exist."
        await interaction.edit_initial_response(embed=embed)
        return
    uploaded_file = hikari.File(f"cache/asset/{str(asset) + '-' + str(version) if version is not None else str(asset)}.{filetype}", filename=f"rowhois-{str(asset) + '-' + str(version) if version is not None else str(asset)}.{filetype}")
    await interaction.edit_initial_response(attachment=uploaded_file)

@app_commands.Command(context="Game", intensity="extreme")
async def game(interaction: hikari.CommandInteraction, game: int):
    """Get detailed game information from a game ID"""
    embed = hikari.Embed(color=0xFF0000)
    shard = await gUtils.shard_metrics(interaction)
    data = await RoModules.fetch_game(game, shard)
    embed.set_thumbnail(hikari.URL(data.thumbnail))
    embed.title = data.name
    embed.url = data.url
    embed.add_field(name="Place ID", value=f"`{data.id}`", inline=True)
    embed.add_field(name="Universe ID", value=f"`{data.universe}`", inline=True)
    embed.add_field(name="Creator", value=f"`{data.creator.username}` (`{data.creator.id}`) {emojiTable.get('verified') if data.creator.verified else ''}")
    embed.add_field(name="Copy Locked/Public", value=f"`{data.copy_protected}` | `{'Private' if not data.playable else 'Public'}`", inline=True)
    embed.add_field(name="Created", value=f"{(await gUtils.fancy_time(data.created))}", inline=True)
    embed.add_field(name="Updated", value=f"{(await gUtils.fancy_time(data.updated))}", inline=True)
    embed.add_field(name="Favorites", value=f"`{data.favorites}`", inline=True)
    embed.add_field(name="Likes", value=f"`{data.likes}`", inline=True)
    embed.add_field(name="Dislikes", value=f"`{data.dislikes}`", inline=True)
    embed.add_field(name="Visits", value=f"`{data.visits}`", inline=True)
    embed.add_field(name="Max Players", value=f"`{data.max_players}`", inline=True)
    embed.add_field(name="Playing", value=f"`{data.playing}`", inline=True)
    if data.description != "": embed.add_field(name="Description", value=f"```{data.description.replace('```', '')}```", inline=False)
    embed.colour = 0x00FF00
    await interaction.create_initial_response(response_type=hikari.ResponseType.MESSAGE_CREATE, embed=embed)
