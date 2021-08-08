import os
import logging

from typing import Optional
from discord import TextChannel
from discord.ext import commands, tasks
from .utils.db import (
    load_guild_db,
    add_guild_admin_channel,
    add_guild_log_channel,
    add_guild_tz,
    add_guild_meowth_raid_category,
    toggle_any_raids_filter,
    toggle_join_name_filter,
    set_guild_active,
    add_guild
)
from .utils.utils import get_current_time, get_settings_embed
from .utils.checks import (
    check_admin_channel, check_admin, check_valid_timezone, check_bot,
    check_guild_exists
)
from dotenv import load_dotenv, find_dotenv

logger = logging.getLogger()
load_dotenv(find_dotenv())
DEFAULT_TZ = os.getenv('DEFAULT_TZ')


class Management(commands.Cog):
    """docstring for Management"""
    def __init__(self, bot):
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
    async def activateAnyRaidsFilter(self, ctx):
        """
        Docstring goes here.
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
                msg = ("Error when attempting to activate the 'Any raids' filter")

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
    async def deactivateAnyRaidsFilter(self, ctx):
        """
        Docstring goes here.
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
                msg = ("Error when attempting to deactivate the 'Any raids' filter")

        await ctx.channel.send(msg)


    @commands.command(
        help=(
            "Turn on the 'join name' filter. If a user joins a server with a name"
            " that is on the ban list then Snorlax will ban them."
        ),
        brief="Turns on the 'join name' filter."
    )
    @commands.check(check_bot)
    @commands.check(check_admin_channel)
    @commands.check(check_admin)
    async def activateJoinNameFilter(self, ctx):
        """
        Docstring goes here.
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
    async def deactivateJoinNameFilter(self, ctx):
        """
        Docstring goes here.
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
                msg = ("Error when attempting to deactivate the 'Join name' filter")

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
    async def currentTime(self, ctx):
        """
        Docstring goes here.
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
    async def ping(self, ctx):
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
    async def setAdminChannel(self, ctx, channel: TextChannel, tz=DEFAULT_TZ):
        """
        Docstring goes here.
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
    @commands.check(check_admin)
    async def setLogChannel(self, ctx, channel: TextChannel):
        """
        Docstring goes here.
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
    @commands.check(check_admin)
    async def setMeowthRaidCategory(
        self, ctx, category_id: int=-1):
        """
        Docstring goes here.
        """
        guild = ctx.guild
        channel = guild.get_channel(category_id)
        if channel == None:
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
    @commands.check(check_admin)
    async def resetMeowthRaidCategory(self, ctx):
        """
        Docstring goes here.
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
    async def setTimezone(self, ctx, tz: str):
        """
        Docstring goes here.
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
            "Show all the current settings for the bot"
            " and guild."
        ),
        brief="Show all settings"
    )
    @commands.check(check_bot)
    @commands.check(check_admin_channel)
    @commands.check(check_admin)
    async def showSettings(self, ctx):
        """
        Docstring goes here.
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
    async def shutdown(self, ctx):
        """
        Function to force the bot to shutdown.
        """

        await ctx.channel.send(
            "Snorlax is shutting down."
        )
        await ctx.bot.logout()

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        """
        Process to complete when a guild is joined.
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
    async def on_guild_remove(self, guild):
        """
        Process to complete when a guild is removed.
        """
        # check if the new guild is already in the database
        if check_guild_exists(guild.id):
            logger.info(f'Setting guild {guild.name} to not active.')
            ok = set_guild_active(guild.id, 0)
