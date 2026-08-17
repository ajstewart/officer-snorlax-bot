"""The schedules Cog of snorlax."""

import asyncio
import datetime

from typing import Optional

import discord

from discord import app_commands
from discord.abc import GuildChannel
from discord.errors import DiscordServerError, Forbidden
from discord.ext import commands, tasks
from discord.utils import get

from bot_logger import get_logger
from models import Schedule
from repositories import (
    GuildRepository,
    GuildScheduleSettingsRepository,
    ScheduleRepository,
)

from .utils import autocompletes as snorlax_autocompletes
from .utils import checks as snorlax_checks
from .utils import embeds as snorlax_embeds
from .utils import log_msgs as snorlax_log
from .utils import select_options as snorlax_options
from .utils import utils as snorlax_utils
from .utils import views as snorlax_views

logger = get_logger(__name__)


@app_commands.default_permissions(administrator=True)
class Schedules(commands.GroupCog, name="schedules"):
    """The schedules Cog of the bot.

    Takes care of everything to do with opening and closing channels.
    """

    def __init__(self, bot: commands.bot) -> None:
        """Init method for schedules.

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
        """Defines the checks to perform on the received command for all cog commands.

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
        name="activate-schedule",
        description="Set a schedule to be active.",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.check(snorlax_checks.check_admin_channel)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.autocomplete(
        schedule=snorlax_autocompletes.schedule_selection_autocomplete
    )
    async def activateSchedule(
        self, interaction: discord.Interaction, schedule: str
    ) -> None:
        """Toggles a saved schedule to active.

        Args:
            interaction: The interaction that triggered the request.
            schedule: The schedule to activate. Type the name of the channel to
                find your schedule.

        Returns:
            None.
        """
        try:
            schedule = int(schedule)
        except Exception as e:
            msg = (
                (
                    f"'{schedule}' is not a valid schedule. Please select a schedule"
                    " from the options provided."
                ),
            )
            embed = snorlax_embeds.get_message_embed(msg, msg_type="warning")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            logger.error(
                f"Failed activate schedule attempt in {interaction.guild.name}: {e}."
            )
            return

        async with self.bot.db_session() as session:
            schedule_repo = ScheduleRepository(session)
            schedule_db = await schedule_repo.get(schedule)

            if not schedule_db:
                msg = "That schedule does not exist!"
                embed = snorlax_embeds.get_message_embed(msg, msg_type="warning")

                await interaction.response.send_message(embed=embed)

                return

            allowed = snorlax_checks.check_remove_schedule(interaction, schedule_db)

            if not allowed:
                msg = f"You do not have permission to activate schedule {schedule}."
                embed = snorlax_embeds.get_message_embed(msg, msg_type="error")
                await interaction.response.send_message(embed=embed)

                return

            try:
                schedule_db.active = True
                embed = snorlax_embeds.get_message_embed(
                    "Schedule activated successfully.", msg_type="success"
                )
                await interaction.response.send_message(embed=embed)
            except Exception:
                embed = snorlax_embeds.get_message_embed(
                    "Schedule activation failed.", msg_type="error"
                )
                await interaction.response.send_message(embed=embed)
                logger.exception("Failed to activate schedule.")

    @app_commands.command(
        name="activate-schedules",
        description="Set multiple schedules to activate at once.",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.check(snorlax_checks.check_admin_channel)
    @app_commands.checks.has_permissions(administrator=True)
    async def activateSchedules(self, interaction: discord.Interaction) -> None:
        """Toggles all schedules provided to active.

        Args:
            interaction: The interaction that triggered the request.

        Returns:
            None.
        """
        async with self.bot.db_session() as session:
            options = await snorlax_options.schedule_options(
                session=session, guild=interaction.guild, active=False
            )

        if not options:
            embed = snorlax_embeds.get_message_embed(
                "All schedules are already active!", msg_type="warning"
            )
            await interaction.response.send_message(embed=embed)

            return

        view = snorlax_views.ScheduleDropdownView(
            user=interaction.user, options=options, context="activate", timeout=120
        )

        await interaction.response.defer()

        out = await interaction.channel.send(view=view)

        view.response = out

        await view.wait()

        if view.values is None:
            logger.info("activate-schedules command timeout.")
            embed = snorlax_embeds.get_message_embed(
                "activate-schedules command timed out.", msg_type="info"
            )
            await interaction.followup.send(embed=embed)
        else:
            async with self.bot.db_session() as session:
                schedule_repo = ScheduleRepository(session)
                try:
                    for id in view.values:
                        schedule_db = await schedule_repo.get(id)
                        schedule_db.active = True

                    embed = snorlax_embeds.get_message_embed(
                        f"Activated {len(view.values)} schedules successfully.",
                        msg_type="success",
                    )
                    await interaction.followup.send(embed=embed)
                except Exception:
                    embed = snorlax_embeds.get_message_embed(
                        "Activation failed.", msg_type="error"
                    )
                    await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="activate-all",
        description="Set all schedules to active.",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.check(snorlax_checks.check_admin_channel)
    @app_commands.checks.has_permissions(administrator=True)
    async def activateAllSchedules(self, interaction: discord.Interaction) -> None:
        """Toggles all schedules to active.

        Args:
            interaction: The interaction that triggered the request.

        Returns:
            None.
        """
        async with self.bot.db_session() as session:
            schedule_repo = ScheduleRepository(session)
            schedules_db = await schedule_repo.get_all(
                guild_id=interaction.guild.id, active=False
            )

            if not schedules_db:
                embed = snorlax_embeds.get_message_embed(
                    "All schedules are active already!", msg_type="warning"
                )
                await interaction.response.send_message(embed=embed)
                return

            try:
                for schedule in schedules_db:
                    schedule.active = True
                embed = snorlax_embeds.get_message_embed(
                    f"Activated {len(schedules_db)} schedules successfully.",
                    msg_type="success",
                )
                await interaction.response.send_message(embed=embed)
            except Exception:
                embed = snorlax_embeds.get_message_embed(
                    "Activation failed.", msg_type="error"
                )
                await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="create-schedule",
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
        silent: Optional[bool] = False,
    ) -> None:
        """Method to create a channel opening and closing schedule.

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
            dynamic: Whether dynamic closing is active for the schedule.
                I.e. if the channel still has activity (as per the guild inactive
                setting), the channel closing will be delayed.
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
            embed = snorlax_embeds.get_message_embed(msg, msg_type="error")
            await interaction.response.send_message(embed=embed)
            return

        # this just checks for single hour inputs, e.g. 6:00
        open_time = f_open_time

        time_ok, f_close_time = snorlax_checks.check_time_format(close_time)
        if not time_ok:
            msg = f"{close_time} is not a valid time."
            embed = snorlax_embeds.get_message_embed(msg, msg_type="error")
            await interaction.response.send_message(embed=embed, ephemeral=ephemeral)
            return

        close_time = f_close_time

        if close_time == open_time:
            msg = "The open and close time cannot be the same!"
            embed = snorlax_embeds.get_message_embed(msg, msg_type="error")
            await interaction.response.send_message(embed=embed, ephemeral=ephemeral)
            return

        async with self.bot.db_session() as session:
            schedule_repo = ScheduleRepository(session)
            exists = await schedule_repo.check_exists_with_times(
                channel.id, open_time, close_time
            )
            if exists:
                msg = "That schedule already exists!"
                embed = snorlax_embeds.get_message_embed(msg, msg_type="warning")
                await interaction.response.send_message(
                    embed=embed, ephemeral=ephemeral
                )
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
            read_message_history=True,
        )

        # Could support different roles in future.
        role = interaction.guild.default_role

        new_schedule = Schedule.create(
            guild_id=interaction.guild.id,
            channel_id=channel.id,
            channel_name=channel.name,
            role_id=role.id,
            role_name=role.name,
            open_time=open_time,
            close_time=close_time,
            open_message=open_message,
            close_message=close_message,
            warning=warning,
            dynamic=dynamic,
            max_num_delays=max_num_delays,
            silent=silent,
        )

        try:
            async with self.bot.db_session() as session:
                schedule_repo = ScheduleRepository(session)
                await schedule_repo.create(new_schedule)

            msg = f"Schedule for {channel.mention} created successfully!"
            msg_embed = snorlax_embeds.get_message_embed(msg, msg_type="success")

            (
                no_effect_roles_allow,
                no_effect_roles_deny,
            ) = await snorlax_checks.check_schedule_overwrites(channel, self.bot.user)

            overwrite_roles = len(no_effect_roles_allow + no_effect_roles_deny)

            embed = snorlax_embeds.get_schedule_embed(
                [new_schedule], num_warning_roles=overwrite_roles
            )

            await interaction.response.send_message(
                embeds=[msg_embed, embed], ephemeral=ephemeral
            )
        except Exception:
            logger.exception("Error when creating the schedule!")
            embed = snorlax_embeds.get_message_embed(
                "Error when creating the schedule!", msg_type="error"
            )
            await interaction.response.send_message(embed=embed, ephemeral=ephemeral)

    @app_commands.command(
        name="deactivate-schedule",
        description="Set a schedule to be deactivated.",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.check(snorlax_checks.check_admin_channel)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.autocomplete(
        schedule=snorlax_autocompletes.schedule_selection_autocomplete
    )
    async def deactivateSchedule(
        self, interaction: discord.Interaction, schedule: str
    ) -> None:
        """Toggles a saved schedule to deactivated.

        Args:
            interaction: The interaction that triggered the request.
            schedule: The schedule to activate.
                Type the name of the channel to find your schedule.

        Returns:
            None.
        """
        try:
            schedule = int(schedule)
        except Exception as e:
            msg = (
                f"'{schedule}' is not a valid schedule. Please select a schedule from"
                " the options provided."
            )
            embed = snorlax_embeds.get_message_embed(msg, msg_type="warning")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            logger.error(
                f"Failed deactivate schedule attempt in {interaction.guild.name}: {e}."
            )
            return

        async with self.bot.db_session() as session:
            schedule_repo = ScheduleRepository(session)
            schedule_db = await schedule_repo.get(schedule)

            if not schedule_db:
                msg = f"Schedule ID {schedule} does not exist!"
                embed = snorlax_embeds.get_message_embed(msg, msg_type="warning")
                await interaction.response.send_message(embed=embed)

                return

            allowed = snorlax_checks.check_remove_schedule(interaction, schedule_db)

            if not allowed:
                msg = f"You do not have permission to deactivate schedule {schedule}."
                embed = snorlax_embeds.get_message_embed(msg, msg_type="error")
                await interaction.response.send_message(embed=embed)

                return

            try:
                schedule_db.active = False
            except Exception:
                msg = "Schedule deactivation failed."
                embed = snorlax_embeds.get_message_embed(msg, msg_type="error")
                await interaction.response.send_message(embed=embed)

        msg = "Schedule deactivated successfully."
        embed = snorlax_embeds.get_message_embed(msg, msg_type="success")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="deactivate-schedules",
        description="Set multiple schedules to deactivated at once.",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.check(snorlax_checks.check_admin_channel)
    @app_commands.checks.has_permissions(administrator=True)
    async def deactivateSchedules(self, interaction: discord.Interaction) -> None:
        """Toggles the provided schedules to not active.

        Args:
            interaction: The interaction that triggered the request.

        Returns:
            None.
        """
        async with self.bot.db_session() as session:
            options = await snorlax_options.schedule_options(
                session=session, guild=interaction.guild, active=True
            )

            if not options:
                msg = "All schedules are already deactivated!"
                embed = snorlax_embeds.get_message_embed(msg, msg_type="warning")
                await interaction.response.send_message(embed=embed)

                return

            view = snorlax_views.ScheduleDropdownView(
                user=interaction.user,
                options=options,
                context="deactivate",
                timeout=120,
            )

            await interaction.response.defer()

            out = await interaction.channel.send(view=view)

            view.response = out

            await view.wait()

            if view.values is None:
                logger.info("deactivate-schedules command timeout.")
                embed = snorlax_embeds.get_message_embed(
                    "deactivate-schedules command timed out.", msg_type="info"
                )
                await interaction.followup.send(embed=embed)
            else:
                try:
                    schedule_repo = ScheduleRepository(session)
                    for id in view.values:
                        schedule_db = await schedule_repo.get(id)
                        allowed = snorlax_checks.check_remove_schedule(
                            interaction, schedule_db
                        )
                        if not allowed:
                            msg = (
                                "You do not have permission to "
                                f"deactivate schedule {id}."
                            )
                            embed = snorlax_embeds.get_message_embed(
                                msg, msg_type="error"
                            )
                            await interaction.followup.send(embed=embed)
                            return

                        schedule_db.active = False

                except Exception:
                    msg = "Deactivation failed."
                    embed = snorlax_embeds.get_message_embed(msg, msg_type="error")
                    await interaction.followup.send(embed=embed)

        msg = f"Deactivated {len(view.values)} schedules successfully."
        embed = snorlax_embeds.get_message_embed(msg, msg_type="success")
        await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="deactivate-all",
        description="Set all schedules to deactivated.",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.check(snorlax_checks.check_admin_channel)
    @app_commands.checks.has_permissions(administrator=True)
    async def deactivateAllSchedules(self, interaction: discord.Interaction) -> None:
        """Toggles all schedules to deactivated.

        Args:
            interaction: The interaction that triggered the request.

        Returns:
            None.
        """
        async with self.bot.db_session() as session:
            schedule_repo = ScheduleRepository(session)
            schedules = await schedule_repo.get_all(
                guild_id=interaction.guild.id, active=True
            )

            if not schedules:
                msg = "All schedules are deactivated already!"
                embed = snorlax_embeds.get_message_embed(msg, msg_type="warning")
                await interaction.response.send_message(embed=embed)

                return

        try:
            for schedule in schedules:
                schedule.active = False
        except Exception:
            msg = "Deactivation failed."
            embed = snorlax_embeds.get_message_embed(msg, msg_type="error")
            await interaction.response.send_message(embed=embed)

        msg = f"Deactivated {len(schedules)} schedules successfully."
        embed = snorlax_embeds.get_message_embed(msg, msg_type="success")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="manual-close",
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
        silent: bool = False,
    ) -> None:
        """A command to manually close a channel.

        Args:
            interaction: The interaction that triggered the request.
            channel: The channel to be closed, defaults to current channel.
            silent: Whether to close the channel silently.

        Returns:
            None
        """
        if channel is None:
            channel = get(interaction.guild.channels, id=interaction.channel.id)

        async with self.bot.db_session() as session:
            guild_repo = GuildRepository(session)
            guild_db = await guild_repo.get(interaction.guild.id)

        # Allow this to be used outside the admin channel but hide response if it is.
        ephemeral = interaction.channel.id != guild_db.admin_channel

        # check if in schedule
        # check if already closed
        # close
        async with self.bot.db_session() as session:
            schedule_repo = ScheduleRepository(session)
            schedule_db = await schedule_repo.get_by_channel(channel.id)

            if not schedule_db or schedule_db[0].active is False:
                msg = "That channel has no active schedule set."
                embed = snorlax_embeds.get_message_embed(msg, msg_type="warning")
                await interaction.response.send_message(embed=embed, ephemeral=True)

                return

        # Grab the schedule row
        # TODO: Poor logic when multiple schedules on a single channel
        schedule = schedule_db[0]

        guild_tz = guild_db.tz
        log_channel_id = guild_db.log_channel

        if log_channel_id != -1:
            log_channel = self.bot.get_channel(log_channel_id)
        else:
            log_channel = None

        time_channel_id = guild_db.time_channel
        if time_channel_id != -1:
            time_format_fill = f"<#{time_channel_id}>"
        else:
            time_format_fill = "Unavailable"

        role = get(channel.guild.roles, id=schedule.role)
        # get current overwrites
        overwrites = channel.overwrites_for(role)
        allow, deny = overwrites.pair()

        if deny.send_messages is True:
            # this means the channel is already closed
            msg = f"{channel.mention} is already closed!"
            embed = snorlax_embeds.get_message_embed(msg, msg_type="warning")
            await interaction.response.send_message(embed=embed, ephemeral=True)

            return

        await self.close_channel(
            channel,
            role,
            overwrites,
            schedule.open,
            schedule.close_message,
            silent,
            log_channel,
            guild_tz,
            time_format_fill,
            schedule.rowid,
            self.bot.user,
        )

        msg = f"Closed {channel.mention}!"
        embed = snorlax_embeds.get_message_embed(msg, msg_type="error")
        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)

    @manualClose.error
    async def manualClose_error(self, ctx: commands.context, error):
        """Handles any errors from manualClose.

        Args:
            ctx: The command context containing the message content and other
                metadata.
            error (Exception): The error passed from manualClose.

        Returns:
            None
        """
        if isinstance(error, commands.ChannelNotFound):
            embed = snorlax_embeds.get_message_embed(
                f"{error}", msg_type="error", title="Error"
            )
            await ctx.channel.send(embed=embed)
        elif isinstance(error, commands.CheckFailure):
            pass
        else:
            embed = snorlax_embeds.get_message_embed(
                f"Unknown error when processing command: {error}", msg_type="error"
            )
            await ctx.channel.send(embed=embed)

    @app_commands.command(
        name="manual-open",
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
        silent: bool = False,
    ) -> None:
        """A command to manually close a channel.

        Args:
            interaction: The interaction that triggered the request.
            channel: The channel to be closed, defaults to current channel.
            silent: Whether to open the channel silently.

        Returns:
            None
        """
        if channel is None:
            channel = get(interaction.guild.channels, id=interaction.channel.id)

        async with self.bot.db_session() as session:
            guild_repo = GuildRepository(session)
            guild_db = await guild_repo.get(interaction.guild.id)

        # Allow this to be used outside the admin channel but hide response if it is.
        ephemeral = interaction.channel.id != guild_db.admin_channel

        # check if in schedule
        # check if already open
        # open
        async with self.bot.db_session() as session:
            schedule_repo = ScheduleRepository(session)
            schedule_db = await schedule_repo.get_by_channel(channel.id)

        if not schedule_db or schedule_db[0].active is False:
            msg = "That channel has no schedule set."
            embed = snorlax_embeds.get_message_embed(msg, msg_type="warning")
            await interaction.response.send_message(embed=embed, ephemeral=True)

            return

        # Grab the schedule row
        schedule = schedule_db[0]

        guild_tz = guild_db.tz

        log_channel_id = guild_db.log_channel
        if log_channel_id != -1:
            log_channel = self.bot.get_channel(log_channel_id)
        else:
            log_channel = None

        time_channel_id = guild_db.time_channel
        if time_channel_id != -1:
            time_format_fill = f"<#{time_channel_id}>"
        else:
            time_format_fill = "Unavailable"

        role = get(channel.guild.roles, id=schedule.role)
        # get current overwrites
        overwrites = channel.overwrites_for(role)
        allow, deny = overwrites.pair()

        if allow.send_messages == deny.send_messages is False:
            # this means the channel is already open
            msg = f"{channel.mention} is already open!"
            embed = snorlax_embeds.get_message_embed(msg, msg_type="warning")
            await interaction.response.send_message(embed=embed, ephemeral=True)

            return

        await self.open_channel(
            channel,
            role,
            overwrites,
            schedule.close,
            schedule.open_message,
            silent,
            log_channel,
            guild_tz,
            time_format_fill,
            schedule.rowid,
            self.bot.user,
        )

        msg = f"Opened {channel.mention}!"
        embed = snorlax_embeds.get_message_embed(msg, msg_type="success")
        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)

    @manualOpen.error
    async def manualOpen_error(self, ctx: commands.context, error) -> None:
        """Handle any errors from manualOpen.

        Args:
            ctx: The command context containing the message content and other
                metadata.
            error (Exception): The error passed from manualOpen.

        Returns:
            None
        """
        if isinstance(error, commands.ChannelNotFound):
            embed = snorlax_embeds.get_message_embed(
                f"{error}", msg_type="error", title="Error"
            )
            await ctx.channel.send(embed=embed)

        elif isinstance(error, commands.CheckFailure):
            pass
        else:
            embed = snorlax_embeds.get_message_embed(
                f"{error}", msg_type="error", title="Unknown Error"
            )
            await ctx.channel.send(embed=embed)

    @app_commands.command(
        name="delete-schedule",
        description="Delete the selected schedule.",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.check(snorlax_checks.check_admin_channel)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.autocomplete(
        schedule=snorlax_autocompletes.schedule_selection_autocomplete
    )
    async def deleteSchedule(
        self, interaction: discord.Interaction, schedule: str
    ) -> None:
        """Deletes the requested schedule.

        Args:
            interaction: The interaction that triggered the request.
            schedule: The schedule to view, start typing the name of the channel
                narrow down the options.

        Returns:
            None
        """
        try:
            schedule = int(schedule)

        except Exception as e:
            msg = (
                f"'{schedule}' is not a valid schedule. Please select a schedule from"
                " the options provided."
            )
            embed = snorlax_embeds.get_message_embed(msg, msg_type="warning")
            await interaction.response.send_message(embed=embed, ephemeral=True)

            logger.error(
                f"Failed view schedule attempt in {interaction.guild.name}: {e}."
            )

            return

        async with self.bot.db_session() as session:
            schedule_repo = ScheduleRepository(session)
            schedule_db = await schedule_repo.get(schedule)

        if not schedule_db:
            msg = "That schedule does not exist!"
            embed = snorlax_embeds.get_message_embed(msg, msg_type="warning")
            await interaction.response.send_message(embed=embed)

            return

        allowed = snorlax_checks.check_remove_schedule(interaction, schedule_db)

        if not allowed:
            msg = "You do not have permission to delete that schedule."
            embed = snorlax_embeds.get_message_embed(msg, msg_type="error")
            await interaction.response.send_message(embed=embed)

            return

        await interaction.response.defer()

        schedule_channel_id = schedule_db.channel

        view = snorlax_views.Confirm(interaction.user, timeout=30)

        embed = snorlax_embeds.get_schedule_embed([schedule_db])

        msg = (
            "Are you sure you want to delete the schedule for"
            f" <#{schedule_channel_id}>?"
        )
        msg_embed = snorlax_embeds.get_message_embed(msg, msg_type="warning")

        out = await interaction.channel.send(view=view, embeds=[msg_embed, embed])

        view.response = out

        await view.wait()

        if view.value is None:
            logger.info(f"Deletion request timeout in guild {interaction.guild.name}.")
            msg = "delete-schedule command timed out."
            embed = snorlax_embeds.get_message_embed(msg, msg_type="info")
        elif view.value:
            try:
                async with self.bot.db_session() as session:
                    schedule_repo = ScheduleRepository(session)
                    # Refresh the object
                    schedule_db = await schedule_repo.get(schedule_db.rowid)
                    await schedule_repo.delete(schedule_db)

                msg = f"<#{schedule_channel_id}> schedule deleted successfully."
                embed = snorlax_embeds.get_message_embed(msg, msg_type="success")
                logger.info(
                    f"Schedule {schedule} deleted in guild {interaction.guild.name}."
                )
            except Exception:
                msg = (
                    "Error occurred while attempting to delete the"
                    f" <#{schedule_channel_id}> schedule!."
                )
                embed = snorlax_embeds.get_message_embed(msg, msg_type="error")
                logger.error(
                    f"Schedule {schedule} delete failed in guild"
                    f" {interaction.guild.name}!"
                )
        else:
            msg = "delete-schedule command cancelled."
            embed = snorlax_embeds.get_message_embed(msg, msg_type="warning")

        await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="delete-schedules",
        description="Select multiple schedules to be deleted.",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.check(snorlax_checks.check_admin_channel)
    @app_commands.checks.has_permissions(administrator=True)
    async def deleteSchedules(self, interaction: discord.Interaction) -> None:
        """Deletes the schedules selected by the user.

        A maximum of 25 schedules can be shown.

        Args:
            interaction: The interaction that triggered the request.

        Returns:
            None.
        """
        async with self.bot.db_session() as session:
            options = await snorlax_options.schedule_options(
                session=session, guild=interaction.guild, active=None
            )

        if not options:
            msg = "There are no schedules to delete!"
            embed = snorlax_embeds.get_message_embed(msg, msg_type="warning")

            await interaction.response.send_message(embed=embed)

            return

        view = snorlax_views.ScheduleDropdownView(
            user=interaction.user, options=options, context="delete", timeout=60
        )

        await interaction.response.defer()

        out = await interaction.channel.send(view=view)

        view.response = out

        await view.wait()

        if view.values is None:
            logger.info("delete-schedules command timeout.")
            msg = "deactivate-schedules command timed out."
            embed = snorlax_embeds.get_message_embed(msg, msg_type="info")
            await interaction.followup.send(embed=embed)
        else:
            # Get schedules for embed.
            schedules_to_delete = [int(schedule) for schedule in view.values]
            async with self.bot.db_session() as session:
                schedules_repo = ScheduleRepository(session)
                schedules_db = [
                    await schedules_repo.get(schedule_id)
                    for schedule_id in schedules_to_delete
                ]

                embed = snorlax_embeds.get_schedule_embed(schedules_db)

                confirm_view = snorlax_views.Confirm(user=interaction.user)

                msg = (
                    "Are you sure you want to delete the"
                    f" {len(schedules_to_delete)} selected schedules?"
                )
                msg_embed = snorlax_embeds.get_message_embed(msg, msg_type="warning")

                confirm_out = await interaction.channel.send(
                    view=confirm_view, embeds=[msg_embed, embed]
                )

                confirm_view.response = confirm_out

                await confirm_view.wait()

                if confirm_view.value is None:
                    logger.info(
                        f"Deletion request timeout in guild {interaction.guild.name}."
                    )
                    msg = "delete-schedules command timed out."
                    embed = snorlax_embeds.get_message_embed(msg, msg_type="info")
                elif confirm_view.value:
                    all_ok = True
                    for schedule in schedules_db:
                        try:
                            await schedules_repo.delete(schedule)
                            logger.info(
                                f"Schedule {schedule.rowid} deleted in guild"
                                f" {interaction.guild.name}."
                            )
                        except Exception:
                            logger.error(
                                f"Schedule {schedule.rowid} delete failed in guild"
                                f" {interaction.guild.name}!"
                            )
                            all_ok = False

                    if not all_ok:
                        msg = "An error was encountered while deleting the schedules."
                        embed = snorlax_embeds.get_message_embed(msg, msg_type="error")
                    else:
                        msg = (
                            f"{len(schedules_to_delete)} "
                            "schedules deleted successfully."
                        )
                        embed = snorlax_embeds.get_message_embed(
                            msg, msg_type="success"
                        )

                    # Send feedback to the user in the channel as this can be a
                    # long message with many schedules.
                    await interaction.channel.send(embed=embed)
                else:
                    msg = "delete-schedules command cancelled."
                    embed = snorlax_embeds.get_message_embed(msg, msg_type="info")

            await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="delete-all",
        description="Delete all the schedules in the guild, use with caution!",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.check(snorlax_checks.check_admin_channel)
    @app_commands.checks.has_permissions(administrator=True)
    async def deleteAllSchedules(self, interaction: discord.Interaction) -> None:
        """Attempts to delete all schedules from the command origin server from the db.

        A confirmation interaction is sent to the user before performing the
        deletion.

        Args:
            interaction: The interaction that triggered the request.

        Returns:
            None
        """
        async with self.bot.db_session() as session:
            schedules_repo = ScheduleRepository(session)
            schedules_db = await schedules_repo.get_all(guild_id=interaction.guild.id)

            if not schedules_db:
                msg = "There are no schedules to delete!"
                embed = snorlax_embeds.get_message_embed(msg, msg_type="warning")
                await interaction.response.send_message(embed=embed)
                return

            await interaction.response.defer()

            view = snorlax_views.Confirm(interaction.user, timeout=30)
            embed = snorlax_embeds.get_schedule_embed(schedules_db)

            msg = (
                f"Are you sure you want to remove all {schedules_db.shape[0]}"
                " schedules?"
            )
            msg_embed = snorlax_embeds.get_message_embed(msg, "warning")

            out = await interaction.channel.send(view=view, embeds=[msg_embed, embed])

            view.response = out

            await view.wait()

            if view.value is None:
                logger.info(
                    f"Deletion request timeout in guild {interaction.guild.name}."
                )
                msg = "delete-all-schedules command timed out."
                embed = snorlax_embeds.get_message_embed(msg, msg_type="info")
            elif view.value:
                all_ok = True
                for schedule in schedules_db:
                    try:
                        await schedules_repo.delete(schedule)
                        logger.info(
                            f"Schedule {schedule.rowid} deleted in guild"
                            f" {interaction.guild.name}."
                        )
                    except Exception:
                        logger.error(
                            f"Schedule {schedule.rowid} delete failed in guild"
                            f" {interaction.guild.name}!"
                        )
                        all_ok = False

                if all_ok:
                    msg = f"{len(schedules_db)} schedules deleted successfully."
                    embed = snorlax_embeds.get_message_embed(msg, msg_type="success")
                else:
                    msg = "An error was encountered while deleting the schedules."
                    embed = snorlax_embeds.get_message_embed(msg, msg_type="error")

                # Send feedback to the user in the channel as this can be a
                # long message with many schedules.
                await interaction.channel.send(embed=embed)
            else:
                msg = "delete-all-schedules command cancelled."
                embed = snorlax_embeds.get_message_embed(msg, msg_type="info")

        await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="update-schedule",
        description="Update an existing schedule.",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.check(snorlax_checks.check_admin_channel)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.autocomplete(
        schedule=snorlax_autocompletes.schedule_selection_autocomplete
    )
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
        silent: Optional[bool] = None,
    ) -> None:
        """Method to update an existing schedule.

        Options are entered as alternate keys and values, e.g., 'open 07:00
        close 21:00'.

        Args:
            interaction: The interaction that triggered the request.
            schedule: The schedule to update.
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
            dynamic: Whether dynamic closing is active for the schedule.
                I.e. if the channel still has activity (as per the guild inactive
                setting), the channel closing will be delayed.
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
            msg = (
                f"'{schedule}' is not a valid schedule. Please select a schedule from"
                " the options provided."
            )
            embed = snorlax_embeds.get_message_embed(msg, msg_type="warning")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            logger.error(
                f"Failed view schedule attempt in {interaction.guild.name}: {e}."
            )
            return

        async with self.bot.db_session() as session:
            schedules_repo = ScheduleRepository(session)
            schedule_db = await schedules_repo.get(schedule)

            if not schedule_db:
                msg = "That schedule does not exist!"
                embed = snorlax_embeds.get_message_embed(msg, msg_type="warning")
                await interaction.response.send_message(embed=embed)

                return

            allowed = snorlax_checks.check_remove_schedule(interaction, schedule_db)

            if not allowed:
                msg = f"You do not have permission to deactivate schedule {schedule}."
                embed = snorlax_embeds.get_message_embed(msg, msg_type="error")
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

                elif column in ["open", "close"]:
                    time_ok, f_value = snorlax_checks.check_time_format(value)
                    if not time_ok:
                        msg = f"{value} is not a valid time."
                        embed = snorlax_embeds.get_message_embed(msg, msg_type="error")
                        await interaction.response.send_message(embed=embed)
                        return

                    if column == "open":
                        if "close" in to_update:
                            if f_value == to_update["close"]:
                                msg = "The open and close time cannot be the same!"
                                embed = snorlax_embeds.get_message_embed(
                                    msg, msg_type="warning"
                                )
                                await interaction.response.send_message(embed=embed)
                                return

                    elif column == "close":
                        if "open" in to_update and f_value == to_update["open"]:
                            msg = "The open and close time cannot be the same!"
                            embed = snorlax_embeds.get_message_embed(
                                msg, msg_type="warning"
                            )
                            await interaction.response.send_message(embed=embed)
                            return

                    value = f_value

                to_update[column] = value

            # Check if one or the other is in to_update, already checked the case
            # where both are to be updated above
            open_close_sum = sum(("open" in to_update, "close" in to_update))

            if open_close_sum > 0:
                channel_id = schedule_db.channel

                if open_close_sum == 1:
                    # Fetch the channel id to fetch for duplicates

                    if "open" in to_update:
                        curr_close = schedule_db.close
                        the_same = curr_close == to_update["open"]

                        if await schedules_repo.check_exists_with_times(
                            channel_id, to_update["open"], curr_close
                        ):
                            msg = "That schedule already exists!"
                            embed = snorlax_embeds.get_message_embed(
                                msg, msg_type="warning"
                            )
                            await interaction.response.send_message(
                                embed=embed, ephemeral=True
                            )
                            return

                    elif "close" in to_update:
                        curr_open = schedule_db.open
                        the_same = curr_open == to_update["close"]

                        if await schedules_repo.check_exists_with_times(
                            channel_id, curr_open, to_update["close"]
                        ):
                            msg = "That schedule already exists!"
                            embed = snorlax_embeds.get_message_embed(
                                msg, msg_type="warning"
                            )
                            await interaction.response.send_message(
                                embed=embed, ephemeral=True
                            )
                            return

                    if the_same:
                        msg = "The open and close time cannot be the same!"
                        embed = snorlax_embeds.get_message_embed(
                            msg, msg_type="warning"
                        )
                        await interaction.response.send_message(
                            embed=embed, ephemeral=True
                        )
                        return

                if open_close_sum == 2 and await schedules_repo.check_exists_with_times(
                    channel_id, to_update["open"], to_update["close"]
                ):
                    msg = "That schedule already exists!"
                    embed = snorlax_embeds.get_message_embed(msg, msg_type="warning")
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return

            try:
                for attr in to_update:
                    setattr(schedule_db, attr, to_update[attr])

                logger.info(f"Schedule {schedule} updated.")
                msg = f"Schedule for <#{schedule_db.channel}> updated successfully!"
                msg_embed = snorlax_embeds.get_message_embed(msg, msg_type="success")
                embed = snorlax_embeds.get_schedule_embed([schedule_db])
                await interaction.response.send_message(embeds=[msg_embed, embed])
            except Exception:
                msg = (
                    "Error when creating the schedule! "
                    "Please check the schedule details."
                )
                embed = snorlax_embeds.get_message_embed(msg, msg_type="error")
                await interaction.response.send_message(embed=embed, ephemeral=True)

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
        client_user: discord.User,
    ) -> None:
        """The opening channel process.

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
        guild_id = channel.guild.id

        async with self.bot.db_session() as session:
            guild_schedule_settings_repo = GuildScheduleSettingsRepository(session)
            guild_schedule_settings_db = await guild_schedule_settings_repo.get(
                guild_id
            )
            if not guild_schedule_settings_db:
                raise ValueError(
                    f"No schedule settings found for guild {channel.guild.name}!"
                )
            else:
                guild_close_message = guild_schedule_settings_db.base_close_message

        now = snorlax_utils.get_current_time(tz=tz)

        close_embed = snorlax_embeds.get_close_embed(
            open,
            now,
            guild_close_message,
            custom_close_message,
            client_user,
            time_format_fill,
        )

        async with self.bot.db_session() as session:
            schedules_repo = ScheduleRepository(session)
            schedules_db = await schedules_repo.get(rowid)
            last_open_message = schedules_db.last_open_message

            # Remove the previous open message if present.
            if last_open_message is not None:
                try:
                    last_open_message = await channel.fetch_message(last_open_message)
                except Exception as e:
                    logger.warning(
                        f"Last open message not found, skipping deletion (error: {e})."
                    )
                else:
                    logger.info(
                        f"Deleting previous open message in {channel.name} in"
                        f" {channel.guild.name}."
                    )
                    await last_open_message.delete()

            if not silent:
                # Send the new one
                close_message = await channel.send(embed=close_embed)

                # Update the DB with the new last close message.
                logger.debug(
                    f"Updating last close message for schedule {rowid} to"
                    f" {close_message.id}."
                )
                schedules_db.last_close_message = close_message.id

            overwrites.send_messages = False
            overwrites.send_messages_in_threads = False

        await channel.set_permissions(role, overwrite=overwrites)

        schedules_db.reset_dynamic_close()
        schedules_db.reset_current_delay_num()

        if log_channel is not None:
            embed = snorlax_log.schedule_log_embed(channel, tz, "close")
            await log_channel.send(embed=embed)

        logger.info(f"Channel {channel.name} closed in guild {channel.guild.name}.")

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
        rowid: int,
        client_user: discord.User,
    ) -> None:
        """The opening channel process.

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
            rowid: The id of the schedule so the delay time can be reset.
            client_user: The bot user instance.

        Returns:
            None
        """
        guild_id = channel.guild.id

        async with self.bot.db_session() as session:
            guild_schedule_settings_repo = GuildScheduleSettingsRepository(session)
            guild_schedule_settings_db = await guild_schedule_settings_repo.get(
                guild_id
            )

            if not guild_schedule_settings_db:
                raise ValueError(
                    f"No schedule settings found for guild {channel.guild.name}!"
                )
            else:
                guild_open_message = guild_schedule_settings_db.base_open_message

        now = snorlax_utils.get_current_time(tz=tz)
        overwrites.send_messages = None
        overwrites.send_messages_in_threads = None
        await channel.set_permissions(role, overwrite=overwrites)

        open_embed = snorlax_embeds.get_open_embed(
            close,
            now,
            guild_open_message,
            custom_open_message,
            client_user,
            time_format_fill,
        )

        async with self.bot.db_session() as session:
            schedules_repo = ScheduleRepository(session)
            schedules_db = await schedules_repo.get(rowid)
            last_close_message = schedules_db.last_close_message

            # Remove the previous close message if present.
            if last_close_message is not None:
                try:
                    last_close_message = await channel.fetch_message(last_close_message)
                except Exception as e:
                    logger.warning(
                        f"Last close message not found, skipping deletion (error: {e})."
                    )
                else:
                    logger.info(
                        f"Deleting previous close message in {channel.name} in"
                        f" {channel.guild.name}."
                    )
                    await last_close_message.delete()

            if not silent:
                open_message = await channel.send(embed=open_embed)
                logger.debug(
                    f"Updating last open message for schedule {rowid} to "
                    f"{open_message.id}."
                )
                schedules_db.last_open_message = open_message.id

            logger.info(f"Opened {channel.name} in {channel.guild.name}.")

        if log_channel is not None:
            embed = snorlax_log.schedule_log_embed(channel, tz, "open")
            await log_channel.send(embed=embed)

    @app_commands.command(
        name="view-schedule",
        description="View the details of the selected schedule.",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.check(snorlax_checks.check_admin_channel)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.autocomplete(
        schedule=snorlax_autocompletes.schedule_selection_autocomplete
    )
    async def viewSchedule(
        self, interaction: discord.Interaction, schedule: str
    ) -> None:
        """Sends an embed to the user that shows the details of the selected schedule.

        Args:
            interaction: The interaction that triggered the request.
            schedule: The schedule to view, start typing the name of the
                channel narrow down the options.

        Returns:
            None
        """
        try:
            schedule = int(schedule)
        except Exception as e:
            msg = (
                f"'{schedule}' is not a valid schedule. Please select a schedule from"
                " the options provided."
            )
            embed = snorlax_embeds.get_message_embed(msg, msg_type="warning")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            logger.error(
                f"Failed view schedule attempt in {interaction.guild.name}: {e}."
            )
            return

        async with self.bot.db_session as session:
            schedules_repo = ScheduleRepository(session)
            schedule_db = await schedules_repo.get(schedule)

            if not schedule_db:
                msg = "That schedule does not exist!"
                embed = snorlax_embeds.get_message_embed(msg, msg_type="warning")
                await interaction.response.send_message(embed=embed)

                return

            allowed = snorlax_checks.check_remove_schedule(interaction, schedule_db)

            if not allowed:
                msg = "You are not allowed to view that schedule!"
                embed = snorlax_embeds.get_message_embed(msg, msg_type="error")
                await interaction.response.send_message(embed=embed)

                return

            embed = snorlax_embeds.get_schedule_embed([schedule_db])

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="view-schedules",
        description=(
            "View all the created schedules. Can filter by activated or deactivated."
        ),
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.check(snorlax_checks.check_admin_channel)
    @app_commands.checks.has_permissions(administrator=True)
    async def viewSchedules(
        self, interaction: discord.Interaction, active: Optional[bool] = None
    ) -> None:
        """Sends an embed to the interacting user that shows all the schedules.

        User can select whether to only show active or deactivated schedules.

        Args:
            interaction: The interaction that triggered the request.
            active: Select 'True' to only show active schedules, select 'False'
                to show all inactive schedules. By default all schedules are shown
                regardless of active state.

        Returns:
            None
        """
        async with self.bot.db_session() as session:
            schedules_repo = ScheduleRepository(session)
            schedules_db = await schedules_repo.get_all(
                guild_id=interaction.guild.id, active=active
            )

        if not schedules_db:
            if active is None:
                msg = "There are no schedules on this server."
            elif active:
                msg = "There are no active schedules on this server."
            else:
                msg = "There are no deactivated schedules on this server."

            embed = snorlax_embeds.get_message_embed(msg, msg_type="warning")

            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            embed = snorlax_embeds.get_schedule_embed(schedules_db)

            await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="check-schedule-roles",
        description=(
            "Check a channel to see if there any roles where the schedule will not"
            " apply."
        ),
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.check(snorlax_checks.check_admin_channel)
    @app_commands.checks.has_permissions(administrator=True)
    async def checkScheduleRoles(
        self, interaction: discord.Interaction, channel: discord.TextChannel
    ) -> None:
        """Check the channel for roles that a schedule won't apply to.

        Args:
            interaction: The interaction that triggered the request.
            channel: The channel to check.

        Returns:
            None
        """
        (
            no_effect_roles_allow,
            no_effect_roles_deny,
        ) = await snorlax_checks.check_schedule_overwrites(channel, self.bot.user)

        if len(no_effect_roles_allow + no_effect_roles_deny) > 0:
            embed = snorlax_embeds.get_schedule_overwrites_embed(
                no_effect_roles_allow, no_effect_roles_deny, channel
            )
        else:
            embed = snorlax_embeds.get_schedule_overwrites_embed_all_ok(channel)

        await interaction.response.send_message(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_update(
        self, before: GuildChannel, after: GuildChannel
    ) -> None:
        """Updates the channel name in the schedules db upon an edit.

        Args:
            before: The channel object before the change.
            after: The channel object after the change.
        """
        if before.name != after.name:
            async with self.bot.db_session() as session:
                schedules_repo = ScheduleRepository(session)
                schedules_db = await schedules_repo.get_by_channel(before.id)

                if schedules_db:
                    for schedule in schedules_db:
                        schedule.channel_name = after.name

            logger.info(
                f"Updated channel {before.name} name to {after.name} "
                f"for guild {after.guild.name} in schedules database."
            )

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: GuildChannel) -> None:
        """Checks on a channel deletion whether the channel had a schedule.

        Args:
            channel: The deleted channel object.

        Returns:
            None
        """
        async with self.bot.db_session() as session:
            schedules_repo = ScheduleRepository(session)
            guilds_repo = GuildRepository(session)

            schedules_db = await schedules_repo.get_by_channel(channel.id)

            if schedules_db:
                log_channel = await guilds_repo.get_log_channel(channel.guild.id)
                for schedule in schedules_db:
                    await schedules_repo.delete(schedule)

        logger.info(
            f"Schedule ID {id} has been deleted for guild"
            f" {channel.guild.name} (channel deletion)."
        )

        if log_channel != -1:
            log_channel = get(channel.guild.channels, id=int(log_channel))
            log_embed = snorlax_log.schedules_deleted_log_embed(channel, id)
            await log_channel.send(embed=log_embed)

    @tasks.loop(seconds=60)
    async def channel_manager(self) -> None:
        """Checks the open and close schedules and acts accordingly.

        TODO: Needs to be broken up and tidied.

        Returns:
            None
        """
        client_user = self.bot.user

        async with self.bot.db_session() as session:
            guilds_repo = GuildRepository(session)
            schedules_repo = ScheduleRepository(session)
            guild_schedule_settings_repo = GuildScheduleSettingsRepository(session)

            guilds_db = await guilds_repo.get_all(active_only=True)

            schedules_by_tz = {}

            for guild in guilds_db:
                guild_schedules = await schedules_repo.get_all(
                    guild_id=guild.id, active=True
                )
                if not guild_schedules:
                    continue
                if guild.tz not in schedules_by_tz:
                    schedules_by_tz[guild.tz] = []
                schedules_by_tz[guild.tz] += guild_schedules

            for tz in schedules_by_tz:
                now = snorlax_utils.get_current_time(tz=tz)
                now_utc = discord.utils.utcnow()
                now_compare = now.strftime("%H:%M")

                scheds_to_check = schedules_by_tz[tz]

                last_guild_id = -1

                for schedule in scheds_to_check:
                    # Load the log channel for the guild
                    guild_id = schedule.guild
                    if guild_id != last_guild_id:
                        guild = await guilds_repo.get(guild_id)
                        log_channel_id = guild.log_channel
                        if log_channel_id != -1:
                            log_channel = self.bot.get_channel(log_channel_id)
                        else:
                            log_channel = None

                        time_channel_id = guild.time_channel
                        if time_channel_id != -1:
                            time_format_fill = f"<#{time_channel_id}>"
                        else:
                            time_format_fill = "Unavailable"
                        last_guild_id = guild_id

                        guild_schedule_settings = (
                            await guild_schedule_settings_repo.get(guild_id)
                        )

                        if not guild_schedule_settings:
                            raise ValueError(
                                f"Schedule settings not found for guild {guild_id}!"
                            )

                        warning_time = guild_schedule_settings.warning_time
                        inactive_time = guild_schedule_settings.inactive_time
                        delay_time = guild_schedule_settings.delay_time

                    channel = self.bot.get_channel(schedule.channel)

                    if channel is None:
                        logger.warning(
                            f"Channel {channel} is not found! Skipping schedule."
                        )
                        continue

                    role = get(channel.guild.roles, id=schedule.role)
                    # get current overwrites
                    overwrites = channel.overwrites_for(role)
                    allow, deny = overwrites.pair()

                    if schedule.open == now_compare:
                        # update dynamic close in case channel never got to close
                        schedule.reset_dynamic_close()
                        if allow.send_messages == deny.send_messages is False:
                            # this means the channel is already set to neutral
                            logger.warning(
                                f"Channel {channel.name} already neutral, "
                                "skipping opening."
                            )
                            if log_channel is not None:
                                embed = snorlax_log.schedule_log_embed(
                                    channel, tz, "open_skip"
                                )
                                await log_channel.send(embed=embed)
                            continue

                        await self.open_channel(
                            channel,
                            role,
                            overwrites,
                            schedule.close,
                            schedule.open_message,
                            schedule.silent,
                            log_channel,
                            tz,
                            time_format_fill,
                            schedule.rowid,
                            client_user,
                        )

                        continue

                    close_hour, close_min = schedule.close.split(":")

                    if schedule.warning:
                        then = now_utc - datetime.timedelta(minutes=inactive_time)

                        warning = (
                            datetime.datetime(
                                10, 10, 10, hour=int(close_hour), minute=int(close_min)
                            )
                            - datetime.timedelta(minutes=warning_time)
                        ).strftime("%H:%M")

                        if warning == now_compare:
                            messages = [
                                message async for message in channel.history(after=then)
                            ]
                            if snorlax_checks.check_if_channel_active(
                                messages, client_user
                            ):
                                warning_embed = snorlax_embeds.get_warning_embed(
                                    schedule.close,
                                    client_user,
                                    time_format_fill,
                                    schedule.dynamic,
                                    False,
                                    delay_time,
                                    warning_time,
                                )

                                await channel.send(embed=warning_embed)

                                if log_channel is not None:
                                    embed = snorlax_log.schedule_log_embed(
                                        channel, tz, "warning"
                                    )
                                    await log_channel.send(embed=embed)

                                continue

                    if schedule.close == now_compare:
                        if deny.send_messages is True:
                            logger.warning(
                                f"Channel {channel.name} already closed, "
                                "skipping closing."
                            )

                            if log_channel is not None:
                                embed = snorlax_log.schedule_log_embed(
                                    channel, tz, "close_skip"
                                )
                                await log_channel.send(embed=embed)

                            # Channel already closed so skip

                            continue

                        then = now_utc - datetime.timedelta(minutes=inactive_time)

                        messages = [
                            message async for message in channel.history(after=then)
                        ]

                        if (
                            snorlax_checks.check_if_channel_active(
                                messages, client_user
                            )
                            and schedule.dynamic
                            and schedule.current_delay_num < schedule.max_num_delays
                        ):
                            new_close_time = (
                                now + datetime.timedelta(minutes=delay_time)
                            ).strftime("%H:%M")

                            schedule.dynamic_close = new_close_time

                            schedule.current_delay_num += 1

                            if log_channel is not None:
                                embed = snorlax_log.schedule_log_embed(
                                    channel,
                                    tz,
                                    "delay",
                                    delay_time,
                                    schedule.current_delay_num,
                                    schedule.max_num_delays,
                                )
                                await log_channel.send(embed=embed)

                            logger.info(
                                f"Delayed closing for {channel.name} in "
                                f"guild {channel.guild.name}."
                            )

                            continue

                        else:
                            await self.close_channel(
                                channel,
                                role,
                                overwrites,
                                schedule.open,
                                schedule.close_message,
                                schedule.silent,
                                log_channel,
                                tz,
                                time_format_fill,
                                schedule.rowid,
                                client_user,
                            )

                    if schedule.dynamic_close == now_compare:
                        if deny.send_messages is True:
                            # Channel already closed so skip
                            schedule.reset_dynamic_close()
                            logger.warning(
                                f"Channel {channel.name} already closed in guild"
                                f" {channel.guild.name}, skipping closing."
                            )

                            if log_channel is not None:
                                embed = snorlax_log.schedule_log_embed(
                                    channel, tz, "close_skip"
                                )
                                await log_channel.send(embed=embed)

                            continue

                        then = now_utc - datetime.timedelta(minutes=inactive_time)

                        messages = [
                            message async for message in channel.history(after=then)
                        ]

                        if (
                            snorlax_checks.check_if_channel_active(
                                messages, client_user
                            )
                            and schedule.current_delay_num < schedule.max_num_delays
                        ):
                            new_close_time = (
                                now + datetime.timedelta(minutes=delay_time)
                            ).strftime("%H:%M")

                            schedule.dynamic_close = new_close_time
                            schedule.current_delay_num += 1

                            if log_channel is not None:
                                embed = snorlax_log.schedule_log_embed(
                                    channel,
                                    tz,
                                    "delay",
                                    delay_time,
                                    schedule.current_delay_num,
                                    schedule.max_num_delays,
                                )
                                await log_channel.send(embed=embed)

                            logger.info(
                                f"Delayed closing for {channel.name} in "
                                f"guild {channel.guild.name}."
                            )

                            if (
                                schedule.current_delay_num + 1
                                == schedule.max_num_delays
                            ):
                                warning_embed = snorlax_embeds.get_warning_embed(
                                    schedule.dynamic_close,
                                    client_user,
                                    time_format_fill,
                                    False,
                                    True,
                                    delay_time,
                                    warning_time,
                                )

                                await channel.send(embed=warning_embed)

                            continue

                        else:
                            await self.close_channel(
                                channel,
                                role,
                                overwrites,
                                schedule.open,
                                schedule.close_message,
                                schedule.silent,
                                log_channel,
                                tz,
                                time_format_fill,
                                schedule.rowid,
                                client_user,
                            )

    @channel_manager.before_loop
    async def before_timer(self) -> None:
        """Method to process before the channel manager loop is started.

        The purpose is to make sure the loop is started at the top of an even
        minute.

        Returns:
            None
        """
        await self.bot.wait_until_ready()
        # Make sure the loop starts at the top of the minute
        seconds = datetime.datetime.now().second
        sleep_time = 60 - seconds
        logger.info(f"Waiting {sleep_time} seconds to start the channel manager loop.")

        await asyncio.sleep(sleep_time)


@app_commands.default_permissions(administrator=True)
class SchedulesSettings(commands.GroupCog, name="schedules-settings"):
    """The schedules settings group.

    Contains commands to set the settings that apply to all schedules.
    """

    def __init__(self, bot: commands.bot) -> None:
        """Init method for schedules settings.

        Args:
            bot: The discord.py bot representation.

        Returns:
            None.
        """
        super(SchedulesSettings, self).__init__()
        self.bot = bot

    async def cog_check(self, ctx: commands.context) -> bool:
        """Defines the checks to perform on the received command for all cog commands.

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
        name="set-server-open-message",
        description=(
            "Sets the default open message that is included in every channel open"
            " message."
        ),
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.check(snorlax_checks.check_admin_channel)
    @app_commands.checks.has_permissions(administrator=True)
    async def set_server_open_message(
        self, interaction: discord.Interaction, open_message: str
    ) -> None:
        """Sets the default open message that is included in every channel open message.

        Args:
            interaction: The interaction that triggered the request.
            open_message: The message to use in the open message.
                Must be 60 characters or less.

        Returns:
            None
        """
        if len(open_message) > 60:
            msg = "The open message must be less than 60 characters."
            embed = snorlax_embeds.get_message_embed(msg, msg_type="warning")
            await interaction.response.send_message(embed=embed, ephemeral=True)

            return

        async with self.bot.db_session() as session:
            guild_schedule_settings_repo = GuildScheduleSettingsRepository(session)
            guild_schedul_settings_db = await guild_schedule_settings_repo.get(
                interaction.guild.id
            )
            guild_schedul_settings_db.base_open_message = open_message

        msg = f"Open message updated to:\n```{open_message}```"
        embed = snorlax_embeds.get_message_embed(msg, msg_type="success")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="set-server-close-message",
        description=(
            "Sets the default close message that is included in every channel close"
            " message."
        ),
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.check(snorlax_checks.check_admin_channel)
    @app_commands.checks.has_permissions(administrator=True)
    async def set_server_close_message(
        self, interaction: discord.Interaction, close_message: str
    ) -> None:
        """Set the default close message for every channel close message.

        Args:
            interaction: The interaction that triggered the request.
            close_message: The message to use in the close message.
                Must be 60 characters or less.

        Returns:
            None
        """
        if len(close_message) > 60:
            msg = "The close message must be less than 60 characters."
            embed = snorlax_embeds.get_message_embed(msg, msg_type="warning")
            await interaction.response.send_message(embed=embed, ephemeral=True)

            return

        async with self.bot.db_session() as session:
            guild_schedule_settings_repo = GuildScheduleSettingsRepository(session)
            guild_schedul_settings_db = await guild_schedule_settings_repo.get(
                interaction.guild.id
            )
            guild_schedul_settings_db.base_close_message = close_message

        msg = f"Close message updated to:\n```{close_message}```"
        embed = snorlax_embeds.get_message_embed(msg, msg_type="success")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="set-server-warning-time",
        description=(
            "Sets the number of minutes before a channel closing that a warning is"
            " sent."
        ),
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.check(snorlax_checks.check_admin_channel)
    @app_commands.checks.has_permissions(administrator=True)
    async def set_server_warning_time(
        self,
        interaction: discord.Interaction,
        warning_mins: app_commands.Range[int, 1, 60],
    ) -> None:
        """Updates the warning_time in the guild_schedule_settings db table.

        Args:
            interaction: The interaction that triggered the request.
            warning_mins: The number of minutes before closure a warning is issued.
                Must be between 1 and 60.

        Returns:
            None
        """
        async with self.bot.db_session() as session:
            guild_schedule_settings_repo = GuildScheduleSettingsRepository(session)
            guild_schedul_settings_db = await guild_schedule_settings_repo.get(
                interaction.guild.id
            )
            guild_schedul_settings_db.warning_time = warning_mins

        msg = f"Warning time updated to {warning_mins} min(s)."
        embed = snorlax_embeds.get_message_embed(msg, msg_type="success")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="set-server-inactive-time",
        description=(
            "Sets the number of minutes since the last message after which the channel"
            " is considered inactive."
        ),
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.check(snorlax_checks.check_admin_channel)
    @app_commands.checks.has_permissions(administrator=True)
    async def set_server_inactive_time(
        self,
        interaction: discord.Interaction,
        inactive_mins: app_commands.Range[int, 1, 120],
    ) -> None:
        """Updates the inactive_time in the guild_schedule_settings db table.

        Args:
            interaction: The interaction that triggered the request.
            inactive_mins: The number of minutes since the last message was
                sent for channel to be considered inactive.

        Returns:
            None
        """
        async with self.bot.db_session() as session:
            guild_schedule_settings_repo = GuildScheduleSettingsRepository(session)
            guild_schedul_settings_db = await guild_schedule_settings_repo.get(
                interaction.guild.id
            )
            guild_schedul_settings_db.inactive_time = inactive_mins

        msg = f"Inactive time updated to {inactive_mins} min(s)."
        embed = snorlax_embeds.get_message_embed(msg, msg_type="success")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="set-server-delay-time",
        description=(
            "Sets the number of minutes closure is delayed if the channel is still"
            " active."
        ),
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.check(snorlax_checks.check_admin_channel)
    @app_commands.checks.has_permissions(administrator=True)
    async def set_server_delay_time(
        self,
        interaction: discord.Interaction,
        delay_mins: app_commands.Range[int, 1, 30],
    ) -> None:
        """Updates the delay_time in the guild_schedule_settings db table.

        Args:
            interaction: The interaction that triggered the request.
            delay_mins: The number of minutes closure is delayed if the channel
                is still active.

        Returns:
            None
        """
        async with self.bot.db_session() as session:
            guild_schedule_settings_repo = GuildScheduleSettingsRepository(session)
            guild_schedul_settings_db = await guild_schedule_settings_repo.get(
                interaction.guild.id
            )
            guild_schedul_settings_db.delay_time = delay_mins

        msg = f"Delay time updated to {delay_mins} min(s)."
        embed = snorlax_embeds.get_message_embed(msg, msg_type="success")

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.bot) -> None:
    """The setup function to initiate the cog.

    Args:
        bot: The bot for which the cog is to be added.
    """
    if bot.test_guild is not None:
        await bot.add_cog(Schedules(bot), guild=discord.Object(id=bot.test_guild))
        await bot.add_cog(
            SchedulesSettings(bot), guild=discord.Object(id=bot.test_guild)
        )
    else:
        await bot.add_cog(Schedules(bot))
        await bot.add_cog(SchedulesSettings(bot))
