import discord
import traceback
import sys
import logging

from discord.ext import commands, tasks

from .utils.checks import check_guild_exists
from .utils import db as snorlax_db


logger = logging.getLogger()


class Initial(commands.Cog):
    """Cog to run on initial startup."""
    def __init__(self, bot: commands.bot) -> None:
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
        self.version = bot.my_version

        self.remove_zombie_schedules.start()

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
            logger.info(f"{guild.id} (name: {guild.name})")

            # INCREMENTS THE GUILD COUNTER.
            guild_count = guild_count + 1

            # CHECK THAT THE GUILD IS IN THE DB
            if not await check_guild_exists(guild.id, check_active=True):
                # ADD TO DB IF DOES NOT EXIST
                logger.info(f'Adding {guild.name} to database.')
                ok = await snorlax_db.add_guild(guild)

            # CHECK THAT IT HAS ASSOCIATED GUILD_SCHEDULE_SETTINGS ENTRY
            if not await snorlax_db.check_schedule_settings_exists(guild.id):
                logger.info(f"Adding default schedule settings for {guild.name}.")
                ok = await snorlax_db.add_default_schedule_settings(guild.id)

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

    @tasks.loop(seconds=1800)
    async def remove_zombie_schedules(self) -> None:
        """Runs a check of schedules to see if a channel has been deleted that was missed.

        If a channel is found to be missing then that schedule is dropped.
        """
        logging.info("Performing zombie schedules check.")

        removed = 0
        schedules_df = await snorlax_db.load_schedule_db()

        for _, row in schedules_df[['rowid', 'channel']].iterrows():
            channel = self.bot.get_channel(row['channel'])
            if channel is None:
                logging.warning(f"Channel {row['channel']} not found! Dropping schedule {row['rowid']}.")
                try:
                    ok = await snorlax_db.drop_schedule(int(row['rowid']))
                except Exception as e:
                    logging.warning(f"Dropping of schedule {row['rowid']} failed! Error: {e}.")
                else:
                    if ok:
                        logging.info(f"Dropping of schedule {row['rowid']} successful.")
                        removed += 1
                    else:
                        logging.warning(f"Dropping of schedule {row['rowid']} failed! Error: {e}.")

        logging.info(f"Zombie schedules check completed: {removed} removed.")

    @remove_zombie_schedules.before_loop
    async def before_timer(self) -> None:
        """
        Method to process before the zombie check loop is started.

        The purpose is to make sure the bot is ready before starting.
        """
        await self.bot.wait_until_ready()


async def setup(bot: commands.bot) -> None:
    """The setup function to initiate the cog.

    Args:
        bot: The bot for which the cog is to be added.
    """
    if bot.test_guild is not None:
        await bot.add_cog(
            Initial(bot),
            guild=discord.Object(id=bot.test_guild)
        )
    else:
        await bot.add_cog(Initial(bot))
