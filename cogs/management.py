"""
The management cog which contains commands related to the management
and set up of the bot.
"""

import discord
import os
import logging

from discord import Guild, TextChannel
from discord.ext import commands
from dotenv import load_dotenv, find_dotenv

from .utils.db import (
    load_guild_db,
    add_guild_admin_channel,
    add_guild_log_channel,
    add_guild_tz,
    add_guild_meowth_raid_category,
    toggle_any_raids_filter,
    toggle_join_name_filter,
    set_guild_active,
    add_guild,
    set_guild_prefix
)
from .utils.embeds import get_settings_embed
from .utils.utils import get_current_time
from .utils.checks import (
    check_admin_channel,
    check_admin,
    check_valid_timezone,
    check_bot,
    check_guild_exists
)


logger = logging.getLogger()
load_dotenv(find_dotenv())
DEFAULT_TZ = os.getenv('DEFAULT_TZ')


class Management(commands.Cog):
    """
    Cog for the management commands.

    All commands (apart from setting the admin channel) must be requested
    from the designated guild admin channel.
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

    @commands.command(
        help=(
            "Turn on the 'any raids' filter. If a user sends a message that"
            " just containts 'any raids?' it will be deleted."
        ),
        brief="Turns on the 'any raids' filter."
    )
    @commands.check(check_bot)
    @commands.check(check_admin_channel)
    @commands.check(check_admin)
    async def activateAnyRaidsFilter(self, ctx: commands.context) -> None:
        """
        Method to activate the any raids filter on the guild.

        Args:
            ctx: The command context containing the message content and other
                metadata.

        Returns:
            None
        """
        guild_db = load_guild_db()
        any_filter = guild_db.loc[ctx.guild.id]['any_raids_filter']
        if any_filter:
            msg = ("The 'any raids' filter is already activated.")
        else:
            ok = toggle_any_raids_filter(ctx.guild, True)
            if ok:
                msg = ("'Any raids' filter activated.")
            else:
                msg = (
                    "Error when attempting to activate the 'Any raids' filter"
                )

        await ctx.channel.send(msg)

    @commands.command(
        help=(
            "Turn off the 'any raids' filter."
        ),
        brief="Turns off the 'any raids' filter."
    )
    @commands.check(check_bot)
    @commands.check(check_admin_channel)
    @commands.check(check_admin)
    async def deactivateAnyRaidsFilter(self, ctx: commands.context):
        """
        Command to deactivate the any raids filter.

        Args:
            ctx: The command context containing the message content and other
                metadata.

        Returns:
            None
        """
        guild_db = load_guild_db()
        any_filter = guild_db.loc[ctx.guild.id]['any_raids_filter']
        if not any_filter:
            msg = ("The 'any raids' filter is already deactivated.")
        else:
            ok = toggle_any_raids_filter(ctx.guild, False)
            if ok:
                msg = ("'Any raids' filter deactivated.")
            else:
                msg = (
                    "Error when attempting to deactivate the 'Any raids' filter"
                )

        await ctx.channel.send(msg)

    @commands.command(
        help=(
            "Turn on the 'join name' filter. If a user joins a server with a "
            "name that is on the ban list then Snorlax will ban them."
        ),
        brief="Turns on the 'join name' filter."
    )
    @commands.check(check_bot)
    @commands.check(check_admin_channel)
    @commands.check(check_admin)
    async def activateJoinNameFilter(self, ctx: commands.context) -> None:
        """
        Command to activate the join name filter.

        Args:
            ctx: The command context containing the message content and other
                metadata.

        Returns:
            None
        """
        guild_db = load_guild_db()
        any_filter = guild_db.loc[ctx.guild.id]['join_name_filter']
        if any_filter:
            msg = ("The 'join name' filter is already activated.")
        else:
            ok = toggle_join_name_filter(ctx.guild, True)
            if ok:
                msg = ("'Join name' filter activated.")
            else:
                msg = ("Error when attempting to activate the 'Join name' filter")

        await ctx.channel.send(msg)

    @commands.command(
        help=(
            "Turn off the 'join name' filter."
        ),
        brief="Turns off the 'join name' filter."
    )
    @commands.check(check_bot)
    @commands.check(check_admin_channel)
    @commands.check(check_admin)
    async def deactivateJoinNameFilter(self, ctx: commands.context) -> None:
        """
        Command to deactivate the join name filter.

        Args:
            ctx: The command context containing the message content and other
                metadata.

        Returns:
            None
        """
        guild_db = load_guild_db()
        any_filter = guild_db.loc[ctx.guild.id]['join_name_filter']
        if not any_filter:
            msg = ("The 'join name' filter is already deactivated.")
        else:
            ok = toggle_join_name_filter(ctx.guild, False)
            if ok:
                msg = ("'Join name' filter deactivated.")
            else:
                msg = (
                    "Error when attempting to deactivate the 'Join name' filter"
                )

        await ctx.channel.send(msg)

    @commands.command(
        help=(
            "Will print the current time for the guild."
        ),
        brief="Shows the current time for the guild."
    )
    @commands.check(check_bot)
    @commands.check(check_admin_channel)
    @commands.check(check_admin)
    async def currentTime(self, ctx: commands.context) -> None:
        """
        Command to ask the bot to send a message containing the current time.

        Args:
            ctx: The command context containing the message content and other
                metadata.

        Returns:
            None
        """
        guild_db = load_guild_db()
        tz = guild_db.loc[ctx.guild.id]['tz']
        the_time = get_current_time(tz)
        msg = (
            "The current time is {}.".format(
                the_time.strftime("%H:%M")
            )
        )

        await ctx.channel.send(msg)

    @commands.command(
        help=(
            "Receive a pong from the bot."
        ),
        brief="Get a pong."
    )
    @commands.check(check_bot)
    @commands.check(check_admin_channel)
    @commands.check(check_admin)
    async def ping(self, ctx: commands.context) -> None:
        """
        Command to return a pong to a ping.

        Args:
            ctx: The command context containing the message content and other
                metadata.

        Returns:
            None
        """
        await ctx.channel.send("pong")

    @commands.command(
        help=(
            "Sets the command channel for the guild where Snorlax"
            " will listen for commands. This is the only command that"
            " can be run from any channel."
        ),
        brief="Set the command channel for the bot."
    )
    @commands.check(check_bot)
    @commands.check(check_admin)
    async def setAdminChannel(
        self,
        ctx: commands.context,
        channel: TextChannel
    ) -> None:
        """
        Sets the admin channel for a guild.

        Args:
            ctx: The command context containing the message content and other
                metadata.
            channel: The channel to be used as the admin channel.

        Returns:
            None
        """
        guild = ctx.guild
        ok = add_guild_admin_channel(guild, channel)
        if ok:
            msg = (
                "{} set as the Snorlax admin channel successfully."
                " Make sure Snorlax has the correct permissions!".format(
                    channel.mention
                )
            )
        else:
            msg = (
                "Error when setting the admin channel."
            )
        await ctx.channel.send(msg)

    @commands.command(
        help=(
            "Sets the log channel for the guild where Snorlax"
            " will post log messages."
        ),
        brief="Set the log channel for the bot."
    )
    @commands.check(check_bot)
    @commands.check(check_admin_channel)
    @commands.check(check_admin)
    async def setLogChannel(
        self,
        ctx: commands.context,
        channel: TextChannel
    ) -> None:
        """
        Sets the log channel for a guild.

        Args:
            ctx: The command context containing the message content and other
                metadata.
            channel: The channel to be used as the log channel.

        Returns:
            None
        """
        guild = ctx.guild
        ok = add_guild_log_channel(guild, channel)
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
        await ctx.channel.send(msg)

    @commands.command(
        help=(
            "Sets the Meowth raid category for the guild where Snorlax"
            " will make sure not to eat friend codes in dynamically created"
            " channels."
        ),
        brief="Set the meowth raid categry for the bot."
    )
    @commands.check(check_bot)
    @commands.check(check_admin_channel)
    @commands.check(check_admin)
    async def setMeowthRaidCategory(
        self,
        ctx: commands.context,
        category_id: int = -1
    ) -> None:
        """
        Sets the Meowth/Pokenav raid category for a guild.

        Args:
            ctx: The command context containing the message content and other
                metadata.
            channel: The category to be set as the meowth category.

        Returns:
            None
        """
        guild = ctx.guild
        channel = guild.get_channel(category_id)
        if channel is None:
            ok = False
        else:
            cat_name = channel.name
            ok = add_guild_meowth_raid_category(guild, channel)
        if ok:
            msg = (
                "**{}** set as the Meowth raid category successfully."
                " Make sure Snorlax has the correct permissions!".format(
                    cat_name.upper()
                )
            )
        else:
            msg = (
                "Error when setting the meowth raid channel."
            )
        await ctx.channel.send(msg)

    @commands.command(
        help=(
            "Resets the Meowth raid category for the guild. Essentially"
            " disabling the Meowth raid channel support."
        ),
        brief="Reset the meowth raid categry for the bot (disables)."
    )
    @commands.check(check_bot)
    @commands.check(check_admin_channel)
    @commands.check(check_admin)
    async def resetMeowthRaidCategory(self, ctx: commands.context) -> None:
        """
        Resets the Meowth/Pokenav raid category for a guild.

        Args:
            ctx: The command context containing the message content and other
                metadata.

        Returns:
            None
        """
        guild = ctx.guild
        ok = add_guild_meowth_raid_category(guild, -1)
        if ok:
            msg = ("Meowth raid category has been reset.")
        else:
            msg = (
                "Error when setting the meowth raid channel."
            )
        await ctx.channel.send(msg)

    @commands.command(
        help=(
            "Set the timezone for the guild. Use standard tz"
            " timezones, e.g. 'Australia/Sydney'."
        ),
        brief="Set the timezone for the guild."
    )
    @commands.check(check_bot)
    @commands.check(check_admin_channel)
    @commands.check(check_admin)
    async def setTimezone(self, ctx: commands.context, tz: str) -> None:
        """
        Sets the timezone for a guild.

        Args:
            ctx: The command context containing the message content and other
                metadata.
            tz: The timezone in string form, e.g. 'Australia/Sydney'.

        Returns:
            None
        """
        if not check_valid_timezone(tz):
            msg = '{} is not a valid timezone'.format(
                tz
            )
        else:
            ok = add_guild_tz(ctx.guild, tz)
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
        await ctx.channel.send(msg)

    @commands.command(
        help=(
            "Set the prefix for the server. Must be 3 characters or less"
        ),
        brief="Set the prefix for the bot."
    )
    @commands.check(check_bot)
    @commands.check(check_admin_channel)
    @commands.check(check_admin)
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

        ok = set_guild_prefix(guild_id, prefix)
        if ok:
            msg = (
                "{} set as the prefix for Snorlax successfully.".format(
                    prefix
                )
            )
        else:
            msg = (
                "Error when setting the prefix."
            )
        await ctx.channel.send(msg)

    @commands.command(
        help=(
            "Show all the current settings for the bot"
            " and guild."
        ),
        brief="Show all settings"
    )
    @commands.check(check_bot)
    @commands.check(check_admin_channel)
    @commands.check(check_admin)
    async def showSettings(self, ctx: commands.context) -> None:
        """
        Shows the bot settings for the guild using an embed.

        Args:
            ctx: The command context containing the message content and other
                metadata.

        Returns:
            None
        """
        guild_db = load_guild_db()
        if ctx.guild.id not in guild_db.index:
            await ctx.channel.send(
                "Settings have not been configured for this guild."
            )
        else:
            guild_settings = guild_db.loc[ctx.guild.id]
            embed = get_settings_embed(ctx, guild_settings)

            await ctx.channel.send(embed=embed)

    @commands.command(
        help=(
            "Shutdown the bot."
        ),
        brief="Shutdown the bot."
    )
    @commands.check(check_bot)
    @commands.check(check_admin_channel)
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
        await ctx.bot.logout()

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
        if check_guild_exists(guild.id):
            logger.info(f'Setting guild {guild.name} to active.')
            ok = set_guild_active(guild.id, 1)
        # if not then create the new entry in the db
        else:
            logger.info(f'Adding {guild.name} to database.')
            ok = add_guild(guild)

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
        if check_guild_exists(guild.id):
            logger.info(f'Setting guild {guild.name} to not active.')
            ok = set_guild_active(guild.id, 0)


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
