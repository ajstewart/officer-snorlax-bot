"""Initial cog for the bot."""

import asyncio
import sys
import traceback

import discord

from discord.ext import commands, tasks

from bot_logger import get_logger
from models import Guild, GuildScheduleSettings
from repositories import (
    FriendCodeChannelRepository,
    GuildRepository,
    GuildScheduleSettingsRepository,
    ScheduleRepository,
)

logger = get_logger(__name__)


class Initial(commands.Cog):
    """Cog to run on initial startup."""

    def __init__(self, bot: commands.Bot) -> None:
        """The initialisation method of the cog.

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
        self.remove_zombie_guilds.start()
        self.remove_zombie_friend_channels.start()

    # EVENT LISTENER FOR WHEN THE BOT HAS SWITCHED FROM OFFLINE TO ONLINE.
    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Method to run once the bot is ready.

        Returns:
            None
        """
        guild_count = 0

        async with self.bot.db_session() as session:
            guild_repo = GuildRepository(session)
            # LOOPS THROUGH ALL THE GUILD / SERVERS THAT THE BOT IS ASSOCIATED WITH.
            for guild in self.bot.guilds:
                # PRINT THE SERVER'S ID AND NAME.
                logger.info(f"{guild.id} (name: {guild.name})")

                # INCREMENTS THE GUILD COUNTER.
                guild_count = guild_count + 1

                # CHECK THAT THE GUILD IS IN THE DB
                if not await guild_repo.check_exists(guild.id, check_active=True):
                    # ADD TO DB IF DOES NOT EXIST
                    logger.info(f"Adding {guild.name} to database.")
                    guild_db = Guild.create_from_discord_guild(guild)
                    await guild_repo.create_guild(guild_db)

                # CHECK THAT IT HAS ASSOCIATED GUILD_SCHEDULE_SETTINGS ENTRY
                schedule_settings_repo = GuildScheduleSettingsRepository(session)
                if not await schedule_settings_repo.check_exists(guild.id):
                    logger.info(f"Adding default schedule settings for {guild.name}.")
                    guild_schedule_settings_db = GuildScheduleSettings.create_default(
                        guild.id
                    )
                    await schedule_settings_repo.create(guild_schedule_settings_db)

        # PRINTS HOW MANY GUILDS / SERVERS THE BOT IS IN.
        logger.info("Snorlax is in " + str(guild_count) + " guilds.")

        await self.bot.change_presence(
            activity=discord.Game(name=f"v{self.version} - sleeping...")
        )

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error) -> None:
        """Handles any error that occurs with a command that is not standard.

        Args:
            ctx: The command context containing the message content and other
                metadata.
            error (Exception): The actual exception that could be a range of
                error types.

        Returns:
            None
        """
        if isinstance(error, commands.errors.CheckFailure):
            logger.warning("Check failure occurred.")
        else:
            logger.warning("Ignoring exception in command {}:".format(ctx.command))
            traceback.print_exception(
                type(error), error, error.__traceback__, file=sys.stderr
            )

    @tasks.loop(seconds=900)
    async def remove_zombie_schedules(self) -> None:
        """Runs a check of schedules to see if a channel has been deleted.

        If a channel is found to be missing then that schedule is dropped.
        """
        logger.info("Performing zombie schedules check.")

        removed = 0

        async with self.bot.db_session() as session:
            schedule_repo = ScheduleRepository(session)
            guild_repo = GuildRepository(session)

            # Get all active guilds
            active_guilds = await guild_repo.get_all(active_only=True)

            for guild in active_guilds:
                logger.debug("Checking schedules for guild: %s", guild.id)
                schedules = await schedule_repo.get_all(guild_id=guild.id)
                logger.debug(
                    "Found %s schedules for guild: %s", len(schedules), guild.id
                )
                for schedule in schedules:
                    logger.debug(
                        "Checking schedule: %s for guild: %s", schedule.rowid, guild.id
                    )
                    channel = self.bot.get_channel(schedule.channel)
                    if channel is None:
                        logger.warning(
                            f"Channel {schedule.channel} not found! Dropping schedule"
                            f" {schedule.rowid}."
                        )
                        try:
                            await schedule_repo.delete(schedule)
                        except Exception as e:
                            logger.warning(
                                "Dropping of schedule %s failed!.",
                                schedule.rowid,
                                exc_info=e,
                            )
                        logger.info(
                            "Dropping of schedule %s successful.",
                            schedule.rowid,
                        )
                        removed += 1

        logger.info("Zombie schedules check completed: %s removed.", removed)

    @tasks.loop(seconds=900)
    async def remove_zombie_friend_channels(self) -> None:
        """Runs a check of friend code whitelist channels.

        Specifically to see if a channel has been deleted that was missed.

        If a channel is found to be missing then that friend channel is removed.
        """
        logger.info("Performing zombie friend channel check.")
        removed = 0

        async with self.bot.db_session() as session:
            friend_code_channel_repo = FriendCodeChannelRepository(session)
            guild_repo = GuildRepository(session)

            friend_code_channels = await friend_code_channel_repo.get_all()
            logger.debug(
                "Found %s friend code channels in the database.",
                len(friend_code_channels),
            )

            for friend_channel in friend_code_channels:
                logger.debug(
                    "Checking friend code channel: %s for guild: %s",
                    friend_channel.channel,
                    friend_channel.guild,
                )
                # If a guild is not active then don't check.
                guild = await guild_repo.get(friend_channel.guild)
                if guild is None or guild.active is False:
                    continue
                channel = self.bot.get_channel(friend_channel.channel)
                if channel is None:
                    logger.warning(
                        "Channel %s not found! Removing from friend code"
                        " whitelist database.",
                        friend_channel.channel,
                    )
                    try:
                        await friend_code_channel_repo.delete(friend_channel)
                    except Exception as e:
                        logger.warning(
                            "Dropping of friend code channel %s failed! Error: %s.",
                            friend_channel.channel,
                            e,
                        )
                    logger.info(
                        "Dropping of friend code channel %s successful.",
                        friend_channel.channel,
                    )
                    removed += 1

        logger.info("Zombie friend code channels check completed: %s removed.", removed)

    @tasks.loop(seconds=900)
    async def remove_zombie_guilds(self) -> None:
        """Runs a check of guilds to see if a guild has left which was missed.

        If a guild is no longer there then it is set to deactive in the
        DB and schedules deactivated.
        """
        logger.info("Performing zombie guilds check.")

        removed = 0

        async with self.bot.db_session() as session:
            guild_repo = GuildRepository(session)
            schedule_repo = ScheduleRepository(session)

            guilds = await guild_repo.get_all(active_only=True)

            logger.debug("Found %s active guilds in the database.", len(guilds))

            # Remember that the index of the df is the guild id.
            for guild in guilds:
                guild_id = guild.id
                guild_obj = self.bot.get_guild(guild_id)
                if guild_obj is None:
                    logger.warning("Guild %s not found! Deactivating.", guild_id)
                    # Set guild to inactive
                    guild.active = False
                    # Check for schedules and deactivate them all
                    schedules = await schedule_repo.get_all(guild_id=guild_id)
                    if schedules:
                        logger.info(
                            "Deactivating all schedules for guild %s.", guild_id
                        )
                        for schedule in schedules:
                            logger.info("Deactivating schedule: %s.", schedule.rowid)
                            schedule.active = False

                    removed += 1

        logger.info("Zombie guilds check completed: %s deactivated.", removed)

    @remove_zombie_schedules.before_loop
    @remove_zombie_friend_channels.before_loop
    async def before_timer_schedules(self) -> None:
        """Method to process before the zombie check loop is started.

        The purpose is to make sure the bot is ready before starting.
        """
        await self.bot.wait_until_ready()

        # Delay by 1 min so zombie guild check can complete.
        await asyncio.sleep(60)

    @remove_zombie_guilds.before_loop
    async def before_timer_guilds(self) -> None:
        """Method to process before the zombie check loop is started.

        The purpose is to make sure the bot is ready before starting.
        """
        await self.bot.wait_until_ready()


async def setup(bot: commands.bot) -> None:
    """The setup function to initiate the cog.

    Args:
        bot: The bot for which the cog is to be added.
    """
    if bot.test_guild is not None:
        await bot.add_cog(Initial(bot), guild=discord.Object(id=bot.test_guild))
    else:
        await bot.add_cog(Initial(bot))
