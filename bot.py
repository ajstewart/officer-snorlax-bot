#!/usr/bin/env python

import discord
import os
from dotenv import load_dotenv
from discord.ext import commands
from cogs.utils.checks import check_admin
from cogs.utils.utils import get_logger, get_prefix


class MyBot(commands.Bot):
    """Bot class.
    """
    def __init__(self, command_prefix, intents, version, guild_server=None):
        super().__init__(
            command_prefix=command_prefix,
            intents=intents
        )
        self.initial_extensions = [
            'cogs.initial',
            'cogs.management',
            'cogs.fc_filter',
            'cogs.join_name_filter',
            'cogs.time_channel',
            'cogs.schedules'
        ]
        self.help_command.add_check(check_admin)
        self.my_version = version
        self.guild_server = guild_server

    async def setup_hook(self):
        for ext in self.initial_extensions:
            await self.load_extension(ext)

        if self.guild_server is None:
            foo = await self.tree.sync()
        else:
            foo = await self.tree.sync(guild=discord.Object(id=self.guild_server))
        print(foo)

    async def on_ready(self):
        print('Ready!')


# LOADS THE .ENV FILE THAT RESIDES ON THE SAME LEVEL AS THE SCRIPT.
load_dotenv()

# GRAB THE API TOKEN FROM THE .ENV FILE.
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
# Set the GUILD_SERVER ID
try:
    GUILD_SERVER = int(os.getenv('GUILD_SERVER'))
    if len(str(GUILD_SERVER)) < 17:
        raise ValueError(f"{GUILD_SERVER} is not a valid guild ID!")
except Exception as e:
    GUILD_SERVER = None

version = '1.0.0dev'

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

logger = get_logger(logfile='snorlax.log')
logger.info('Starting bot...')

bot = MyBot((get_prefix), intents, version, guild_server=GUILD_SERVER)
bot.run(DISCORD_TOKEN)
