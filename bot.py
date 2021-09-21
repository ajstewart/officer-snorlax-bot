#!/usr/bin/env python

import discord
import os
import logging
from dotenv import load_dotenv
from discord.ext import commands
from cogs.utils.checks import check_admin
from cogs.utils.utils import get_logger, get_prefix
from cogs import (
    initial, management, schedules, fc_filter, time_channel, join_name_filter
)

# LOADS THE .ENV FILE THAT RESIDES ON THE SAME LEVEL AS THE SCRIPT.
load_dotenv()

# GRAB THE API TOKEN FROM THE .ENV FILE.
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

version = '0.1.3dev'

intents = discord.Intents.default()
intents.members = True

logger = get_logger(logfile='snorlax.log')
logger.info('Starting bot...')

# GETS THE CLIENT OBJECT FROM DISCORD.PY. CLIENT IS SYNONYMOUS WITH BOT.
bot = commands.Bot(
    intents=intents, command_prefix=(get_prefix))
bot.help_command.add_check(check_admin)

bot.add_cog(initial.Initial(bot, version))
bot.add_cog(management.Management(bot))
bot.add_cog(fc_filter.FriendCodeFilter(bot))
bot.add_cog(join_name_filter.JoinNameFilter(bot))
bot.add_cog(time_channel.TimeChannel(bot))
bot.add_cog(schedules.Schedules(bot))

# EXECUTES THE BOT WITH THE SPECIFIED TOKEN. TOKEN HAS BEEN REMOVED AND USED JUST AS AN EXAMPLE.
bot.run(DISCORD_TOKEN)
