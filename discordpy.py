from discord.ext import commands
from discord import *
import asyncio
import json

config_json = json.load(open('./config.json', 'r'))

COGS = [
    "cogs.main"
]

class DiscordBot(commands.Bot):
    def __init__(self):
        super().__init__(
                    intents=Intents.all(),
                    help_command=None,
                    command_prefix="!"
                    )
        
    async def setup_hook(self):
        self.tree.copy_global_to(guild=Object(id=config_json["guild_id"]))
        await self.tree.sync(guild=Object(id=config_json["guild_id"]))
        return await super().setup_hook()

bot = DiscordBot()

@bot.event
async def on_ready():
    print("Logged!")

# @bot.event
# async def on_message(message):
#     if message.author.bot:
#         return 
#     if message.content == ">hot_reload":
#         for cog in COGS:
#             await bot.reload_extension(cog)
#         await message.channel.send("Hot reloaded!")
        
if __name__ == "__main__":
    async def boot():
        for cog in COGS:
            await bot.load_extension(cog)
    asyncio.run(boot())
    bot.run(config_json["token"])