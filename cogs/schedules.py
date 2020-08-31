from discord.ext import commands, tasks
from typing import Optional
from .utils.checks import (
    check_admin,
    check_admin_channel,
    check_time_format,
    check_bot,
    check_if_channel_active
)
from .utils.db import (
    load_guild_db,
    load_schedule_db,
    create_schedule,
    drop_schedule,
    update_dynamic_close
)
from discord.utils import get
from discord import TextChannel
import pytz
import datetime
import os
import logging
from .utils.utils import (
    get_current_time,
    get_schedule_embed
)
from dotenv import load_dotenv, find_dotenv


load_dotenv(find_dotenv())
DEFAULT_OPEN_MESSAGE = os.getenv('DEFAULT_OPEN_MESSAGE')
DEFAULT_CLOSE_MESSAGE = os.getenv('DEFAULT_CLOSE_MESSAGE')
WARNING_TIME = int(os.getenv('WARNING_TIME'))
INACTIVE_TIME = int(os.getenv('INACTIVE_TIME'))
DELAY_TIME = int(os.getenv('DELAY_TIME'))

logger = logging.getLogger()


class Schedules(commands.Cog):
    """docstring for Schedules"""
    def __init__(self, bot):
        super(Schedules, self).__init__()
        self.bot = bot

        self.channel_manager.start()

    async def cog_check(self, ctx):
        admin_check = check_admin(ctx)
        channel_check = check_admin_channel(
            ctx
        )
        bot_check = check_bot(
            ctx
        )

        if not bot_check:
            return False

        if admin_check and channel_check:
            return True
        else:
            return False

    @commands.command(
        help=(
            "Create an opening and closing schedule for a channel"
            " in the guild. Times must be provided in 24 hour format"
            " e.g. '21:00'. Custom messages will appear under the"
            " default Snorlax message."
        ),
        brief="Create an opening and closing schedule for a channel."
    )
    async def addSchedule(
        self, ctx, channel: TextChannel, open_time: str, close_time: str,
        open_message: Optional[str] = "None",
        close_message: Optional[str] = "None",
        warning: Optional[str] = "False", dynamic: Optional[str] = "True"
    ):
        """
        Docstring goes here.
        """
        if not check_time_format(open_time):
            msg = (
                "{} is not a valid time.".format(
                    open_time
                )
            )
            await ctx.channel.send(msg)
            return

        if not check_time_format(close_time):
            msg = (
                "{} is not a valid time.".format(
                    close_time
                )
            )
            await ctx.channel.send(msg)
            return

        ok = create_schedule(
            ctx, channel, open_time, close_time,
            open_message, close_message, warning,
            dynamic
        )

        if ok:
            msg = "Schedule set successfully."
        else:
            msg = "Error when setting schedule."

        await ctx.channel.send(msg)

    @commands.command(
        help=(
            "Will list all the active schedules for the"
            " guild, showing the open and close times."
        ),
        brief="Show a list of active schedules."
    )
    async def listSchedules(self, ctx):
        """
        Docstring goes here.
        """
        schedule_db = load_schedule_db()
        if ctx.guild.id not in schedule_db['guild'].values:
            await ctx.channel.send("There are no schedules set.")
        else:
            guild_schedules = schedule_db.loc[
                schedule_db['guild'] == ctx.guild.id
            ]
            guild_db = load_guild_db()
            guild_tz = guild_db.loc[ctx.guild.id]['tz']
            embed = get_schedule_embed(ctx, guild_schedules, guild_tz)

            await ctx.channel.send(embed=embed)

    @commands.command(
        help=(
            "Remove a channel from the active schedules."
            " Use the 'id' to remove."
        ),
        brief="Remove a channel from the active schedules."
    )
    async def removeSchedule(self, ctx, id: int):
        """
        Docstring goes here.
        """
        ok = drop_schedule(ctx, id)

        if ok:
            msg = 'Schedule ID {} removed successfully.'.format(
                id
            )
        else:
            msg = 'Error during removal of schedule with ID {}.'.format(
                id
            )

        await ctx.channel.send(msg)

    @tasks.loop(seconds=60)
    async def channel_manager(self):
        await self.bot.wait_until_ready()

        client_user = self.bot.user
        guild_db = load_guild_db()
        schedule_db = load_schedule_db()

        for tz in guild_db['tz'].unique():
            now = get_current_time(tz=tz)
            now_utc = datetime.datetime.utcnow()
            now_compare = now.strftime(
                "%H:%M"
            )
            guilds = guild_db.loc[guild_db['tz'] == tz].index.values

            guild_mask = [
                g in guilds for g in schedule_db['guild'].values
            ]

            scheds_to_check = schedule_db.loc[guild_mask, :]

            for i,row in scheds_to_check.iterrows():
                channel = self.bot.get_channel(row.channel)
                role = get(channel.guild.roles, id=row.role)
                allow, deny = channel.overwrites_for(role).pair()

                if row.open == now_compare:
                    # update dynamic close in case channel never got to close
                    update_dynamic_close(row.rowid)
                    if allow.send_messages == deny.send_messages == False:
                        # this means the channel is already set to neutral
                        logger.warning(
                            f'Channel {channel.name} already neutral, skipping opening.'
                        )
                        continue
                    await channel.set_permissions(role, send_messages=None)
                    open_message = DEFAULT_OPEN_MESSAGE.format(
                        row.close
                    )
                    if row['open_message'] != "None":
                        open_message += "\n\n" + row['open_message']
                    await channel.send(open_message)

                    continue

                close_hour, close_min = row.close.split(":")

                if row.warning:
                    then = now_utc - datetime.timedelta(minutes=INACTIVE_TIME)

                    messages = await channel.history(after=then).flatten()

                    if check_if_channel_active(
                        messages, client_user
                    ):
                        warning = (
                            datetime.datetime(
                                10, 10, 10,
                                hour=int(close_hour), minute=int(close_min)
                            ) - datetime.timedelta(minutes=WARNING_TIME)
                        ).strftime("%H:%M")

                        if warning == now_compare:
                            warning_msg = (
                                "**Warning!** Snorlax is approaching! "
                                "This channel is scheduled to close in {}"
                                " minutes.".format(WARNING_TIME)
                            )
                            if row.dynamic:
                                warning_msg += (
                                    "\n\nIf the channel is still active then"
                                    " closing will be delayed."
                                )

                            await channel.send(warning_msg)
                            continue

                if row.close == now_compare:

                    if deny.send_messages is True:
                        logger.warning(
                            f'Channel {channel.name} already closed, skipping closing.'
                        )
                        # Channel already closed so skip

                        continue

                    then = now_utc - datetime.timedelta(minutes=INACTIVE_TIME)

                    messages = await channel.history(after=then).flatten()

                    if check_if_channel_active(
                        messages, client_user
                    ):
                        new_close_time = (
                            now + datetime.timedelta(minutes=DELAY_TIME)
                        ).strftime("%H:%M")

                        update_dynamic_close(row.rowid, new_close_time=new_close_time)
                        continue

                    else:
                        close_message = DEFAULT_CLOSE_MESSAGE.format(
                            row.open
                        )
                        if row['close_message'] != "None":
                            close_message += "\n\n" + row['close_message']
                        await channel.send(close_message)
                        await channel.set_permissions(role, send_messages=False)

                if row.dynamic_close == now_compare:

                    if deny.send_messages is True:
                        # Channel already closed so skip
                        update_dynamic_close(row.rowid)
                        logger.warning(
                            f'Channel {channel.name} already closed, skipping closing.'
                        )
                        continue

                    then = now_utc - datetime.timedelta(minutes=INACTIVE_TIME)

                    messages = await channel.history(after=then).flatten()

                    if check_if_channel_active(
                        messages, client_user
                    ):

                        new_close_time = (
                            now + datetime.timedelta(minutes=DELAY_TIME)
                        ).strftime("%H:%M")

                        update_dynamic_close(row.rowid, new_close_time=new_close_time)
                        continue

                    else:
                        update_dynamic_close(row.rowid)
                        close_message = DEFAULT_CLOSE_MESSAGE.format(
                            row.open
                        )
                        if row['close_message'] != "None":
                            close_message += "\n\n" + row['close_message']
                        await channel.send(close_message)
                        await channel.set_permissions(role, send_messages=False)
