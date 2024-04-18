import hikari, time
from typing import Literal
from utils import logger

command_tree, userCooldowns = {}, {}
log_collector = logger.AsyncLogCollector("logs/main.log")

async def check_cooldown(interaction: hikari.CommandInteraction, intensity: Literal["extreme", "high", "medium", "low"], cooldown_seconds: int = 60) -> bool:
    """Custom cooldown handler for user commands
    True = On cooldown, False = Not on cooldown
    """
    global userCooldowns
    try:
        currentTime = time.time()
        for userId in list(userCooldowns.keys()):
            for command in list(userCooldowns[userId].keys()):
                userCooldowns[userId][command] = [timestamp for timestamp in userCooldowns[userId][command] if currentTime - timestamp <= time.time() + cooldown_seconds]
                if not userCooldowns[userId][command]: del userCooldowns[userId][command]
            if not userCooldowns[userId]: del userCooldowns[userId]
        userId = interaction.user.id
        commandName = inspect.stack()[1].function
        premiumCoolDict = {"extreme": 5, "high": 6, "medium": 7, "low": 8}
        stdCoolDict = {"extreme": 2, "high": 3, "medium": 4, "low": 5}
        # if len(interaction.entitlements) >= 1 and productionMode or not productionMode: maxCommands = premiumCoolDict.get(intensity)
        # else:
        maxCommands = stdCoolDict.get(intensity)
        if userId not in userCooldowns: userCooldowns[userId] = {}
        if commandName not in userCooldowns[userId]: userCooldowns[userId][commandName] = []
        recentTimestamps = [timestamp for timestamp in userCooldowns[userId][commandName] if currentTime - timestamp <= time.time() + cooldown_seconds]
        if len(recentTimestamps) < maxCommands:
            recentTimestamps.append(currentTime)
            userCooldowns[userId][commandName] = recentTimestamps
            return False
        else:
            earliestTimestamp = min(recentTimestamps)
            remainingSeconds = max(0, round(((earliestTimestamp + (time.time() + cooldown_seconds)) - currentTime).total_seconds()))
            await interaction.response.send_message(f"*Your enthusiasm is greatly appreciated, but please slow down! Try again in **{remainingSeconds}** seconds.*", ephemeral=True)
            return True
    except Exception as e:
        await log_collector.error(f"Error in cooldown handler: {e} | Command: {commandName} | User: {userId} | Returning False... ", initiator="RoWhoIs.check_cooldown")
        return False

class Command:
    def __init__(self, intensity: Literal["extreme", "high", "medium", "low"], func= None, requires_entitlement= False, requires_connection= True):
        self.func = func
        self.intensity = intensity
        self.requires_entitlement = requires_entitlement
        self.requires_connection = requires_connection
        if func:
            self.name = func.__name__
            self.description = func.__doc__

    def __call__(self, *args, **kwargs): return self.wrapper(*args, **kwargs)
    def __get__(self, instance, owner): return types.MethodType(self, instance)
    async def wrapper(self, interaction: hikari.CommandInteraction, *args, **kwargs):
        try:
            if await check_cooldown(interaction, self.intensity): return
            await self.func(interaction, *args, **kwargs)
        except Exception as e:
            raise e
            # await handle_error(e, interaction, self.func.__name__, shard, "User")


async def interaction_runner(event: hikari.InteractionCreateEvent):
    try:
        if isinstance(event.interaction, hikari.CommandInteraction):
            command_name = event.interaction.command_name
            if command_name in command_tree:
                command_func, _ = command_tree[command_name]
                await command_func(event.interaction)
    except Exception as e:
        raise e
        # await handle_error(e, event.interaction, event.interaction.command_name, event.interaction.guild_id, "User")