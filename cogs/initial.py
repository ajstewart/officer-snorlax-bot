import discord
import traceback
import sys
import logging

from discord.ext import commands, tasks

from .utils.checks import check_guild_exists
from .utils.db import add_guild


logger = logging.getLogger()


class Initial(commands.Cog):
    """Cog to run on initial startup."""
    def __init__(self, bot: commands.bot, version: str) -> None:
        """
        The initialisation method of the cog.

        Args:
            bot: The discord.py bot representation.
            version: The bot version string.

        Returns:
            None
        """
        super(Initial, self).__init__()
        self.bot = bot
        self.version = version

    # EVENT LISTENER FOR WHEN THE BOT HAS SWITCHED FROM OFFLINE TO ONLINE.
    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """
        Method to run once the bot is ready.

        Returns:
            None
        """
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
    async def on_command_error(self, ctx: commands.context, error) -> None:
        """
        Handles any error that occurs with a command that is not standard.

        Args:
            ctx: The command context containing the message content and other
                metadata.
            error (Exception): The actual exception that could be a range of
                error types.

        Returns:
            None
        """
        if isinstance(error, commands.errors.CheckFailure):
            logger.warning('Check failure occurred.')
        else:
            logger.warning(
                'Ignoring exception in command {}:'.format(ctx.command)
            )
            traceback.print_exception(
                type(error), error, error.__traceback__, file=sys.stderr
            )
