import asyncio
import datetime
import discord
import os
import logging

from discord import TextChannel, User, Role, PermissionOverwrite, Interaction
from discord.errors import (
    DiscordServerError, Forbidden,
)
from discord.ext import commands, tasks
from discord.utils import get
from dotenv import load_dotenv, find_dotenv
from typing import Optional

from .utils import checks as snorlax_checks
from .utils import db as snorlax_db
from .utils import embeds as snorlax_embeds
from .utils.db import (
    load_guild_db,
    load_schedule_db,
    create_schedule,
    drop_schedule,
    update_dynamic_close,
    update_current_delay_num,
    update_schedule,
)
from .utils.log_msgs import schedule_log_embed
from .utils.utils import (
    get_current_time,
    str2bool,
)


# obtain the bot settings from the dotenv.
load_dotenv(find_dotenv())
DEFAULT_OPEN_MESSAGE = os.getenv('DEFAULT_OPEN_MESSAGE')
DEFAULT_CLOSE_MESSAGE = os.getenv('DEFAULT_CLOSE_MESSAGE')
WARNING_TIME = int(os.getenv('WARNING_TIME'))
INACTIVE_TIME = int(os.getenv('INACTIVE_TIME'))
DELAY_TIME = int(os.getenv('DELAY_TIME'))

logger = logging.getLogger()


# Define a simple View that gives us a confirmation menu
class RemoveAllConfirm(discord.ui.View):
    """This View is used for the confirmation of the removeAllSchedules command.

    Users will confirm or cancel the command. Only responds to the original author.
    Note that the initial response message should be attached to the class when used!

    Attributes:
        value (Optional[bool]): Whether the interaction is complete (True) or not (False).
            None indicates a timeout.
        user (Discord.User): The original author of the command who the view will only respond to.
    """
    def __init__(self, user: User, timeout: int = 60) -> None:
        """Init function of the view.

        Args:
            user: The original author of the command who the view will only respond to.
            timeout: How long, in seconds, the view will remain active for.
        """
        super().__init__(timeout=timeout)
        self.value = None
        self.user = user

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(label='Confirm', style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        """The confirm button of the view.

        The value attribute is set to True when used and the view is stopped.

        Args:
            interaction: The interaction instance.
            button: The button instance.
        """
        await interaction.response.send_message('Confirmed!', ephemeral=True)
        self.value = True
        await self.disable_children()
        self.stop()

    # This one is similar to the confirmation button except sets the inner value to `False`
    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.grey)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        """The cancel button of the view.

        The value attribute is set to False when used and the view is stopped.

        Args:
            interaction: The interaction instance.
            button: The button instance.
        """
        await interaction.response.send_message('Cancelled!', ephemeral=True)
        self.value = False
        await self.disable_children()
        self.stop()

    async def disable_children(self, timeout_label: bool = False) -> None:
        """Loops through the view children and disables the components.

        The response must have been attached to the view!

        Args:
            timeout_label: If True, the label of button components will be replaced with 'Timeout!'.
        """
        for child in self.children:
            child.disabled = True
            if timeout_label:
                child.label = "Timeout!"

        await self.response.edit(view=self)

    async def on_timeout(self) -> None:
        """Disable the buttons of the view in the event of a timeout.
        """
        await self.disable_children(timeout_label=True)

    async def interaction_check(self, interaction: Interaction) -> bool:
        """The interaction check for the view.

        Checks whether the interaction user is the initial command user. A response is sent if this is not the case.

        Args:
            interaction: The interaction instance.

        Returns:
            Whether the check has passed (True) or not (False).
        """
        check_pass = self.user.id == interaction.user.id

        if not check_pass:
            await interaction.response.send_message("You do not have permission to do that!", ephemeral=True)

        return check_pass


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
        admin_check = snorlax_checks.check_admin(ctx)
        channel_check = await snorlax_checks.check_admin_channel(ctx)
        bot_check = snorlax_checks.check_bot(ctx)

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
        exists = await snorlax_checks.check_schedule_exists(id)

        if not exists:
            msg = 'Schedule ID {} does not exist!'.format(
                id
            )

            await ctx.channel.send(msg)

            return

        allowed = await snorlax_checks.check_remove_schedule(ctx, id)

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
        schedules = await load_schedule_db(guild_id=ctx.guild.id)

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
        time_ok, f_open_time = snorlax_checks.check_time_format(open_time)
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

        time_ok, f_close_time = snorlax_checks.check_time_format(close_time)
        if not time_ok:
            msg = (
                "{} is not a valid time.".format(
                    close_time
                )
            )
            await ctx.channel.send(msg)
            return
        close_time = f_close_time

        if close_time == open_time:
            msg = "The open and close time cannot be the same!"
            await ctx.channel.send(msg)
            return

        # Replace empty strings
        if open_message == "":
            open_message = "None"

        if close_message == "":
            close_message = "None"

        # Could support different roles in future.
        role = ctx.guild.default_role

        ok, rowid = await create_schedule(
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
        elif isinstance(error, commands.CheckFailure):
            pass
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
        exists = await snorlax_checks.check_schedule_exists(id)

        if not exists:
            msg = 'Schedule ID {} does not exist!'.format(
                id
            )

            await ctx.channel.send(msg)

            return

        allowed = await snorlax_checks.check_remove_schedule(ctx, id)

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
        schedules = await load_schedule_db(guild_id=ctx.guild.id)

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
        schedule_db = await load_schedule_db()
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
            guild_db = await load_guild_db()
            guild_tz = guild_db.loc[ctx.guild.id]['tz']
            embed = snorlax_embeds.get_schedule_embed(guild_schedules, guild_tz)

            await ctx.channel.send(embed=embed)

    @commands.command(
        help=(
            "Provides the ability to manually close a channel at any time."
            " Normal close settings will apply and the channel will open"
            " again at the scheduled time (unless manually opened earlier)."
            " Only works on channels with an active schedule."
        ),
        brief="Manually close a channel."
    )
    async def manualClose(
        self,
        ctx: commands.context,
        channel: TextChannel,
        silent: bool = False
    ) -> None:
        """
        A command to manually close a channel.

        Args:
            ctx: The command context containing the message content and other
                metadata.
            channel: The channel to be closed.
            silent: Whether to close the channel silently.

        Returns:
            None
        """
        # check if in schedule
        # check if already closed
        # close
        schedule_db = await load_schedule_db(active_only=True)
        if channel.id not in schedule_db['channel'].to_numpy():
            await ctx.channel.send("That channel has no schedule set.")

            return

        # Grab the schedule row
        row = schedule_db[schedule_db['channel'] == channel.id].iloc[0]

        guild_db = await load_guild_db()
        guild_tz = guild_db.loc[ctx.guild.id]['tz']

        log_channel_id = int(guild_db.loc[ctx.guild.id]['log_channel'])
        if log_channel_id != -1:
            log_channel = self.bot.get_channel(log_channel_id)
        else:
            log_channel = None
        time_channel_id = int(
            guild_db.loc[ctx.guild.id]['time_channel']
        )
        if time_channel_id != -1:
            time_format_fill = f"<#{time_channel_id}>"
        else:
            time_format_fill = "Unavailable"

        role = get(channel.guild.roles, id=row.role)
        # get current overwrites
        overwrites = channel.overwrites_for(role)
        allow, deny = overwrites.pair()

        if deny.send_messages is True:
            # this means the channel is already closed
            await ctx.channel.send(f"{channel.mention} is already closed!")

            return

        await self.close_channel(
            channel,
            role,
            overwrites,
            row['open'],
            row['close_message'],
            silent,
            log_channel,
            guild_tz,
            time_format_fill,
            row['rowid'],
            self.bot.user
        )

        await ctx.channel.send(f"Closed {channel.mention}!")

    @manualClose.error
    async def manualClose_error(self, ctx: commands.context, error):
        """
        Handles any errors from manualClose.

        Args:
            ctx: The command context containing the message content and other
                metadata.
            error (Exception): The error passed from manualClose.

        Returns:
            None
        """
        if isinstance(error, commands.ChannelNotFound):
            await ctx.channel.send(f"{error}")
        elif isinstance(error, commands.CheckFailure):
            pass
        else:
            await ctx.channel.send(
                f"Unknown error when processing command: {error}"
            )

    @commands.command(
        help=(
            "Provides the ability to manually open a channel at any time."
            " Normal open settings will apply and the channel will close"
            " at the scheduled time (unless manually closed earlier)."
            " Only works on channels with an active schedule."
        ),
        brief="Manually open a channel."
    )
    async def manualOpen(
        self,
        ctx: commands.context,
        channel: TextChannel,
        silent: bool = False
    ) -> None:
        """
        A command to manually close a channel.

        Args:
            ctx: The command context containing the message content and other
                metadata.
            channel: The channel to be opened.
            silent: Whether to open the channel silently.

        Returns:
            None
        """
        # check if in schedule
        # check if already open
        # open
        schedule_db = await load_schedule_db()
        if channel.id not in schedule_db['channel'].to_numpy():
            await ctx.channel.send("That channel has no schedule set.")

            return

        # Grab the schedule row
        row = schedule_db[schedule_db['channel'] == channel.id].iloc[0]

        guild_db = await load_guild_db()
        guild_tz = guild_db.loc[ctx.guild.id]['tz']

        log_channel_id = int(guild_db.loc[ctx.guild.id]['log_channel'])
        if log_channel_id != -1:
            log_channel = self.bot.get_channel(log_channel_id)
        else:
            log_channel = None

        time_channel_id = int(
            guild_db.loc[ctx.guild.id]['time_channel']
        )
        if time_channel_id != -1:
            time_format_fill = f"<#{time_channel_id}>"
        else:
            time_format_fill = "Unavailable"

        role = get(channel.guild.roles, id=row.role)
        # get current overwrites
        overwrites = channel.overwrites_for(role)
        allow, deny = overwrites.pair()

        if allow.send_messages == deny.send_messages is False:
            # this means the channel is already open
            await ctx.channel.send(f"{channel.mention} is already open!")

            return

        await self.open_channel(
            channel,
            role,
            overwrites,
            row['close'],
            row['open_message'],
            silent,
            log_channel,
            guild_tz,
            time_format_fill,
            self.bot.user
        )

        await ctx.channel.send(f"Opened {channel.mention}!")

    @manualOpen.error
    async def manualOpen_error(self, ctx: commands.context, error) -> None:
        """
        Handles any errors from manualOpen.

        Args:
            ctx: The command context containing the message content and other
                metadata.
            error (Exception): The error passed from manualOpen.

        Returns:
            None
        """
        if isinstance(error, commands.ChannelNotFound):
            await ctx.channel.send(f"{error}")
        elif isinstance(error, commands.CheckFailure):
            pass
        else:
            await ctx.channel.send(
                f"Unknown error when processing command: {error}"
            )

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
        exists = await snorlax_checks.check_schedule_exists(id)

        if not exists:
            msg = 'Schedule ID {} does not exist!'.format(
                id
            )

            await ctx.channel.send(msg)

            return

        allowed = await snorlax_checks.check_remove_schedule(ctx, id)

        if not allowed:
            msg = f'You do not have permission to remove schedule {id}.'

            await ctx.channel.send(msg)

            return

        ok = await drop_schedule(ctx, id)

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

        A confirmation interaction is sent to the user before performing the
        deletion.

        Args:
            ctx: The command context containing the message content and other
                metadata.

        Returns:
            None
        """
        schedules = await load_schedule_db(guild_id=ctx.guild.id)

        if schedules.empty:
            await ctx.send("There are no schedules to delete!")
            return

        view = RemoveAllConfirm(ctx.author, timeout=30)

        out = await ctx.send(
            "Are you sure you want to remove all "
            f"{schedules.shape[0]} schedules?",
            view=view
        )

        view.response = out

        await view.wait()

        if view.value is None:
            logger.info("removeAllSchedules command timeout.")
        elif view.value:
            for id in schedules['rowid'].tolist():
                try:
                    await self.removeSchedule(ctx, int(id))
                except Exception as e:
                    pass
        else:
            logger.info("removeAllSchedules command cancelled.")

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
        exists = await snorlax_checks.check_schedule_exists(id)

        if not exists:
            msg = 'Schedule ID {} does not exist!'.format(
                id
            )

            await ctx.channel.send(msg)

            return

        allowed = await snorlax_checks.check_remove_schedule(ctx, id)

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
                time_ok, f_value = snorlax_checks.check_time_format(value)
                if not time_ok:
                    msg = "{} is not a valid time.".format(value)
                    await ctx.channel.send(msg)
                    return

                if column == 'open':
                    if 'close' in to_update:
                        if f_value == to_update['close']:
                            msg = "The open and close time cannot be the same!"
                            await ctx.channel.send(msg)
                            return

                elif column == 'close':
                    if 'open' in to_update:
                        if f_value == to_update['open']:
                            msg = "The open and close time cannot be the same!"
                            await ctx.channel.send(msg)
                            return

                value = f_value

            elif column == 'max_num_delays':
                value = int(value)

            elif column in ['active', 'warning', 'dynamic', 'silent']:
                value = str2bool(value)

            to_update[column] = value

        # Check if one or the other is in to_update, already checked the case
        # where both are to be updated above
        if sum(('open' in to_update, 'close' in to_update)) == 1:
            if 'open' in to_update:
                curr_close = await snorlax_db.get_schedule_close(id)
                the_same = curr_close == to_update['open']

            elif 'close' in to_update:
                curr_open = await snorlax_db.get_schedule_open(id)
                the_same = curr_open == to_update['close']

            if the_same:
                msg = "The open and close time cannot be the same!"
                await ctx.channel.send(msg)
                return

        errored = False

        for column in to_update:
            ok = await update_schedule(id, column, to_update[column])
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
        if isinstance(error, commands.CheckFailure):
            pass
        else:
            msg = (
                "Unknown error in updating schedule."
                f"\n```{error}```\n"
            )
            await ctx.send(msg)

    async def close_channel(
        self,
        channel: TextChannel,
        role: Role,
        overwrites: PermissionOverwrite,
        open: str,
        custom_close_message: str,
        silent: bool,
        log_channel: Optional[TextChannel],
        tz: str,
        time_format_fill: str,
        rowid: int,
        client_user: User
    ) -> None:
        """
        The opening channel process.

        Args:
            channel: The channel to be closed.
            role: The role to apply the toggle to.
            overwrites: The channel overwrites for the role.
            open: The open time of the channel from its schedule.
            custom_close_message: The custom close message to add to the
                default message.
            silent: Whether to close silently.
            log_channel: The guild log channel.
            tz: Guild timezone as a string.
            time_format_fill: The string to fill in the opening time in the
                open message.
            rowid: The id of the schedule so the delay time can be reset.
            client_user: The bot user instance.

        Returns:
            None
        """
        now = get_current_time(tz=tz)

        close_embed = snorlax_embeds.get_close_embed(
            open,
            now,
            custom_close_message,
            client_user,
            time_format_fill
        )

        if not silent:
            await channel.send(embed=close_embed)

        overwrites.send_messages = False
        overwrites.send_messages_in_threads = False

        await channel.set_permissions(role, overwrite=overwrites)

        await update_dynamic_close(rowid)
        await update_current_delay_num(rowid)

        if log_channel is not None:
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

    async def open_channel(
        self,
        channel: TextChannel,
        role: Role,
        overwrites: PermissionOverwrite,
        close: str,
        custom_open_message: str,
        silent: bool,
        log_channel: Optional[TextChannel],
        tz: str,
        time_format_fill: str,
        client_user: User
    ) -> None:
        """
        The opening channel process.

        Args:
            channel: The channel to be opened.
            role: The role to apply the toggle to.
            overwrites: The channel overwrites for the role.
            close: The close time of the channel from its schedule.
            custom_open_message: The custom open message to add to the
                default message.
            silent: Whether to open silently.
            log_channel: The guild log channel.
            tz: Guild timezone as a string.
            time_format_fill: The string to fill in the closing time in the
                open message.
            client_user: The bot user instance.

        Returns:
            None
        """
        now = get_current_time(tz=tz)
        overwrites.send_messages = None
        overwrites.send_messages_in_threads = None
        await channel.set_permissions(role, overwrite=overwrites)

        open_embed = snorlax_embeds.get_open_embed(
            close,
            now,
            custom_open_message,
            client_user,
            time_format_fill
        )

        if not silent:
            await channel.send(embed=open_embed)

        logger.info(
            f'Opened {channel.name} in {channel.guild.name}.'
        )

        if log_channel is not None:
            embed = schedule_log_embed(
                channel,
                tz,
                'open'
            )
            await log_channel.send(embed=embed)

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
        guild_db = await load_guild_db(active_only=True)
        schedule_db = await load_schedule_db(active_only=True)

        for tz in guild_db['tz'].unique():
            now = get_current_time(tz=tz)
            now_utc = discord.utils.utcnow()
            now_compare = now.strftime(
                "%H:%M"
            )
            guilds = guild_db.loc[guild_db['tz'] == tz].index.values

            guild_mask = [
                g in guilds for g in schedule_db['guild'].values
            ]

            scheds_to_check = schedule_db.loc[guild_mask, :]

            last_guild_id = -1

            for _, row in scheds_to_check.iterrows():
                # Load the log channel for the guild
                guild_id = row['guild']
                if guild_id != last_guild_id:
                    log_channel_id = int(guild_db.loc[guild_id]['log_channel'])
                    if log_channel_id != -1:
                        log_channel = self.bot.get_channel(log_channel_id)
                    else:
                        log_channel = None

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
                    await update_dynamic_close(row.rowid)
                    if allow.send_messages == deny.send_messages is False:
                        # this means the channel is already set to neutral
                        logger.warning(
                            f'Channel {channel.name} already neutral, skipping opening.'
                        )
                        if log_channel is not None:
                            embed = schedule_log_embed(
                                channel,
                                tz,
                                'open_skip'
                            )
                            await log_channel.send(embed=embed)
                        continue

                    await self.open_channel(
                        channel,
                        role,
                        overwrites,
                        row['close'],
                        row['open_message'],
                        row['silent'],
                        log_channel,
                        tz,
                        time_format_fill,
                        client_user
                    )

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
                        messages = [message async for message in channel.history(after=then)]
                        if snorlax_checks.check_if_channel_active(messages, client_user):
                            warning_embed = snorlax_embeds.get_warning_embed(
                                row['close'],
                                now_utc,
                                client_user,
                                time_format_fill,
                                row['dynamic'],
                                False
                            )

                            await channel.send(embed=warning_embed)

                            if log_channel is not None:
                                embed = schedule_log_embed(
                                    channel,
                                    tz,
                                    'warning'
                                )
                                await log_channel.send(embed=embed)

                            continue

                if row.close == now_compare:

                    if deny.send_messages is True:
                        logger.warning(
                            f'Channel {channel.name} already closed, skipping closing.'
                        )

                        if log_channel is not None:
                            embed = schedule_log_embed(
                                channel,
                                tz,
                                'close_skip'
                            )
                            await log_channel.send(embed=embed)

                        # Channel already closed so skip

                        continue

                    then = now_utc - datetime.timedelta(minutes=INACTIVE_TIME)

                    messages = [message async for message in channel.history(after=then)]

                    if (
                        snorlax_checks.check_if_channel_active(messages, client_user)
                        and row.dynamic
                        and row.current_delay_num < row.max_num_delays
                    ):
                        new_close_time = (
                            now + datetime.timedelta(minutes=DELAY_TIME)
                        ).strftime("%H:%M")

                        await update_dynamic_close(row.rowid, new_close_time=new_close_time)
                        await update_current_delay_num(row.rowid, row.current_delay_num + 1)

                        if log_channel is not None:
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
                        await self.close_channel(
                            channel,
                            role,
                            overwrites,
                            row['open'],
                            row['close_message'],
                            row['silent'],
                            log_channel,
                            tz,
                            time_format_fill,
                            row['rowid'],
                            client_user
                        )

                if row.dynamic_close == now_compare:

                    if deny.send_messages is True:
                        # Channel already closed so skip
                        await update_dynamic_close(row.rowid)
                        logger.warning(
                            f'Channel {channel.name} already closed in guild'
                            f' {channel.guild.name}, skipping closing.'
                        )

                        if log_channel is not None:
                            embed = schedule_log_embed(
                                channel,
                                tz,
                                'close_skip'
                            )
                            await log_channel.send(embed=embed)

                        continue

                    then = now_utc - datetime.timedelta(minutes=INACTIVE_TIME)

                    messages = [message async for message in channel.history(after=then)]

                    if (
                        snorlax_checks.check_if_channel_active(messages, client_user)
                        and row.current_delay_num < row.max_num_delays
                    ):
                        new_close_time = (
                            now + datetime.timedelta(minutes=DELAY_TIME)
                        ).strftime("%H:%M")

                        await update_dynamic_close(row.rowid, new_close_time=new_close_time)
                        await update_current_delay_num(row.rowid, row.current_delay_num + 1)

                        if log_channel is not None:
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
                            warning_embed = snorlax_embeds.get_warning_embed(
                                row['dynamic_close'],
                                now_utc,
                                client_user,
                                time_format_fill,
                                False,
                                True
                            )

                            await channel.send(embed=warning_embed)

                        continue

                    else:
                        await self.close_channel(
                            channel,
                            role,
                            overwrites,
                            row['open'],
                            row['close_message'],
                            row['silent'],
                            log_channel,
                            tz,
                            time_format_fill,
                            row['rowid'],
                            client_user
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


async def setup(bot: commands.bot) -> None:
    """The setup function to initiate the cog.

    Args:
        bot: The bot for which the cog is to be added.
    """
    if bot.test_guild is not None:
        await bot.add_cog(
            Schedules(bot),
            guild=discord.Object(id=bot.test_guild)
        )
    else:
        await bot.add_cog(Schedules(bot))
