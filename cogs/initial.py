from discord.ext import commands, tasks
import discord
import traceback
import sys
import logging
from .utils.checks import (
    check_for_friend_code, check_admin, check_guild_exists
)
from .utils.db import add_guild


logger = logging.getLogger()


class Initial(commands.Cog):
    """docstring for Initial"""
    def __init__(self, bot, version):
        super(Initial, self).__init__()
        self.bot = bot
        self.version = version

    # EVENT LISTENER FOR WHEN THE BOT HAS SWITCHED FROM OFFLINE TO ONLINE.
    @commands.Cog.listener()
    async def on_ready(self):
        guild_count = 0

        # LOOPS THROUGH ALL THE GUILD / SERVERS THAT THE BOT IS ASSOCIATED WITH.
        for guild in self.bot.guilds:
            # PRINT THE SERVER'S ID AND NAME.
            logger.info(f"- {guild.id} (name: {guild.name})")

            # INCREMENTS THE GUILD COUNTER.
            guild_count = guild_count + 1

            # CHECK THAT THE GUILD IS IN THE DB
            if not check_guild_exists(guild.id, check_active=True):
                # ADD TO DB IF DOES NOT EXIST
                logger.info(f'Adding {guild.name} to database.')
                ok = add_guild(guild)

        # PRINTS HOW MANY GUILDS / SERVERS THE BOT IS IN.
        logger.info("Snorlax is in " + str(guild_count) + " guilds.")

        await self.bot.change_presence(
            activity=discord.Game(name=f"v{self.version} - sleeping...")
        )

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            logger.warning('Check failure occurred.')
        else:
            logger.warning('Ignoring exception in command {}:'.format(ctx.command))
            traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
