from discord.ext import commands, tasks
from discord import TextChannel
from typing import Optional
import os
from .utils.db import (
    load_guild_db,
    add_guild_admin_channel,
    add_guild_tz,
)
from .utils.utils import get_current_time
from .utils.checks import (
    check_admin_channel, check_admin, check_valid_timezone, check_bot
)


DEFAUL_TZ = os.getenv('DEFAULT_TZ')


class Management(commands.Cog):
    """docstring for Management"""
    def __init__(self, bot):
        super(Management, self).__init__()
        self.bot = bot

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
    async def setAdminChannel(self, ctx, channel: TextChannel, tz=DEFAUL_TZ):
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