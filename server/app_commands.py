"""
RoWhoIs app command backend library
Pray to god nothing here breaks, soldier
"""
import hikari, time, types, inspect
from typing import Literal, get_origin, get_args
from collections import defaultdict, deque
from utils import logger, ErrorDict
from server import globals

command_tree = {}
log_collector = logger.AsyncLogCollector("logs/main.log")

def init(productionmode: bool, optout, userblocklist, emojitable, subscription_bypass) -> None:
    global productionMode, optOut, userBlocklist, assetBlock, emojiTable, subscriptionBypass
    productionMode, optOut, userBlocklist, emojiTable, subscriptionBypass = productionmode, optout, userblocklist, emojitable, subscription_bypass

class CommandType:
    """Class for defining command objects"""
    def __init__(self, wrapper, name: str, description: str, context: str, intensity: Literal["extreme", "high", "medium", "low"], requires_entitlement: bool = False, requires_connection: bool = True, options: hikari.CommandOption = None, kind_upsell: bool = True):
        self.wrapper = wrapper
        self.name = name
        self.description = description if description else 'No description provided.'
        self.context = context
        self.intensity = intensity
        self.requires_entitlement = requires_entitlement
        self.requires_connection = requires_connection
        self.options = options
        self.kind_upsell = kind_upsell

async def commandType_fetch(interaction: hikari.CommandInteraction) -> CommandType:
    """Converts an interaction into a CommandType object"""
    command_name = interaction.command_name
    if command_name in command_tree: return command_tree[command_name]
    else: return None

userCooldowns = defaultdict(lambda: defaultdict(deque))
cooldownValues = {
    "extreme": {"premium": 5, "standard": 2},
    "high": {"premium": 6, "standard": 3},
    "medium": {"premium": 7, "standard": 4},
    "low": {"premium": 8, "standard": 5},
}

async def check_cooldown(interaction: hikari.CommandInteraction, intensity: Literal["extreme", "high", "medium", "low"], commandName: str, cooldown_seconds: int = 60) -> bool:
    """Custom cooldown handler for user commands
    True = On cooldown, False = Not on cooldown
    """ # Still somewhat glitchy, but it works and it's better than the old system
    userId, current_time = interaction.user.id, time.time()
    user_cooldowns = userCooldowns[commandName][userId]
    if (interaction.entitlements and productionMode) or not productionMode or (interaction.user.id in subscriptionBypass): max_commands = cooldownValues[intensity]["premium"]
    else: max_commands = cooldownValues[intensity]["standard"]
    if len(user_cooldowns) >= max_commands and current_time - user_cooldowns[0] < cooldown_seconds:
        remaining_seconds = round(cooldown_seconds - (current_time - user_cooldowns[0]))
        if remaining_seconds <= 0: remaining_seconds = 1
        await interaction.create_initial_response(response_type=hikari.ResponseType.MESSAGE_CREATE, content=f"Your enthusiasm is greatly appreciated, but please slow down! Try again in **{remaining_seconds}** second{'s' if remaining_seconds >= 2 else ''}.", flags=hikari.MessageFlag.EPHEMERAL)
        return True
    else:
        user_cooldowns.append(current_time)
        if len(user_cooldowns) > max_commands: user_cooldowns.popleft()
    return False

async def sync_app_commands(client: hikari.GatewayBot) -> None:
    """Syncs the global app command tree with the Discord API."""
    try:
        existingCommands = await client.rest.fetch_application_commands(client.get_me().id)
        existingCommandsDict = {cmd.name: cmd for cmd in existingCommands}
        for command in command_tree.values():
            if command.name in existingCommandsDict:
                existingCommand = existingCommandsDict[command.name]
                if existingCommand.description != command.description or existingCommand.options != command.options: await client.rest.edit_application_command(client.get_me().id, existingCommand.id, name=command.name, description=command.description, options=command.options)
            else: await client.rest.create_slash_command(application=client.get_me().id, name=command.name, description=command.description, options=command.options)
        for command_name, command in existingCommandsDict.items():
            if command_name not in command_tree: await client.rest.delete_application_command(client.get_me().id, command.id)
    except Exception as e: await log_collector.error(f"Error syncing app commands: {e}", initiator="RoWhoIs.sync_app_commands")

class Command:
    global command_tree
    def __init__(self, context: str, intensity: Literal["extreme", "high", "medium", "low"], requires_entitlement: bool = False, requires_connection: bool = True, kind_upsell: bool = True):
        self.intensity = intensity
        self.requires_entitlement = requires_entitlement
        self.requires_connection = requires_connection
        self.context = context
        self.kind_upsell = kind_upsell
    def __call__(self, func):
        # Inspect the function to create a CommandType object to append to the command tree
        self.func = func
        self.name = func.__name__
        self.description = func.__doc__
        sig = inspect.signature(func)
        self.options = []
        for name, param in sig.parameters.items():
            if name == 'self' or name == 'interaction': continue
            option_type = hikari.OptionType.STRING
            choices = None
            if param.annotation is int: option_type = hikari.OptionType.INTEGER
            elif param.annotation is bool: option_type = hikari.OptionType.BOOLEAN
            elif get_origin(param.annotation) is Literal:
                literal_values = get_args(param.annotation)
                choices = [hikari.CommandChoice(name=str(value), value=value) for value in literal_values]
                option_type = hikari.OptionType.STRING if isinstance(literal_values[0], str) else hikari.OptionType.INTEGER
            option = hikari.CommandOption(name=name, description='No description provided.', type=option_type, is_required=True if param.default == inspect.Parameter.empty else False, choices=choices)
            self.options.append(option)
        command_tree[self.name] = CommandType(self.wrapper, self.name, self.description, self.context, self.intensity, self.requires_entitlement, self.requires_connection, self.options, self.kind_upsell)
        return self.wrapper
    def __get__(self, instance, owner): return types.MethodType(self, instance)
    async def wrapper(self, interaction: hikari.CommandInteraction, *args, **kwargs):
        try:
            if await check_cooldown(interaction, self.intensity, self.func.__name__): return
            await self.func(interaction, *args, **kwargs)
        except Exception as e: raise e

async def handle_error(error, interaction: hikari.CommandInteraction, command: str, shard_id: int, context: str = "Requested resource") -> bool:
    """Handles both user-facing and backend errors, even if they are undocumented."""
    embed = hikari.Embed(color=0xFF0000)
    if isinstance(error, ErrorDict.InvalidAuthorizationError): embed.description = f"Hm.. Looks like we can't access this {context.lower()} right now. Please try again later."
    elif isinstance(error, ErrorDict.DoesNotExistError): embed.description = f"{context} doesn't exist."
    elif isinstance(error, ErrorDict.MismatchedDataError): embed.description = f"{context} is invalid."
    elif isinstance(error, ErrorDict.RatelimitedError): embed.description = "RoWhoIs is experiencing unusually high demand and your command couldn't be fulfilled. Please try again later."
    elif isinstance(error, hikari.errors.NotFoundError): return True
    else:
        await log_collector.error(f"Error in the {command} command: {type(error)}, {error}", initiator="RoWhoIs.handle_error", shard_id=shard_id)
        embed.description = "Whoops! An unknown error occurred. Please try again later."
    if isinstance(interaction, hikari.CommandInteraction):
        try: await interaction.create_initial_response(response_type=hikari.ResponseType.MESSAGE_CREATE, embed=embed, flags=hikari.MessageFlag.EPHEMERAL, attachments=None)
        except hikari.errors.BadRequestError: await interaction.edit_initial_response(embed=embed, attachments=None)
    else:
        try: await interaction.interaction.create_initial_response(response_type=hikari.ResponseType.MESSAGE_CREATE, embed=embed, flags=hikari.MessageFlag.EPHEMERAL, attachments=None)
        except hikari.errors.BadRequestError: await interaction.interaction.edit_initial_response(embed=embed, attachments=None)
    return True

async def interaction_permissions_check(interaction: hikari.CommandInteraction, command: CommandType = None, user_id: int = None, kind_upsell: bool = True, requires_connection: bool = True, requires_entitlements: bool = False) -> bool:
    """Checks if the user has the required entitlements to run the command. Returns False if the user does not have the required entitlements."""
    embed = hikari.Embed(color=0xFF0000)
    if command is None: command = await commandType_fetch(interaction)
    if (command.requires_entitlement or requires_entitlements) and productionMode and (interaction.user.id not in subscriptionBypass) and not interaction.entitlements:
        try:
            if not (kind_upsell or command.kind_upsell):
                await interaction.create_premium_required_response()
                return False
        except hikari.errors.BadRequestError: pass
        embed.description = f"This advanced option requires RoWhoIs {emojiTable.get('subscription')}. Please upgrade to use this feature!"
    elif interaction.user.id in userBlocklist:
        await log_collector.warn(f"Blocklist user {interaction.user.id} attempted to call a command and was denied!", initiator="RoWhoIs.interaction_permissions_check")
        embed.description = "You have been permanently banned from using RoWhoIs. In accordance to our [Terms of Service](https://rowhois.com/terms-of-service/), we reserve the right to block any user from using our service."
    elif user_id and user_id in optOut:
        await log_collector.warn(f"Blocklist user {user_id} was requested by {interaction.user.id} and denied!", initiator="RoWhoIs.interaction_permissions_check")
        embed.description = "This user has requested to opt-out of RoWhoIs."
    elif globals.heartBeat is False and requires_connection: embed.description = "Roblox is currently experiencing downtime. Please try again later."
    else: return True
    try: await interaction.create_initial_response(response_type=hikari.ResponseType.MESSAGE_CREATE, embed=embed, flags=hikari.MessageFlag.EPHEMERAL)
    except hikari.errors.BadRequestError: await interaction.edit_initial_response(embed=embed)
    return False

async def interaction_runner(event: hikari.InteractionCreateEvent):
    try:
        command_name = event.interaction.command_name
        shard = event.shard.id
        if command_name in command_tree:
            command = command_tree[command_name]
            options = event.interaction.options
            args, kwargs = [], {}
            if options:
                for option in options:
                    if isinstance(option.value, dict): kwargs[option.name] = option.value
                    else: args.append(option.value)
            try:
                if not await interaction_permissions_check(event.interaction, requires_connection=command.requires_connection, requires_entitlements=command.requires_entitlement, kind_upsell=command.kind_upsell): return
                await command.wrapper(event.interaction, *args, **kwargs)
            except Exception as e: await handle_error(e, event, command.name, shard, command.context)
        else:
            await log_collector.error(f"Command '{command_name}' not found in command tree.", initiator="RoWhoIs.interaction_runner", shard_id=shard)
            await event.interaction.create_initial_response(response_type=hikari.ResponseType.MESSAGE_CREATE, content="Whoops! I couldn't find this command.", flags=hikari.MessageFlag.EPHEMERAL)
            return
    except Exception as e: raise e
