from discord.ext import commands, tasks
import discord
import traceback
import sys
import logging
from .utils.checks import check_for_friend_code, check_admin


logger = logging.getLogger()


class Initial(commands.Cog):
    """docstring for Initial"""
    def __init__(self, bot):
        super(Initial, self).__init__()
        self.bot = bot

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

        # PRINTS HOW MANY GUILDS / SERVERS THE BOT IS IN.
        logger.info("Snorlax is in " + str(guild_count) + " guilds.")

        await self.bot.change_presence(
            activity=discord.Game(name="Sleeping...")
        )

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            logger.warning('Check failure occurred.')
        else:
            logger.warning('Ignoring exception in command {}:'.format(ctx.command))
            traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
