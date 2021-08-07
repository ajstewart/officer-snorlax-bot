from discord.ext import commands, tasks
from typing import Optional
from .utils.checks import (
    check_admin,
    check_admin_channel,
    check_time_format,
    check_bot,
    check_if_channel_active,
    check_remove_schedule,
    check_schedule_exists
)
from .utils.db import (
    load_guild_db,
    load_schedule_db,
    create_schedule,
    drop_schedule,
    update_dynamic_close,
    update_current_delay_num
)
from discord.utils import get
from discord import TextChannel
from discord.errors import DiscordServerError, Forbidden
import asyncio
import pytz
import datetime
import os
import logging
from .utils.utils import (
    get_current_time,
    get_schedule_embed
)
from .utils.log_msgs import schedule_log_embed
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

        self.channel_manager.add_exception_type(DiscordServerError, Forbidden)
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
        warning: Optional[str] = "False", dynamic: Optional[str] = "True",
        max_num_delays: Optional[int] = 1,
        silent: Optional[str] = "False"
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
            dynamic, max_num_delays, silent
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
        exists = check_schedule_exists(id)

        if not exists:
            msg = 'Schedule ID {} does not exist!'.format(
                id
            )

            await ctx.channel.send(msg)

            return

        allowed = check_remove_schedule(ctx, id)

        if not allowed:
            msg = 'You do not have permission to remove this schedule'

            await ctx.channel.send(msg)

            return

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
        client_user = self.bot.user
        guild_db = load_guild_db(active_only=True)
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

            last_guild_id = -1

            for i,row in scheds_to_check.iterrows():
                # Load the log channel for the guild
                guild_id = row['guild']
                if guild_id != last_guild_id:
                    log_channel_id = int(guild_db.loc[guild_id]['log_channel'])
                    if log_channel_id != -1:
                        log_channel = self.bot.get_channel(log_channel_id)
                    last_guild_id = guild_id

                channel = self.bot.get_channel(row.channel)
                role = get(channel.guild.roles, id=row.role)
                # get current overwrites
                overwrites = channel.overwrites_for(role)
                allow, deny = overwrites.pair()

                if row.open == now_compare:
                    # update dynamic close in case channel never got to close
                    update_dynamic_close(row.rowid)
                    if allow.send_messages == deny.send_messages == False:
                        # this means the channel is already set to neutral
                        logger.warning(
                            f'Channel {channel.name} already neutral, skipping opening.'
                        )
                        if log_channel_id != -1:
                            embed = schedule_log_embed(
                                channel,
                                tz,
                                'open_skip'
                            )
                            await log_channel.send(embed=embed)
                        continue

                    overwrites.send_messages = None
                    await channel.set_permissions(role, overwrite=overwrites)
                    open_message = DEFAULT_OPEN_MESSAGE.format(
                        row.close, now.tzname()
                    )
                    if row['open_message'] != "None":
                        open_message += "\n\n" + row['open_message']
                    if not row.silent:
                        await channel.send(open_message)

                    logger.info(
                        f'Opened {channel.name} in {channel.guild.name}.'
                    )

                    if log_channel_id != -1:
                        embed = schedule_log_embed(
                            channel,
                            tz,
                            'open'
                        )
                        await log_channel.send(embed=embed)

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

                            if log_channel_id != -1:
                                embed = schedule_log_embed(
                                    channel,
                                    tz,
                                    'warning'
                                )
                                await log_channel.send(embed=embed)

                            await channel.send(warning_msg)
                            continue

                if row.close == now_compare:

                    if deny.send_messages is True:
                        logger.warning(
                            f'Channel {channel.name} already closed, skipping closing.'
                        )

                        if log_channel_id != -1:
                            embed = schedule_log_embed(
                                channel,
                                tz,
                                'close_skip'
                            )
                            await log_channel.send(embed=embed)

                        # Channel already closed so skip

                        continue

                    then = now_utc - datetime.timedelta(minutes=INACTIVE_TIME)

                    messages = await channel.history(after=then).flatten()

                    if (check_if_channel_active(messages, client_user)
                        and row.dynamic
                        and row.current_delay_num < row.max_num_delays
                    ):
                        new_close_time = (
                            now + datetime.timedelta(minutes=DELAY_TIME)
                        ).strftime("%H:%M")

                        update_dynamic_close(row.rowid, new_close_time=new_close_time)

                        update_current_delay_num(row.rowid, row.current_delay_num + 1)

                        if log_channel_id != -1:
                            embed = schedule_log_embed(
                                channel,
                                tz,
                                'delay',
                                DELAY_TIME,
                                row.current_delay_num + 1,
                                row.max_num_delays
                            )
                            await log_channel.send(embed=embed)

                        logger.info(
                            f'Delayed closing for {channel.name} in '
                            f'guild {channel.guild.name}.'
                        )

                        continue

                    else:
                        close_message = DEFAULT_CLOSE_MESSAGE.format(
                            row.open, now.tzname()
                        )
                        if row['close_message'] != "None":
                            close_message += "\n\n" + row['close_message']
                        if not row.silent:
                            await channel.send(close_message)
                        overwrites.send_messages = False
                        await channel.set_permissions(role, overwrite=overwrites)
                        update_dynamic_close(row.rowid)
                        update_current_delay_num(row.rowid)

                        if log_channel_id != -1:
                            embed = schedule_log_embed(
                                channel,
                                tz,
                                'close'
                            )
                            await log_channel.send(embed=embed)

                        logger.info(
                            f'Channel {channel.name} closed in guild'
                            f' {channel.guild.name}.'
                        )

                if row.dynamic_close == now_compare:

                    if deny.send_messages is True:
                        # Channel already closed so skip
                        update_dynamic_close(row.rowid)
                        logger.warning(
                            f'Channel {channel.name} already closed in guild'
                            f' {channel.guild.name}, skipping closing.'
                        )

                        if log_channel_id != -1:
                            embed = schedule_log_embed(
                                channel,
                                tz,
                                'close_skip'
                            )
                            await log_channel.send(embed=embed)

                        continue

                    then = now_utc - datetime.timedelta(minutes=INACTIVE_TIME)

                    messages = await channel.history(after=then).flatten()

                    if (check_if_channel_active(messages, client_user)
                        and row.current_delay_num < row.max_num_delays):
                        new_close_time = (
                            now + datetime.timedelta(minutes=DELAY_TIME)
                        ).strftime("%H:%M")

                        update_dynamic_close(row.rowid, new_close_time=new_close_time)

                        update_current_delay_num(row.rowid, row.current_delay_num + 1)

                        if log_channel_id != -1:
                            embed = schedule_log_embed(
                                channel,
                                tz,
                                'delay',
                                DELAY_TIME,
                                row.current_delay_num + 1,
                                row.max_num_delays
                            )
                            await log_channel.send(embed=embed)

                        logger.info(
                            f'Delayed closing for {channel.name} in '
                            f'guild {channel.guild.name}.'
                        )

                        if row.current_delay_num + 1 == row.max_num_delays:
                            warning_msg = (
                                "**Warning!** Snorlax is approaching! "
                                "This channel will close in {}"
                                " minutes.".format(DELAY_TIME)
                            )

                            await channel.send(warning_msg)

                        continue

                    else:
                        update_dynamic_close(row.rowid)
                        update_current_delay_num(row.rowid)
                        close_message = DEFAULT_CLOSE_MESSAGE.format(
                            row.open, now.tzname()
                        )
                        if row['close_message'] != "None":
                            close_message += "\n\n" + row['close_message']

                        if not row.silent:
                            await channel.send(close_message)
                        overwrites.send_messages = False
                        await channel.set_permissions(role, overwrite=overwrites)

                        if log_channel_id != -1:
                            embed = schedule_log_embed(
                                channel,
                                tz,
                                'close'
                            )
                            await log_channel.send(embed=embed)

                        logger.info(
                            f'Channel {channel.name} closed in guild'
                            f' {channel.guild.name}.'
                        )

    @channel_manager.before_loop
    async def before_timer(self):
        await self.bot.wait_until_ready()
        # Make sure the loop starts at the top of the minute
        seconds = datetime.datetime.now().second
        sleep_time = 60 - seconds
        logger.info(
            f'Waiting {sleep_time} seconds to start the channel manager loop.'
        )

        await asyncio.sleep(sleep_time)

