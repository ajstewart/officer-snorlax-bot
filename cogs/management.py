"""
The management cog which contains commands related to the management
and set up of the bot.
"""

import discord
import os
import logging
import traceback

from discord import Guild, TextChannel, app_commands, Interaction, CategoryChannel
from discord.abc import GuildChannel
from discord.ext import commands
from discord.utils import get
from dotenv import load_dotenv, find_dotenv

from .utils import checks as snorlax_checks
from .utils import db as snorlax_db
from .utils import autocompletes as snorlax_autocompletes
from .utils import log_msgs as snorlax_logs
from .utils.embeds import get_settings_embed
from .utils.utils import get_current_time


logger = logging.getLogger()
load_dotenv(find_dotenv())
DEFAULT_TZ = os.getenv('DEFAULT_TZ')


class Management(commands.Cog):
    """
    Cog for the management commands.
    """
    def __init__(self, bot: commands.bot) -> None:
        """
        Init method for management.

        Args:
            bot: The discord.py bot representation.

        Returns:
            None.
        """
        super(Management, self).__init__()
        self.bot = bot
        bot.tree.on_error = self.on_app_command_error

    async def on_app_command_error(
        self,
        interaction: Interaction,
        error: app_commands.AppCommandError
    ):
        if isinstance(error, discord.app_commands.errors.MissingPermissions):
            if 'administrator' in error.missing_permissions:
                await interaction.response.send_message(
                    "You do not have permission to use this command.",
                    ephemeral=True
                )
                logger.error(error)

                # Send message to log_channel if it is in use
                log_channel_id = await snorlax_db.get_guild_log_channel(interaction.guild.id)
                if log_channel_id != -1:
                    log_channel = get(interaction.guild.channels, id=int(log_channel_id))
                    embed = snorlax_logs.attempted_app_command_embed(
                        interaction.command, interaction.channel, interaction.user
                    )
                    await log_channel.send(embed=embed)
                    logger.info('Unauthorised command attempt notification sent to log channel.')

        elif isinstance(error, app_commands.CheckFailure):
            if (('manage_channels' in error.missing_permissions
                    or 'connect' in error.missing_permissions)
                    and interaction.command.name == 'create-time-channel'):
                await interaction.response.send_message(
                    (
                        "Permission error! Snorlax is missing the following permissions to create a time channel:\n"
                        f"`{', '.join(error.missing_permissions)}` (`connect` may also be required)."
                    ),
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                        "You can't use that here.",
                        ephemeral=True
                    )
        elif isinstance(error, app_commands.errors.CommandInvokeError) and "Missing Permissions" in str(error):
            await interaction.response.send_message(
                    "A permissions error has occurred. Does Snorlax have the correct permissions?",
                    ephemeral=True
                )
            logger.error(error, exc_info=True)
        else:
            await interaction.response.send_message(
                    "Unexpected error occurred, contact administrator.",
                    ephemeral=True
                )
            logger.error(type(error))
            logger.error(error, exc_info=True)

    @app_commands.command(
        name='activate-any-raids-filter',
        description=(
            "Turn on the 'any raids' filter. Filters messages containing 'any raids?'."
        ),
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.checks.has_permissions(administrator=True)
    async def activateAnyRaidsFilter(self, interaction: Interaction) -> None:
        """
        Method to activate the any raids filter on the guild.

        Args:
            interaction: The interaction triggering the request.

        Returns:
            None
        """
        any_filter = await snorlax_db.get_guild_any_raids_active(interaction.guild.id)
        if any_filter:
            msg = ("The 'any raids' filter is already activated.")
        else:
            ok = await snorlax_db.toggle_any_raids_filter(interaction.guild, True)
            if ok:
                msg = ("'Any raids' filter activated.")
            else:
                msg = (
                    "Error when attempting to activate the 'Any raids' filter"
                )

        await interaction.response.send_message(msg, ephemeral=True)

    @app_commands.command(
        name="deactivate-any-raids-filter",
        description="Turns off the 'any raids' filter."
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.checks.has_permissions(administrator=True)
    async def deactivateAnyRaidsFilter(self, interaction: Interaction):
        """
        Command to deactivate the any raids filter.

        Args:
            interaction: The interaction that triggered the request.

        Returns:
            None
        """
        any_filter = await snorlax_db.get_guild_any_raids_active(interaction.guild.id)
        if not any_filter:
            msg = ("The 'any raids' filter is already deactivated.")
        else:
            ok = await snorlax_db.toggle_any_raids_filter(interaction.guild, False)
            if ok:
                msg = ("'Any raids' filter deactivated.")
            else:
                msg = (
                    "Error when attempting to deactivate the 'Any raids' filter"
                )

        await interaction.response.send_message(msg, ephemeral=True)

    @app_commands.command(
        name='activate-join-name-filter',
        description="Turns on the 'join name' filter."
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.checks.has_permissions(administrator=True)
    async def activateJoinNameFilter(self, interaction: Interaction) -> None:
        """
        Command to activate the join name filter.

        Args:
            interaction: The interaction that triggered the request.

        Returns:
            None
        """
        join_filter = snorlax_db.get_guild_join_name_active(interaction.guild.id)
        if join_filter:
            msg = ("The 'join name' filter is already activated.")
        else:
            ok = await snorlax_db.toggle_join_name_filter(interaction.guild, True)
            if ok:
                msg = ("'Join name' filter activated.")
            else:
                msg = ("Error when attempting to activate the 'Join name' filter")

        await interaction.response.send_message(msg, ephemeral=True)

    @app_commands.command(
        name='deactivate-join-name-filter',
        description="Turns off the 'join name' filter."
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.checks.has_permissions(administrator=True)
    async def deactivateJoinNameFilter(self, interaction: Interaction) -> None:
        """
        Command to deactivate the join name filter.

        Args:
            interaction: The interaction that triggered the request.

        Returns:
            None
        """
        join_filter = snorlax_db.get_guild_join_name_active(interaction.guild.id)
        if not join_filter:
            msg = ("The 'join name' filter is already deactivated.")
        else:
            ok = await snorlax_db.toggle_join_name_filter(interaction.guild, False)
            if ok:
                msg = ("'Join name' filter deactivated.")
            else:
                msg = (
                    "Error when attempting to deactivate the 'Join name' filter"
                )

        await interaction.response.send_message(msg, ephemeral=True)

    @app_commands.command(
        name='current-time',
        description="Shows the current local time for the guild."
    )
    @app_commands.check(snorlax_checks.interaction_check_bot)
    async def currentTime(self, interaction: Interaction) -> None:
        """
        Command to ask the bot to send a message containing the current time.

        Args:
            interaction: The interaction that triggered the request.

        Returns:
            None
        """
        guild_tz = await snorlax_db.get_guild_tz(interaction.guild.id)
        the_time = get_current_time(guild_tz)
        msg = (
            "The current time is {}.".format(
                the_time.strftime("%I:%M %p %Z")
            )
        )

        await interaction.response.send_message(msg)

    @app_commands.command(
        name='ping',
        description="Get a pong!"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.checks.has_permissions(administrator=True)
    async def ping(self, interaction: Interaction) -> None:
        """
        Command to return a pong to a ping.

        Args:
            interaction: The interaction that triggered the request.

        Returns:
            None
        """
        await interaction.response.send_message("Pong!", ephemeral=True)

    @app_commands.command(
        name="set-log-channel",
        description="Set the channel for where snorlax will send log messages."
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.checks.has_permissions(administrator=True)
    async def setLogChannel(
        self,
        interaction: Interaction,
        channel: TextChannel
    ) -> None:
        """
        Sets the log channel for a guild.

        Args:
            interaction: The interaction that triggered the request.
            channel: The channel to be used as the log channel.

        Returns:
            None
        """
        guild = interaction.guild
        ok = await snorlax_db.add_guild_log_channel(guild, channel)
        if ok:
            msg = (
                "{} set as the Snorlax log channel successfully.".format(
                    channel.mention
                )
            )
        else:
            msg = (
                "Error when setting the log channel."
            )
        await interaction.response.send_message(msg, ephemeral=True)

    @app_commands.command(
        name='set-pokenav-raid-category',
        description=(
            "Sets the Pokenav raid category for the guild where Snorlax"
            " will make sure not to eat friend codes."
        ),
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.checks.has_permissions(administrator=True)
    async def setPokenavRaidCategory(
        self,
        interaction: Interaction,
        category: CategoryChannel
    ) -> None:
        """
        Sets the Pokenav raid category for a guild.

        Args:
            interaction: The interaction that triggered the request.
            category: The category to be set as the Pokenav category.

        Returns:
            None
        """
        guild = interaction.guild
        cat_name = category.name
        ok = await snorlax_db.add_guild_meowth_raid_category(guild, category)
        if ok:
            msg = (
                "**{}** set as the Pokenav raid category successfully."
                " Make sure Snorlax has the correct permissions!".format(
                    cat_name.upper()
                )
            )
        else:
            msg = (
                "Error when setting the Pokenav raid channel."
            )
        await interaction.response.send_message(msg, ephemeral=True)

    @app_commands.command(
        name='reset-pokenav-raid-category',
        description="Resets the Pokenav raid category (disables)."
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.checks.has_permissions(administrator=True)
    async def resetPokenavRaidCategory(self, interaction: Interaction) -> None:
        """
        Resets the Pokenav raid category for a guild.

        Args:
            interaction: The interaction that triggered the request.

        Returns:
            None
        """
        guild = interaction.guild
        ok = await snorlax_db.add_guild_meowth_raid_category(guild)
        if ok:
            msg = ("Pokenav raid category has been reset.")
        else:
            msg = (
                "Error when setting the Pokenav raid channel."
            )
        await interaction.response.send_message(msg, ephemeral=True)

    @app_commands.command(
        name="set-timezone",
        description=(
            "Set the timezone for the guild."
        )
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.autocomplete(tz=snorlax_autocompletes.timezones_autocomplete)
    async def setTimezone(self, interaction: Interaction, tz: str) -> None:
        """
        Sets the timezone for a guild.

        Args:
            interaction: The interaction containing the message content and other
                metadata.
            tz: The timezone in string form. Uses format from the tz database of timezones
                e.g. 'Australia/Sydney', 'America/Los_Angeles'.

        Returns:
            None
        """
        ok = await snorlax_db.add_guild_tz(interaction.guild, tz)
        if ok:
            msg = (
                "{} set as the timezone successfully.".format(
                    tz
                )
            )
        else:
            msg = (
                "Error when setting the timezone."
            )

        await interaction.response.send_message(msg)

    @commands.command(
        help=(
            "Set the prefix for the server. Must be 3 characters or less"
        ),
        brief="Set the prefix for the bot."
    )
    @app_commands.default_permissions(administrator=True)
    @commands.check(snorlax_checks.check_bot)
    @commands.check(snorlax_checks.check_admin)
    async def setPrefix(self, ctx: commands.context, prefix: str) -> None:
        """
        Sets the command prefix for a guild.

        Args:
            ctx: The command context containing the message content and other
                metadata.
            prefix: The prefix to use. Must be 3 or less characters in length.

        Returns:
            None
        """
        guild_id = ctx.guild.id

        if len(prefix) > 3:
            await ctx.send("Prefix must be 3 or less characters.")
            return

        ok = await snorlax_db.set_guild_prefix(guild_id, prefix)
        if ok:
            msg = (
                "`{}` set as the prefix for Snorlax successfully.".format(
                    prefix
                )
            )
        else:
            msg = (
                "Error when setting the prefix."
            )
        await ctx.channel.send(msg)

    @app_commands.command(
        name="show-settings",
        description=(
            "Show all the current settings for the bot and guild."
        ),
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.checks.has_permissions(administrator=True)
    async def showSettings(self, interaction: Interaction) -> None:
        """
        Shows the bot settings for the guild using an embed.

        Args:
            interaction: The interaction containing the request.

        Returns:
            None
        """
        guild_id = interaction.guild.id
        guild_db = await snorlax_db.load_guild_db()
        if guild_id not in guild_db.index:
            await interaction.response.send_message(
                "Settings have not been configured for this guild.",
                ephemeral=True
            )
        else:
            guild_settings = guild_db.loc[guild_id]
            embed = get_settings_embed(interaction, guild_settings)

            await interaction.response.send_message(embed=embed, ephemeral=True)

    @commands.command(
        help=(
            "Shutdown the bot."
        ),
        brief="Shutdown the bot."
    )
    @commands.check(snorlax_checks.check_bot)
    @commands.is_owner()
    async def shutdown(self, ctx: commands.context) -> None:
        """
        Function to force the bot to shutdown.

        Args:
            ctx: The command context containing the message content and other
                metadata.

        Returns:
            None
        """

        await ctx.channel.send(
            "Snorlax is shutting down."
        )
        await ctx.bot.close()

    @commands.Cog.listener()
    async def on_guild_join(self, guild: Guild) -> None:
        """
        Process to complete when the bot joins a new guild.

        Args:
            guild: The guild object representing the new guild.

        Returns:
            None
        """
        # check if the new guild is already in the database
        if await snorlax_checks.check_guild_exists(guild.id):
            logger.info(f'Setting guild {guild.name} to active.')
            ok = await snorlax_db.set_guild_active(guild.id, 1)
            # Then go through log_channel, time_channel, schedules
            # and raid category to see if the channels still exist. Reset or drop if they don't.
            log_channel_id = await snorlax_db.get_guild_log_channel(guild.id)
            if log_channel_id != -1:
                log_channel = get(guild.channels, id=int(log_channel_id))
                if log_channel is None:
                    logger.warning(f'Log channel not found for {guild.name}, resetting.')
                    await snorlax_db.add_guild_log_channel(guild)

            time_channel_id = await snorlax_db.get_guild_time_channel(guild.id)
            if time_channel_id != -1:
                time_channel = get(guild.channels, id=int(time_channel_id))
                if time_channel is None:
                    logger.warning(f'Time channel not found for {guild.name}, resetting.')
                    await snorlax_db.add_guild_time_channel(guild)

            raid_category_id = await snorlax_db.get_guild_raid_category(guild.id)
            if raid_category_id != -1:
                raid_category = get(guild.categories, id=int(raid_category_id))
                if raid_category is None:
                    logger.warning(f'Raid category not found for {guild.name}, resetting.')
                    await snorlax_db.add_guild_meowth_raid_category(guild)

            schedules = await snorlax_db.load_schedule_db(guild_id=guild.id)
            if not schedules.empty:
                for _, row in schedules.iterrows():
                    sched_channel_id = row['channel']
                    sched_channel = get(guild.channels, id=int(sched_channel_id))
                    if sched_channel is None:
                        logger.warning(f"Dropping schedule {row['rowid']} in {guild.name} as channel not found.")
                        ok = await snorlax_db.drop_schedule(row['rowid'])

        # if not then create the new entry in the db
        else:
            logger.info(f'Adding {guild.name} to database.')
            ok = await snorlax_db.add_guild(guild)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: Guild) -> None:
        """
        Process to complete when a guild is removed.

        Args:
            guild: The guild object representing the removed guild.

        Returns:
            None
        """
        # check if the new guild is already in the database
        if await snorlax_checks.check_guild_exists(guild.id):
            logger.info(f'Setting guild {guild.name} to not active.')
            # Set guild to inactive
            ok = await snorlax_db.set_guild_active(guild.id, 0)
            # Check for schedules and deactivate them all
            schedules = await snorlax_db.load_schedule_db(guild_id=guild.id)
            if not schedules.empty:
                logger.info(f'Deactivating all schedules for {guild.name}.')
                for rowid in schedules['rowid']:
                    ok = await snorlax_db.update_schedule(schedule_id=rowid, column='active', value=False)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: GuildChannel) -> None:
        """
        Checks on a channel deletion whether the channel was the log channel.

        Args:
            channel: The deleted channel object.

        Returns:
            None
        """
        log_channel = await snorlax_db.get_guild_log_channel(channel.guild.id)

        if log_channel == channel.id:
            await snorlax_db.add_guild_log_channel(channel.guild)
            logger.info(f'Log channel reset for guild {channel.guild.name}.')


async def setup(bot: commands.bot) -> None:
    """The setup function to initiate the cog.

    Args:
        bot: The bot for which the cog is to be added.
    """
    if bot.test_guild is not None:
        await bot.add_cog(
            Management(bot),
            guild=discord.Object(id=bot.test_guild)
        )
    else:
        await bot.add_cog(Management(bot))
