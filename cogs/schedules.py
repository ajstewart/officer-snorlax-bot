import asyncio
import datetime
import discord
import os
import logging

from discord import app_commands
from discord.errors import DiscordServerError, Forbidden
from discord.abc import GuildChannel
from discord.ext import commands, tasks
from discord.utils import get
from dotenv import load_dotenv, find_dotenv
from typing import Optional

from .utils import checks as snorlax_checks
from .utils import db as snorlax_db
from .utils import embeds as snorlax_embeds
from .utils import log_msgs as snorlax_log
from .utils import utils as snorlax_utils
from .utils import autocompletes as snorlax_autocompletes
from .utils import select_options as snorlax_options
from .utils import views as snorlax_views


# obtain the bot settings from the dotenv.
load_dotenv(find_dotenv())
DEFAULT_OPEN_MESSAGE = os.getenv('DEFAULT_OPEN_MESSAGE')
DEFAULT_CLOSE_MESSAGE = os.getenv('DEFAULT_CLOSE_MESSAGE')
WARNING_TIME = int(os.getenv('WARNING_TIME'))
INACTIVE_TIME = int(os.getenv('INACTIVE_TIME'))
DELAY_TIME = int(os.getenv('DELAY_TIME'))

logger = logging.getLogger()


@app_commands.default_permissions(administrator=True)
class Schedules(commands.GroupCog, name='schedules'):
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
        bot_check = snorlax_checks.check_bot(ctx)

        if not bot_check:
            return False

        if admin_check:
            return True
        else:
            return False

    @app_commands.command(
        name='activate-schedule',
        description="Set a schedule to be active.",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.check(snorlax_checks.check_admin_channel)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.autocomplete(schedule=snorlax_autocompletes.schedule_selection_autocomplete)
    async def activateSchedule(self, interaction: discord.Interaction, schedule: str) -> None:
        """
        Toggles a saved schedule to active.

        Args:
            interaction: The interaction that triggered the request.
            schedule: The schedule to activate. Type the name of the channel to find your schedule.

        Returns:
            None.
        """
        try:
            schedule = int(schedule)
        except Exception as e:
            await interaction.response.send_message(
                f"'{schedule}' is not a valid schedule. Please select a schedule from the options provided.",
                ephemeral=True
            )
            logger.error(f'Failed activate schedule attempt in {interaction.guild.name}: {e}.')
            return

        # TODO: Move this check sequence to checks. It is used often.
        exists = await snorlax_checks.check_schedule_exists(schedule)

        if not exists:
            msg = 'That schedule does not exist!'

            await interaction.response.send_message(msg)

            return

        allowed = await snorlax_checks.check_remove_schedule(interaction, schedule)

        if not allowed:
            msg = f'You do not have permission to activate schedule {schedule}.'

            await interaction.response.send_message(msg)

            return

        ok = await snorlax_db.update_schedule(schedule, 'active', True)
        if ok:
            await interaction.response.send_message('Schedule activated successfully.')
        else:
            await interaction.response.send_message('Schedule activation failed.')

    @app_commands.command(
        name='activate-schedules',
        description="Set multiple schedules to activate at once.",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.check(snorlax_checks.check_admin_channel)
    @app_commands.checks.has_permissions(administrator=True)
    async def activateSchedules(
        self,
        interaction: discord.Interaction
    ) -> None:
        """
        Toggles all schedules provided to active.

        Args:
            interaction: The interaction that triggered the request.

        Returns:
            None.
        """
        options = await snorlax_options.schedule_options(guild=interaction.guild, active=False)

        if not options:
            await interaction.response.send_message('All schedules are already active!')

            return

        view = snorlax_views.ScheduleDropdownView(
            user=interaction.user,
            options=options,
            context='activate',
            timeout=120
        )

        await interaction.response.defer()

        out = await interaction.channel.send(view=view)

        view.response = out

        await view.wait()

        if view.values is None:
            logger.info("activate-schedules command timeout.")
            await interaction.followup.send("activate-schedules command timed out.")
        else:
            all_ok = True
            for id in view.values:
                ok = await snorlax_db.update_schedule(id, 'active', True)
                if not ok and all_ok:
                    all_ok = False
            if all_ok:
                await interaction.followup.send(f"Activated {len(view.values)} schedules successfully.")
            else:
                await interaction.followup.send(f"Activation failed.")

    @app_commands.command(
        name='activate-all',
        description="Set all schedules to active.",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.check(snorlax_checks.check_admin_channel)
    @app_commands.checks.has_permissions(administrator=True)
    async def activateAllSchedules(self, interaction: discord.Interaction) -> None:
        """
        Toggles all schedules to active.

        Args:
            interaction: The interaction that triggered the request.

        Returns:
            None.
        """
        schedules = await snorlax_db.load_schedule_db(guild_id=interaction.guild.id, active=False)

        if schedules.empty:
            await interaction.response.send_message("All schedules are active already!")
            return

        all_ok = True
        for id in schedules['rowid'].tolist():
            ok = await snorlax_db.update_schedule(id, 'active', True)
            if not ok and all_ok:
                all_ok = False
        if all_ok:
            await interaction.response.send_message(f"Activated {len(schedules)} schedules successfully.")
        else:
            await interaction.response.send_message(f"Activation failed.")

    @app_commands.command(
        name='create-schedule',
        description="Create an open, close schedule for a channel.",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.checks.has_permissions(administrator=True)
    async def createSchedule(
        self,
        interaction: discord.Interaction,
        open_time: str,
        close_time: str,
        channel: Optional[discord.TextChannel] = None,
        open_message: Optional[str] = None,
        close_message: Optional[str] = None,
        warning: Optional[bool] = False,
        dynamic: Optional[bool] = False,
        max_num_delays: app_commands.Range[int, 0, 10] = 0,
        silent: Optional[bool] = False
    ) -> None:
        """
        Method to create a channel opening and closing schedule.

        Args:
            interaction: The interaction that triggered the request.
            open_time: The time to open the channel in 24 hour %H:%m format,
                e.g. `06:00`.
            close_time: The time to close the channel in 24 hour %H:%m format,
                e.g. `21:00`.
            channel: The Discord channel that the schedule should apply to.
                Defaults to the current channel.
            open_message: A custom message to send to the channel when it is
                opened.
            close_message: A custom message to send to the channel when it is
                closed.
            warning: Whether a closure warning message should be sent to the channel.
            dynamic: Whether dynamic closing is active for the schedule. I.e. if the channel
                still has activity (as per the guild inactive setting), the channel closing will
                be delayed.
            max_num_delays: The maximum number of times the closing of the
                channel can be delayed when using dynamic mode.
            silent: If True then no messages are sent to the channel when it is
                opened or closed.

        Returns:
            None
        """
        # Get the current channel if not passed.
        if channel is None:
            channel = get(interaction.guild.channels, id=interaction.channel.id)
            ephemeral = True
        else:
            await snorlax_checks.check_admin_channel(interaction)
            ephemeral = False

        time_ok, f_open_time = snorlax_checks.check_time_format(open_time)
        if not time_ok:
            msg = f"{open_time} is not a valid time."
            await interaction.response.send_message(msg)
            return

        # this just checks for single hour inputs, e.g. 6:00
        open_time = f_open_time

        time_ok, f_close_time = snorlax_checks.check_time_format(close_time)
        if not time_ok:
            msg = f"{close_time} is not a valid time."
            await interaction.response.send_message(msg, ephemeral=ephemeral)
            return

        close_time = f_close_time

        if close_time == open_time:
            msg = "The open and close time cannot be the same!"
            await interaction.response.send_message(msg, ephemeral=ephemeral)
            return

        if await snorlax_db.check_schedule_exists_with_times(channel.id, open_time, close_time):
            msg = "That schedule already exists!"
            await interaction.response.send_message(msg, ephemeral=ephemeral)
            return

        # Replace empty strings
        if open_message == "":
            open_message = "None"

        if close_message == "":
            close_message = "None"

        # Give bot permission to always send messages to channel
        bot_role = interaction.guild.self_role
        await channel.set_permissions(
            bot_role,
            send_messages=True,
            view_channel=True,
            read_messages=True,
            read_message_history=True
        )

        # Could support different roles in future.
        role = interaction.guild.default_role

        ok, rowid = await snorlax_db.create_schedule(
            interaction.guild.id, channel.id, channel.name, role.id, role.name,
            open_time, close_time, open_message, close_message, warning,
            dynamic, max_num_delays, silent
        )

        if ok:
            msg = f"Schedule for {channel.mention} created successfully!"
            schedule_df = await snorlax_db.load_schedule_db(rowid=rowid)

            no_effect_roles_allow, no_effect_roles_deny = await snorlax_checks.check_schedule_overwrites(
                channel,
                self.bot.user
            )

            overwrite_roles = len(no_effect_roles_allow + no_effect_roles_deny)

            embed = snorlax_embeds.get_schedule_embed(schedule_df, num_warning_roles=overwrite_roles)

            await interaction.response.send_message(msg, embed=embed, ephemeral=ephemeral)
        else:
            await interaction.response.send_message("Error when creating the schedule!", ephemeral=ephemeral)

    @app_commands.command(
        name='deactivate-schedule',
        description="Set a schedule to be deactivated.",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.check(snorlax_checks.check_admin_channel)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.autocomplete(schedule=snorlax_autocompletes.schedule_selection_autocomplete)
    async def deactivateSchedule(self, interaction: discord.Interaction, schedule: str) -> None:
        """Toggles a saved schedule to deactivated.

        Args:
            interaction: The interaction that triggered the request.
            schedule: The schedule to activate. Type the name of the channel to find your schedule.

        Returns:
            None.
        """
        try:
            schedule = int(schedule)
        except Exception as e:
            await interaction.response.send_message(
                f"'{schedule}' is not a valid schedule. Please select a schedule from the options provided.",
                ephemeral=True
            )
            logger.error(f'Failed deactivate schedule attempt in {interaction.guild.name}: {e}.')
            return

        exists = await snorlax_checks.check_schedule_exists(schedule)

        if not exists:
            msg = f'Schedule ID {schedule} does not exist!'

            await interaction.response.send_message(msg)

            return

        allowed = await snorlax_checks.check_remove_schedule(interaction, schedule)

        if not allowed:
            msg = f'You do not have permission to deactivate schedule {schedule}.'

            await interaction.response.send_message(msg)

            return

        ok = await snorlax_db.update_schedule(schedule, 'active', False)
        if ok:
            await interaction.response.send_message('Schedule deactivated successfully.')
        else:
            await interaction.response.send_message('Schedule deactivation failed.')

    @app_commands.command(
        name='deactivate-schedules',
        description="Set multiple schedules to deactivated at once.",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.check(snorlax_checks.check_admin_channel)
    @app_commands.checks.has_permissions(administrator=True)
    async def deactivateSchedules(self, interaction: discord.Interaction) -> None:
        """
        Toggles the provided schedules to not active.

        Args:
            interaction: The interaction that triggered the request.

        Returns:
            None.
        """
        options = await snorlax_options.schedule_options(guild=interaction.guild, active=True)

        if not options:
            await interaction.response.send_message('All schedules are already deactivated!')

            return

        view = snorlax_views.ScheduleDropdownView(
            user=interaction.user,
            options=options,
            context='deactivate',
            timeout=120
        )

        await interaction.response.defer()

        out = await interaction.channel.send(view=view)

        view.response = out

        await view.wait()

        if view.values is None:
            logger.info("deactivate-schedules command timeout.")
            await interaction.followup.send("deactivate-schedules command timed out.")
        else:
            all_ok = True
            for id in view.values:
                ok = await snorlax_db.update_schedule(id, 'active', False)
                if not ok and all_ok:
                    all_ok = False
            if all_ok:
                await interaction.followup.send(f"Deactivated {len(view.values)} schedules successfully.")
            else:
                await interaction.followup.send(f"Deactivation failed.")

    @app_commands.command(
        name='deactivate-all',
        description="Set all schedules to deactivated.",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.check(snorlax_checks.check_admin_channel)
    @app_commands.checks.has_permissions(administrator=True)
    async def deactivateAllSchedules(self, interaction: discord.Interaction) -> None:
        """
        Toggles all schedules to deactivated.

        Args:
            interaction: The interaction that triggered the request.

        Returns:
            None.
        """
        schedules = await snorlax_db.load_schedule_db(guild_id=interaction.guild.id, active=True)

        if schedules.empty:
            await interaction.response.send_message("All schedules are deactivated already!")
            return

        all_ok = True
        for id in schedules['rowid'].tolist():
            ok = await snorlax_db.update_schedule(id, 'active', False)
            if not ok and all_ok:
                all_ok = False
        if all_ok:
            await interaction.response.send_message(f"Deactivated {len(schedules)} schedules successfully.")
        else:
            await interaction.response.send_message(f"Deactivation failed.")

    @app_commands.command(
        name='manual-close',
        description=(
            "Manually close a channel early. The channel must have an active schedule"
            " for the command to work!"
        ),
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.checks.bot_has_permissions(manage_roles=True)
    async def manualClose(
        self,
        interaction: discord.Interaction,
        channel: Optional[discord.TextChannel] = None,
        silent: bool = False
    ) -> None:
        """
        A command to manually close a channel.

        Args:
            interaction: The interaction that triggered the request.
            channel: The channel to be closed, defaults to current channel.
            silent: Whether to close the channel silently.

        Returns:
            None
        """
        if channel is None:
            channel = get(interaction.guild.channels, id=interaction.channel.id)

        # Allow this to be used outside the admin channel but hide response if it is.
        ephemeral = interaction.channel.id != await snorlax_db.get_guild_admin_channel(interaction.guild.id)

        # check if in schedule
        # check if already closed
        # close
        schedule_db = await snorlax_db.load_schedule_db(active=True)
        if channel.id not in schedule_db['channel'].to_numpy():
            await interaction.response.send_message("That channel has no active schedule set.", ephemeral=True)

            return

        # Grab the schedule row
        row = schedule_db[schedule_db['channel'] == channel.id].iloc[0]

        guild_db = await snorlax_db.load_guild_db()
        guild_tz = guild_db.loc[interaction.guild.id]['tz']

        log_channel_id = int(guild_db.loc[interaction.guild.id]['log_channel'])
        if log_channel_id != -1:
            log_channel = self.bot.get_channel(log_channel_id)
        else:
            log_channel = None
        time_channel_id = int(
            guild_db.loc[interaction.guild.id]['time_channel']
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
            await interaction.response.send_message(f"{channel.mention} is already closed!", ephemeral=True)

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

        await interaction.response.send_message(f"Closed {channel.mention}!", ephemeral=ephemeral)

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

    @app_commands.command(
        name='manual-open',
        description=(
            "Manually open a channel early. The channel must have an active schedule"
            " for the command to work!"
        ),
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.checks.bot_has_permissions(manage_roles=True)
    async def manualOpen(
        self,
        interaction: discord.Interaction,
        channel: Optional[discord.TextChannel] = None,
        silent: bool = False
    ) -> None:
        """
        A command to manually close a channel.

        Args:
            interaction: The interaction that triggered the request.
            channel: The channel to be closed, defaults to current channel.
            silent: Whether to open the channel silently.

        Returns:
            None
        """
        if channel is None:
            channel = get(interaction.guild.channels, id=interaction.channel.id)

        # Allow this to be used outside the admin channel but hide response if it is.
        ephemeral = interaction.channel.id != await snorlax_db.get_guild_admin_channel(interaction.guild.id)

        # check if in schedule
        # check if already open
        # open
        schedule_db = await snorlax_db.load_schedule_db()
        if channel.id not in schedule_db['channel'].to_numpy():
            await interaction.response.send_message("That channel has no schedule set.", ephemeral=True)

            return

        # Grab the schedule row
        row = schedule_db[schedule_db['channel'] == channel.id].iloc[0]

        guild_db = await snorlax_db.load_guild_db()
        guild_tz = guild_db.loc[interaction.guild.id]['tz']

        log_channel_id = int(guild_db.loc[interaction.guild.id]['log_channel'])
        if log_channel_id != -1:
            log_channel = self.bot.get_channel(log_channel_id)
        else:
            log_channel = None

        time_channel_id = int(
            guild_db.loc[interaction.guild.id]['time_channel']
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
            await interaction.response.send_message(f"{channel.mention} is already open!", ephemeral=True)

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

        await interaction.response.send_message(f"Opened {channel.mention}!", ephemeral=ephemeral)

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

    @app_commands.command(
        name='delete-schedule',
        description="Delete the selected schedule.",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.check(snorlax_checks.check_admin_channel)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.autocomplete(schedule=snorlax_autocompletes.schedule_selection_autocomplete)
    async def deleteSchedule(self, interaction: discord.Interaction, schedule: str) -> None:
        """Deletes the requested schedule.

        Args:
            interaction: The interaction that triggered the request.
            schedule: The schedule to view, start typing the name of the channel narrow down the
                options.

        Returns:
            None
        """
        try:
            schedule = int(schedule)
        except Exception as e:
            await interaction.response.send_message(
                f"'{schedule}' is not a valid schedule. Please select a schedule from the options provided.",
                ephemeral=True
            )
            logger.error(f'Failed view schedule attempt in {interaction.guild.name}: {e}.')
            return

        exists = await snorlax_checks.check_schedule_exists(schedule)

        if not exists:
            msg = f'That schedule does not exist!'

            await interaction.response.send_message(msg)

            return

        allowed = await snorlax_checks.check_remove_schedule(interaction, schedule)

        if not allowed:
            msg = f'That schedule does not exist!'

            await interaction.response.send_message(msg)

            return

        await interaction.response.defer()

        schedule_df = await snorlax_db.load_schedule_db(rowid=schedule)
        schedule_channel_id = schedule_df.iloc[0]['channel']

        view = snorlax_views.Confirm(interaction.user, timeout=30)

        embed = snorlax_embeds.get_schedule_embed(schedule_df)

        out = await interaction.channel.send(
            f"Are you sure you want to delete the schedule for <#{schedule_channel_id}>?",
            view=view,
            embed=embed
        )

        view.response = out

        await view.wait()

        if view.value is None:
            logger.info(f"Deletion request timeout in guild {interaction.guild.name}.")
            msg = "delete-schedule command timed out."
        elif view.value:
            ok = await snorlax_db.drop_schedule(schedule)
            if ok:
                msg = f'<#{schedule_channel_id}> schedule deleted successfully.'
                logger.info(f'Schedule {schedule} deleted in guild {interaction.guild.name}.')
            else:
                msg = f'Error ocurred while attempting to delete the <#{schedule_channel_id}> schedule!.'
                logger.error(f'Schedule {schedule} delete failed in guild {interaction.guild.name}!')
        else:
            msg = "delete-schedule command cancelled."

        await interaction.followup.send(msg)

    @app_commands.command(
        name='delete-schedules',
        description="Select multiple schedules to be deleted.",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.check(snorlax_checks.check_admin_channel)
    @app_commands.checks.has_permissions(administrator=True)
    async def deleteSchedules(self, interaction: discord.Interaction) -> None:
        """
        Deletes the schedules selected by the user. A maximum of 25 schedules can be shown.

        Args:
            interaction: The interaction that triggered the request.

        Returns:
            None.
        """
        options = await snorlax_options.schedule_options(guild=interaction.guild, active=None)

        if not options:
            await interaction.response.send_message('There are no schedules to delete!')

            return

        view = snorlax_views.ScheduleDropdownView(
            user=interaction.user,
            options=options,
            context='delete',
            timeout=60
        )

        await interaction.response.defer()

        out = await interaction.channel.send(view=view)

        view.response = out

        await view.wait()

        if view.values is None:
            logger.info("delete-schedules command timeout.")
            await interaction.followup.send("deactivate-schedules command timed out.")
        else:
            # Get schedules for embed.
            schedules_to_delete = [int(schedule) for schedule in view.values]
            schedules_db = await snorlax_db.load_schedule_db(guild_id=interaction.guild.id)
            schedules_db = schedules_db.loc[schedules_db['rowid'].isin(schedules_to_delete)]

            embed = snorlax_embeds.get_schedule_embed(schedules_db)

            confirm_view = snorlax_views.Confirm(user=interaction.user)

            confirm_out = await interaction.channel.send(
                f"Are you sure you want to delete the {len(schedules_to_delete)} selected schedules?",
                view=confirm_view,
                embed=embed
            )

            confirm_view.response = confirm_out

            await confirm_view.wait()

            if confirm_view.value is None:
                logger.info(f"Deletion request timeout in guild {interaction.guild.name}.")
                msg = "delete-schedules command timed out."
            elif confirm_view.value:
                all_ok = True
                for schedule_id in schedules_to_delete:
                    ok = await snorlax_db.drop_schedule(schedule_id)
                    if ok:
                        logger.info(f'Schedule {schedule_id} deleted in guild {interaction.guild.name}.')
                    else:
                        logger.error(f'Schedule {schedule_id} delete failed in guild {interaction.guild.name}!')
                        all_ok = False

                if all_ok:
                    msg = f"{len(schedules_to_delete)} schedules deleted successfully."
                else:
                    msg = "An error was encountered while deleting the schedules."

                # Send feedback to the user in the channel as this can be a long message with many schedules.
                await interaction.channel.send(msg)
            else:
                msg = "delete-schedules command cancelled."

            await interaction.followup.send(msg)

    @app_commands.command(
        name='delete-all',
        description="Delete all the schedules in the guild, use with caution!",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.check(snorlax_checks.check_admin_channel)
    @app_commands.checks.has_permissions(administrator=True)
    async def deleteAllSchedules(self, interaction: discord.Interaction) -> None:
        """
        Attempts to delete all schedules from the command origin server from
        the database.

        A confirmation interaction is sent to the user before performing the
        deletion.

        Args:
            interaction: The interaction that triggered the request.

        Returns:
            None
        """
        schedules = await snorlax_db.load_schedule_db(guild_id=interaction.guild.id)

        if schedules.empty:
            await interaction.response.send_message("There are no schedules to delete!")
            return

        await interaction.response.defer()

        view = snorlax_views.Confirm(interaction.user, timeout=30)
        embed = snorlax_embeds.get_schedule_embed(schedules)

        out = await interaction.channel.send(
            "Are you sure you want to remove all "
            f"{schedules.shape[0]} schedules?",
            view=view,
            embed=embed
        )

        view.response = out

        await view.wait()

        if view.value is None:
            logger.info(f"Deletion request timeout in guild {interaction.guild.name}.")
            msg = "delete-all-schedules command timed out."
        elif view.value:
            all_ok = True
            for schedule_id in schedules['rowid']:
                ok = await snorlax_db.drop_schedule(schedule_id)
                if ok:
                    logger.info(f'Schedule {schedule_id} deleted in guild {interaction.guild.name}.')
                else:
                    logger.error(f'Schedule {schedule_id} delete failed in guild {interaction.guild.name}!')
                    all_ok = False

            if all_ok:
                msg = f"{len(schedules)} schedules deleted successfully."
            else:
                msg = "An error was encountered while deleting the schedules."

            # Send feedback to the user in the channel as this can be a long message with many schedules.
            await interaction.channel.send(msg)
        else:
            msg = "delete-all-schedules command cancelled."

        await interaction.followup.send(msg)

    @app_commands.command(
        name='update-schedule',
        description="Update an existing schedule.",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.check(snorlax_checks.check_admin_channel)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.autocomplete(schedule=snorlax_autocompletes.schedule_selection_autocomplete)
    async def updateSchedule(
        self,
        interaction: discord.Interaction,
        schedule: str,
        open_time: Optional[str] = None,
        close_time: Optional[str] = None,
        open_message: Optional[str] = None,
        close_message: Optional[str] = None,
        warning: Optional[bool] = None,
        dynamic: Optional[bool] = None,
        max_num_delays: Optional[app_commands.Range[int, 0, 10]] = None,
        silent: Optional[bool] = None
    ) -> None:
        """
        Method to update an existing schedule.

        Options are entered as alternate keys and values, e.g., 'open 07:00
        close 21:00'.

        Args:
            open_time: The time to open the channel in 24 hour %H:%m format,
                e.g. `06:00`.
            close_time: The time to close the channel in 24 hour %H:%m format,
                e.g. `21:00`.
            channel: The Discord channel that the schedule should apply to.
                Defaults to the current channel.
            open_message: A custom message to send to the channel when it is
                opened.
            close_message: A custom message to send to the channel when it is
                closed.
            warning: Whether a closure warning message should be sent to the channel.
            dynamic: Whether dynamic closing is active for the schedule. I.e. if the channel
                still has activity (as per the guild inactive setting), the channel closing will
                be delayed.
            max_num_delays: The maximum number of times the closing of the
                channel can be delayed when using dynamic mode.
            silent: If True then no messages are sent to the channel when it is
                opened or closed.

        Returns:
            None
        """
        try:
            schedule = int(schedule)
        except Exception as e:
            await interaction.response.send_message(
                f"'{schedule}' is not a valid schedule. Please select a schedule from the options provided.",
                ephemeral=True
            )
            logger.error(f'Failed view schedule attempt in {interaction.guild.name}: {e}.')
            return

        exists = await snorlax_checks.check_schedule_exists(schedule)

        if not exists:
            msg = f'That schedule does not exist!'

            await interaction.response.send_message(msg)

            return

        allowed = await snorlax_checks.check_remove_schedule(interaction, schedule)

        if not allowed:
            msg = f'You do not have permission to deactivate schedule {schedule}.'

            await interaction.response.send_message(msg)

            return

        args = {
            "open": open_time,
            "close": close_time,
            "open_message": open_message,
            "close_message": close_message,
            "warning": warning,
            "dynamic": dynamic,
            "max_num_delays": max_num_delays,
            "silent": silent,
        }

        to_update = {}
        for column in args:

            value = args[column]

            if args[column] is None:
                continue

            elif column in ['open', 'close']:
                time_ok, f_value = snorlax_checks.check_time_format(value)
                if not time_ok:
                    msg = f"{value} is not a valid time."
                    await interaction.response.send_message(msg)
                    return

                if column == 'open':
                    if 'close' in to_update:
                        if f_value == to_update['close']:
                            msg = "The open and close time cannot be the same!"
                            await interaction.response.send_message(msg)
                            return

                elif column == 'close':
                    if 'open' in to_update:
                        if f_value == to_update['open']:
                            msg = "The open and close time cannot be the same!"
                            await interaction.response.send_message(msg)
                            return

                value = f_value

            to_update[column] = value

        # Check if one or the other is in to_update, already checked the case
        # where both are to be updated above
        open_close_sum = sum(('open' in to_update, 'close' in to_update))

        if open_close_sum > 0:
            channel_id = await snorlax_db.get_schedule_channel(schedule)

            if open_close_sum == 1:
                # Fetch the channel id to fetch for duplicates

                if 'open' in to_update:
                    curr_close = await snorlax_db.get_schedule_close(schedule)
                    the_same = curr_close == to_update['open']

                    if await snorlax_db.check_schedule_exists_with_times(channel_id, to_update['open'], curr_close):
                        msg = "That schedule already exists!"
                        await interaction.response.send_message(msg, ephemeral=True)
                        return

                elif 'close' in to_update:
                    curr_open = await snorlax_db.get_schedule_open(schedule)
                    the_same = curr_open == to_update['close']

                    if await snorlax_db.check_schedule_exists_with_times(channel_id, curr_open, to_update['close']):
                        msg = "That schedule already exists!"
                        await interaction.response.send_message(msg, ephemeral=True)
                        return

                if the_same:
                    await interaction.response.send_message(
                        "The open and close time cannot be the same!",
                        ephemeral=True
                    )
                    return

            if open_close_sum == 2:
                if await snorlax_db.check_schedule_exists_with_times(channel_id, to_update['open'], to_update['close']):
                    msg = "That schedule already exists!"
                    await interaction.response.send_message(msg, ephemeral=True)
                    return

        all_ok = True
        for column in to_update:
            ok = await snorlax_db.update_schedule(schedule, column, to_update[column])
            if not ok:
                all_ok = False
                logger.error(f'Update on schedule {schedule} errored for column {column}')

        if all_ok:
            logger.info(f'Schedule {schedule} updated.')
            schedule_df = await snorlax_db.load_schedule_db(rowid=schedule)
            msg = f"Schedule for <#{schedule_df['channel'].iloc[0]}> updated successfully!"
            embed = snorlax_embeds.get_schedule_embed(schedule_df)

            await interaction.response.send_message(msg, embed=embed)
        else:
            await interaction.response.send_message(
                "Error when creating the schedule! Please check the schedule details.",
                ephemeral=True
            )

    async def close_channel(
        self,
        channel: discord.TextChannel,
        role: discord.Role,
        overwrites: discord.PermissionOverwrite,
        open: str,
        custom_close_message: str,
        silent: bool,
        log_channel: Optional[discord.TextChannel],
        tz: str,
        time_format_fill: str,
        rowid: int,
        client_user: discord.User
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
        now = snorlax_utils.get_current_time(tz=tz)

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

        await snorlax_db.update_dynamic_close(rowid)
        await snorlax_db.update_current_delay_num(rowid)

        if log_channel is not None:
            embed = snorlax_log.schedule_log_embed(
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
        channel: discord.TextChannel,
        role: discord.Role,
        overwrites: discord.PermissionOverwrite,
        close: str,
        custom_open_message: str,
        silent: bool,
        log_channel: Optional[discord.TextChannel],
        tz: str,
        time_format_fill: str,
        client_user: discord.User
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
        now = snorlax_utils.get_current_time(tz=tz)
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
            embed = snorlax_log.schedule_log_embed(
                channel,
                tz,
                'open'
            )
            await log_channel.send(embed=embed)

    @app_commands.command(
        name='view-schedule',
        description="View the details of the selected schedule.",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.check(snorlax_checks.check_admin_channel)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.autocomplete(schedule=snorlax_autocompletes.schedule_selection_autocomplete)
    async def viewSchedule(self, interaction: discord.Interaction, schedule: str) -> None:
        """Sends an embed to the interacting user that shows the details of the selected schedule.

        Args:
            interaction: The interaction that triggered the request.
            schedule: The schedule to view, start typing the name of the channel narrow down the
                options.

        Returns:
            None
        """
        try:
            schedule = int(schedule)
        except Exception as e:
            await interaction.response.send_message(
                f"'{schedule}' is not a valid schedule. Please select a schedule from the options provided.",
                ephemeral=True
            )
            logger.error(f'Failed view schedule attempt in {interaction.guild.name}: {e}.')
            return

        exists = await snorlax_checks.check_schedule_exists(schedule)

        if not exists:
            msg = f'That schedule does not exist!'

            await interaction.response.send_message(msg)

            return

        allowed = await snorlax_checks.check_remove_schedule(interaction, schedule)

        if not allowed:
            msg = f'That schedule does not exist!'

            await interaction.response.send_message(msg)

            return

        schedule_df = await snorlax_db.load_schedule_db(rowid=schedule)
        embed = snorlax_embeds.get_schedule_embed(schedule_df)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name='view-schedules',
        description="View all the created schedules. Can filter by activated or deactivated.",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.check(snorlax_checks.check_admin_channel)
    @app_commands.checks.has_permissions(administrator=True)
    async def viewSchedules(self, interaction: discord.Interaction, active: Optional[bool] = None) -> None:
        """
        Sends an embed to the interacting user that shows all the schedules.

        User can select whether to only show active or deactivated schedules.

        Args:
            interaction: The interaction that triggered the request.
            active: Select 'True' to only show active schedules, select 'False'
                to show all inactive schedules. By default all schedules are shown
                regardless of active state.

        Returns:
            None
        """
        schedule_df = await snorlax_db.load_schedule_db(
            guild_id=interaction.guild.id,
            active=active
        )

        if schedule_df.empty:
            if active is None:
                msg = "There are no schedules on this server."
            elif active:
                msg = "There are no active schedules on this server."
            else:
                msg = "There are no deactivated schedules on this server."

            await interaction.response.send_message(msg, ephemeral=True)
        else:
            embed = snorlax_embeds.get_schedule_embed(schedule_df)

            await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name='check-schedule-roles',
        description=(
            "Check a channel to see if there any roles where the schedule will not apply."
        ),
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.check(snorlax_checks.check_admin_channel)
    @app_commands.checks.has_permissions(administrator=True)
    async def checkScheduleRoles(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        """
        Check the channel for roles that a schedule won't apply to.

        Args:
            interaction: The interaction that triggered the request.
            channel: The channel to check.

        Returns:
            None
        """
        no_effect_roles_allow, no_effect_roles_deny = await snorlax_checks.check_schedule_overwrites(
            channel,
            self.bot.user
        )

        if len(no_effect_roles_allow + no_effect_roles_deny) > 0:
            embed = snorlax_embeds.get_schedule_overwrites_embed(
                no_effect_roles_allow,
                no_effect_roles_deny,
                channel
            )
        else:
            embed = snorlax_embeds.get_schedule_overwrites_embed_all_ok(channel)

        await interaction.response.send_message(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: GuildChannel, after: GuildChannel) -> None:
        """Updates the channel name in the schedules db upon an edit.

        Args:
            before: The channel object before the change.
            after: The channel object after the change.
        """
        if before.name != after.name:
            schedule_ids = await snorlax_db.get_schedule_ids_by_channel_id(before.id)

            if schedule_ids:
                for id in schedule_ids:
                    ok = await snorlax_db.update_schedule(id[0], 'channel_name', after.name)
                    if not ok:
                        logger.error(
                            f'Update channel name failed for channel {after.name} in '
                            f'guild {after.guild.name}.'
                        )

                logger.info(
                    f'Updated channel {before.name} name to {after.name} '
                    f'for guild {after.guild.name} in schedules database.'
                )

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: GuildChannel) -> None:
        """
        Checks on a channel deletion whether the channel had a schedule.

        Args:
            channel: The deleted channel object.

        Returns:
            None
        """
        schedules = await snorlax_db.load_schedule_db()

        schedules = schedules.loc[schedules['channel'] == channel.id]

        if not schedules.empty:
            for id in schedules['rowid']:
                ok = await snorlax_db.drop_schedule(id)
                if ok:
                    log_channel = await snorlax_db.get_guild_log_channel(channel.guild.id)
                    if log_channel != -1:
                        log_channel = get(channel.guild.channels, id=int(log_channel))
                        log_embed = snorlax_log.schedules_deleted_log_embed(channel, id)
                        await log_channel.send(embed=log_embed)
                    logger.info(
                        f'Schedule ID {id} has been deleted for guild {channel.guild.name}'
                        ' (channel deletion).'
                    )

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
        guild_db = await snorlax_db.load_guild_db(active_only=True)
        schedule_db = await snorlax_db.load_schedule_db(active=True)

        for tz in guild_db['tz'].unique():
            now = snorlax_utils.get_current_time(tz=tz)
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
                    await snorlax_db.update_dynamic_close(row.rowid)
                    if allow.send_messages == deny.send_messages is False:
                        # this means the channel is already set to neutral
                        logger.warning(
                            f'Channel {channel.name} already neutral, skipping opening.'
                        )
                        if log_channel is not None:
                            embed = snorlax_log.schedule_log_embed(
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
                                embed = snorlax_log.schedule_log_embed(
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
                            embed = snorlax_log.schedule_log_embed(
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

                        await snorlax_db.update_dynamic_close(row.rowid, new_close_time=new_close_time)
                        await snorlax_db.update_current_delay_num(row.rowid, row.current_delay_num + 1)

                        if log_channel is not None:
                            embed = snorlax_log.schedule_log_embed(
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
                        await snorlax_db.update_dynamic_close(row.rowid)
                        logger.warning(
                            f'Channel {channel.name} already closed in guild'
                            f' {channel.guild.name}, skipping closing.'
                        )

                        if log_channel is not None:
                            embed = snorlax_log.schedule_log_embed(
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

                        await snorlax_db.update_dynamic_close(row.rowid, new_close_time=new_close_time)
                        await snorlax_db.update_current_delay_num(row.rowid, row.current_delay_num + 1)

                        if log_channel is not None:
                            embed = snorlax_log.schedule_log_embed(
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
