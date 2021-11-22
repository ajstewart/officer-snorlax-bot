import asyncio
import pytz
import datetime
import os
import logging

from discord import TextChannel, Reaction, User
from discord.errors import (
    DiscordServerError, Forbidden,
)
from discord.ext import commands, tasks
from discord.utils import get
from dotenv import load_dotenv, find_dotenv
from typing import Optional, Tuple
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
    update_current_delay_num,
    update_schedule
)
from .utils.log_msgs import schedule_log_embed
from .utils.utils import (
    get_current_time,
    get_schedule_embed,
    str2bool
)


# obtain the bot settings from the dotenv.
load_dotenv(find_dotenv())
DEFAULT_OPEN_MESSAGE = os.getenv('DEFAULT_OPEN_MESSAGE')
DEFAULT_CLOSE_MESSAGE = os.getenv('DEFAULT_CLOSE_MESSAGE')
WARNING_TIME = int(os.getenv('WARNING_TIME'))
INACTIVE_TIME = int(os.getenv('INACTIVE_TIME'))
DELAY_TIME = int(os.getenv('DELAY_TIME'))

logger = logging.getLogger()


class Schedules(commands.Cog):
    """
    The schedules Cog of the bot that takes care of everything to do with
    opening and closing channels.
    """
    def __init__(self, bot: commands.bot) -> None:
        """
        Init method for schedules.

        Args:
            bot: The discord.py bot representation.

        Returns:
            None.
        """
        super(Schedules, self).__init__()
        self.bot = bot

        self.channel_manager.add_exception_type(DiscordServerError, Forbidden)
        self.channel_manager.start()

    async def cog_check(self, ctx: commands.context) -> bool:
        """
        Defines the checks to perform on the received command for all the
        commands in the cog.

        Args:
            ctx: The command context containing the message content and other
                metadata.

        Returns:
            bool: True of False for whether the checks pass or fail,
                respectively.
        """
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
        help="Set a schedule to be active.",
        brief="Set a schedule to be active."
    )
    async def activateSchedule(self, ctx: commands.context, id: int) -> None:
        """
        Toggles a saved schedule to active.

        Args:
            ctx: The command context containing the message content and other
                metadata.
            id: The database id value of the schedule to be toggled.

        Returns:
            None.
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
            msg = f'You do not have permission to activate schedule {id}.'

            await ctx.channel.send(msg)

            return

        try:
            await self.updateSchedule(ctx, int(id), 'active', 'on')
        except Exception as e:
            pass

    @commands.command(
        help="Set multiple schedules to be active.",
        brief="Set multiple schedules to be active."
    )
    async def activateSchedules(
        self,
        ctx: commands.context,
        *args: int
    ) -> None:
        """
        Toggles all schedules provided to active.

        Args:
            ctx: The command context containing the message content and other
                metadata.
            id: The database id value of the schedule to be toggled.

        Returns:
            None.
        """
        for id in args:
            try:
                await self.activateSchedule(ctx, int(id))
            except Exception as e:
                pass

    @commands.command(
        help="Set all schedules to be active.",
        brief="Set all schedules to be active."
    )
    async def activateAllSchedules(self, ctx: commands.context) -> None:
        """
        Toggles all schedules to active.

        Args:
            ctx: The command context containing the message content and other
                metadata.

        Returns:
            None.
        """
        schedules = load_schedule_db(guild_id=ctx.guild.id)

        if schedules.empty:
            await ctx.send("There are no schedules to delete!")
            return

        for id in schedules['rowid'].tolist():
            try:
                await self.activateSchedule(ctx, int(id))
            except Exception as e:
                pass

    @commands.command(
        help=(
            "Create an opening and closing schedule for a channel"
            " in the guild. Times must be provided in 24 hour format"
            " e.g. '21:00'. Custom messages will appear under the"
            " default Snorlax message. Schedules created will be"
            " activated by default."
        ),
        brief="Create an opening and closing schedule for a channel."
    )
    async def createSchedule(
        self,
        ctx: commands.context,
        channel: TextChannel,
        open_time: str,
        close_time: str,
        open_message: Optional[str] = "None",
        close_message: Optional[str] = "None",
        warning: Optional[str] = "False",
        dynamic: Optional[str] = "True",
        max_num_delays: Optional[int] = 1,
        silent: Optional[str] = "False"
    ) -> None:
        """
        Method to create a channel opening and closing schedule.

        Args:
            ctx: The command context containing the message content and other
                metadata.
            channel: The Discord channel object representing the channel that
                the schedule applies to.
            open_time: The time to open the channel in 24 hour %H:%m format,
                e.g.  '06:00'.
            close_time: The time to close the channel in 24 hour %H:%m format,
                e.g. '21:00'.
            open_message: A custom message to send to the channel when it is
                opened.
            close_message: A custom message to send to the channel when it is
                closed.
            warning: Whether a closure warning should be sent to the channel.
            dynamic: Whether dynamic closing is active for the schedule.
            max_num_delays: The maximum number of times the closing of the
                channel can be delayed when using dynamic mode.
            silent: If True then no messages are sent to the channel when it is
                opened or closed.

        Returns:
            None
        """
        time_ok, f_open_time = check_time_format(open_time)
        if not time_ok:
            msg = (
                "{} is not a valid time.".format(
                    open_time
                )
            )
            await ctx.channel.send(msg)
            return
        # this just checks for single hour inputs, e.g. 6:00
        open_time = f_open_time

        time_ok, f_close_time = check_time_format(close_time)
        if not time_ok:
            msg = (
                "{} is not a valid time.".format(
                    close_time
                )
            )
            await ctx.channel.send(msg)
            return
        close_time = f_close_time

        # Replace empty strings
        if open_message == "":
            open_message = "None"

        if close_message == "":
            close_message = "None"

        # Could support different roles in future.
        role = ctx.guild.default_role

        ok, rowid = create_schedule(
            ctx.guild.id, channel.id, channel.name, role.id, role.name,
            open_time, close_time, open_message, close_message, warning,
            dynamic, max_num_delays, silent
        )

        if ok:
            msg = "Schedule set successfully."
            await self.listSchedules(ctx, schedule_id=rowid)
        else:
            msg = "Error when setting schedule."

        await ctx.channel.send(msg)

    @createSchedule.error
    async def createSchedule_error(
        self,
        ctx: commands.context,
        error
    ) -> None:
        """
        Method to pass the errors from the createSchedule method.

        Args:
            ctx: The command context containing the message content and other
                metadata.
            error (Exception): The actual exception that could be a range of
                error types.
        Returns:
            None
        """
        if isinstance(error, commands.InvalidEndOfQuotedStringError):
            msg = (
                "Error in setting schedule."
                " Were the open and close messages entered correctly?"
                f"\n```{error}```\n"
            )
            await ctx.send(msg)
        else:
            msg = (
                "Unknown error in setting schedule."
                f"\n```{error}```\n"
            )
            await ctx.send(msg)

    @commands.command(
        help="Deactivate a schedule.",
        brief="Deactivate a schedule."
    )
    async def deactivateSchedule(self, ctx: commands.context, id: int) -> None:
        """
        Toggles a saved schedule to not active.

        Args:
            ctx: The command context containing the message content and other
                metadata.
            id: The database id value of the schedule to be toggled.

        Returns:
            None.
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
            msg = f'You do not have permission to deactivate schedule {id}.'

            await ctx.channel.send(msg)

            return

        try:
            await self.updateSchedule(ctx, int(id), 'active', 'off')
        except Exception as e:
            pass

    @commands.command(
        help="Deactivate multiple schedules.",
        brief="Deactivate multiple schedules."
    )
    async def deactivateSchedules(
        self, ctx: commands.context, *args: int
    ) -> None:
        """
        Toggles the provided schedules to not active.

        Args:
            ctx: The command context containing the message content and other
                metadata.
            id: The database id values of the schedules to be toggled.

        Returns:
            None.
        """
        for id in args:
            try:
                await self.deactivateSchedule(ctx, int(id))
            except Exception as e:
                pass

    @commands.command(
        help="Deactivate all schedules.",
        brief="Deactivate all schedules."
    )
    async def deactivateAllSchedules(self, ctx: commands.context) -> None:
        """
        Toggles all saved schedules to not active on the command origin server.

        Args:
            ctx: The command context containing the message content and other
                metadata.

        Returns:
            None.
        """
        schedules = load_schedule_db(guild_id=ctx.guild.id)

        if schedules.empty:
            await ctx.send("There are no schedules to delete!")
            return

        for id in schedules['rowid'].tolist():
            try:
                await self.deactivateSchedule(ctx, int(id))
            except Exception as e:
                pass

    @commands.command(
        help=(
            "Will list all the active schedules for the"
            " guild, showing the open and close times."
        ),
        brief="Show a list of active schedules."
    )
    async def listSchedules(self, ctx, schedule_id: int = None) -> None:
        """
        A method to send a message to the command channel that contains an
        embed of all the schedules for that server.

        If a `schedule_id` is provided then only that schedule is shown.

        Args:
            ctx: The command context containing the message content and other
                metadata.
            schedule_id: Limit the output to only the provided id. If None
                then all are listed.

        Returns:
            None
        """
        schedule_db = load_schedule_db()
        if ctx.guild.id not in schedule_db['guild'].values:
            await ctx.channel.send("There are no schedules set.")
        else:
            guild_schedules = schedule_db.loc[
                schedule_db['guild'] == ctx.guild.id
            ]
            if schedule_id is not None:
                guild_schedules = guild_schedules.loc[
                    guild_schedules['rowid'] == schedule_id
                ]
            guild_db = load_guild_db()
            guild_tz = guild_db.loc[ctx.guild.id]['tz']
            embed = get_schedule_embed(
                ctx, guild_schedules, guild_tz
            )

            await ctx.channel.send(embed=embed)

    @commands.command(
        help=(
            "Remove a channel from the active schedules."
            " Use the 'id' to remove."
        ),
        brief="Remove a channel from the active schedules."
    )
    async def removeSchedule(self, ctx: commands.context, id: int) -> None:
        """
        Attempts to delete the requested schedule from the database.

        Args:
            ctx: The command context containing the message content and other
                metadata.
            id: The database id value of the schedule to be deleted.

        Returns:
            None
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
            msg = f'You do not have permission to remove schedule {id}.'

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

    @commands.command(
        help=(
            "Remove multiple schedules."
            " Use the 'id' value to remove with space in between."
            " E.g. removeSchedules 1 2 4 10"
        ),
        brief="Remove multiple schedules."
    )
    async def removeSchedules(self, ctx: commands.context, *args: int) -> None:
        """
        Attempts to delete the requested schedules from the database.

        Args:
            ctx: The command context containing the message content and other
                metadata.
            id: The database id values of the schedules to be deleted.

        Returns:
            None
        """
        for id in args:
            try:
                await self.removeSchedule(ctx, int(id))
            except Exception as e:
                pass

    @commands.command(
        help="Remove all schedules. Confirmation will be requested.",
        brief="Remove all schedules."
    )
    async def removeAllSchedules(self, ctx: commands.context) -> None:
        """
        Attempts to delete all schedules from the command origin server from
        the database.

        A confirmation message is sent to the user before performing the
        deletion.

        Args:
            ctx: The command context containing the message content and other
                metadata.

        Returns:
            None
        """
        schedules = load_schedule_db(guild_id=ctx.guild.id)

        if schedules.empty:
            await ctx.send("There are no schedules to delete!")
            return

        requester = ctx.author.id

        message = await ctx.send(
            "Are you sure you want to remove all "
            f"{schedules.shape[0]} schedules?"
        )

        emojis = ['✅', '❌']

        for emoji in (emojis):
            await message.add_reaction(emoji)

        def check(reaction: Reaction, user: User) -> Tuple[bool, bool]:
            """
            Internal method to perform the user confirmation.

            Checks that the emoji reacted with is either confirm or deny and
            that the user is the original command request user.

            Args:
                reaction: The discord reaction object.
                user: The discord user object.

            Returns:
                A tuple of bools representing the pass (True) or fail (False)
                of the two checks.
            """
            reacted = reaction.emoji
            return user.id == requester and str(reaction.emoji) in emojis

        try:
            reaction, user = await self.bot.wait_for(
                'reaction_add', timeout=10, check=check
            )
        except asyncio.TimeoutError:
            await ctx.send("Command timeout, cancelling.", delete_after=5)
            await message.delete()
        else:
            if reaction.emoji == '✅':
                for id in schedules['rowid'].tolist():
                    try:
                        await self.removeSchedule(ctx, int(id))
                    except Exception as e:
                        pass
                await message.delete()
            elif reaction.emoji == '❌':
                await ctx.send("Remove all schedules cancelled!")
                await message.delete()

    @commands.command(
        help=(
            "Updates a specific parameter of an existing schedule."
            " The columns to use are:"
            "\nopen"
            "\nclose"
            "\nopen_message"
            "\nclose_message"
            "\nwarning"
            "\ndynamic"
            "\nmax_num_delays"
            "\nsilent"
        ),
        brief=(
            "Update a parameter in an existing schedule. "
            "See full help for details."
        )
    )
    async def updateSchedule(
        self,
        ctx: commands.context,
        id: int,
        *args: str
    ) -> None:
        """
        Method to update an existing schedule.

        Options are entered as alternate keys and values, e.g., 'open 07:00
        close 21:00'.

        Args:
            ctx: The command context containing the message content and other
                metadata.
            id: The schedule id to be updated.
            args: The list of key and values of the settings to update.

        Returns:
            None
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
            msg = 'You do not have permission to update this schedule'

            await ctx.channel.send(msg)

            return

        if len(args) % 2 != 0:
            msg = 'Error! There are an odd number of columns and values!'

            await ctx.channel.send(msg)

            return

        valid_columns = [
            "active",
            "open",
            "close",
            "open_message",
            "close_message",
            "warning",
            "dynamic",
            "max_num_delays",
            "silent",
        ]

        to_update = {}

        for i in range(0, len(args), 2):
            column = args[i]
            value = args[i+1]

            if column not in valid_columns:
                 msg = (
                     "'{}' is not a valid column to update."
                     " Valid columns are: {}".format(
                         column, ", ".join(valid_columns)
                     )
                 )
                 await ctx.channel.send(msg)
                 return

            elif column in to_update:
                 msg = f"'{column}' has been entered multiple times!"
                 await ctx.channel.send(msg)
                 return

            elif column in ['open', 'close']:
                time_ok, f_value = check_time_format(value)
                if not time_ok:
                    msg = "{} is not a valid time.".format(value)
                    await ctx.channel.send(msg)
                    return
                value = f_value

            elif column == 'max_num_delays':
                value = int(value)

            elif column in ['active', 'warning', 'dynamic', 'silent']:
                value = str2bool(value)

            to_update[column] = value

        errored = False

        for column in to_update:
            ok = update_schedule(id, column, to_update[column])
            if not ok:
                errored = True
                msg = (
                    f'Error during update of schedule with ID {id} on'
                    f' column {column}. Check inputs and try again.'
                )
                await ctx.send(msg)
        if not errored:
            msg = f'Schedule ID {id} updated successfully.'
        else:
            msg = (
                f'Schedule ID {id} updated, however some columns were not.'
                'Refer to the error message above and check input.'
            )
        await ctx.channel.send(msg)
        await self.listSchedules(ctx, schedule_id=id)

    @updateSchedule.error
    async def updateSchedule_error(self, ctx: commands.context, error) -> None:
        """
        Handles any errors from updateSchedule.

        Args:
            ctx: The command context containing the message content and other
                metadata.
            error (Exception): The error passed from updateSchedule.

        Returns:
            None
        """
        msg = (
            "Unknown error in updating schedule."
            f"\n```{error}```\n"
        )
        await ctx.send(msg)

    @tasks.loop(seconds=60)
    async def channel_manager(self) -> None:
        """
        The main function that checks the open and close schedules and acts
        accordingly.

        TODO: Needs to be broken up and tidied.

        Returns:
            None
        """
        client_user = self.bot.user
        guild_db = load_guild_db(active_only=True)
        schedule_db = load_schedule_db(active_only=True)

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

                    time_channel_id = int(
                        guild_db.loc[guild_id]['time_channel']
                    )
                    if time_channel_id != -1:
                        time_format_fill = f"<#{time_channel_id}>"
                    else:
                        time_format_fill = "Unavailable"
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
                        datetime.datetime.strptime(
                            row.close, '%H:%M'
                        ).strftime('%I:%M %p'),
                        now.tzname()
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

                    warning = (
                        datetime.datetime(
                            10, 10, 10,
                            hour=int(close_hour), minute=int(close_min)
                        ) - datetime.timedelta(minutes=WARNING_TIME)
                    ).strftime("%H:%M")

                    if warning == now_compare:
                        messages = await channel.history(after=then).flatten()
                        if check_if_channel_active(messages, client_user):
                            warning_msg = (
                                "**Warning!** Snorlax is approaching! "
                                "This channel is scheduled to close in {}"
                                " minute".format(WARNING_TIME)
                            )
                            if WARNING_TIME > 1:
                                warning_msg+="s."
                            else:
                                warning_msg+="."
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
                            datetime.datetime.strptime(
                                row.open, '%H:%M'
                            ).strftime('%I:%M %p'),
                            now.tzname(),
                            time_format_fill
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
                            datetime.datetime.strptime(
                                row.open, '%H:%M'
                            ).strftime('%I:%M %p'),
                            now.tzname(),
                            time_format_fill
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
    async def before_timer(self) -> None:
        """
        Method to process before the channel manager loop is started.

        The purpose is to make sure the loop is started at the top of an even
        minute.

        Returns:
            None
        """
        await self.bot.wait_until_ready()
        # Make sure the loop starts at the top of the minute
        seconds = datetime.datetime.now().second
        sleep_time = 60 - seconds
        logger.info(
            f'Waiting {sleep_time} seconds to start the channel manager loop.'
        )

        await asyncio.sleep(sleep_time)
