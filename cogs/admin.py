"""The admin cog which contains commands related to administrating the bot."""

from typing import Literal, Optional

import discord

from discord import app_commands
from discord.ext import commands
from discord.utils import get

from bot_logger import get_logger
from models import Guild, GuildScheduleSettings
from repositories import (
    GuildRepository,
    GuildScheduleSettingsRepository,
    ScheduleRepository,
)

from .utils import autocompletes as snorlax_autocompletes
from .utils import checks as snorlax_checks
from .utils import log_msgs as snorlax_logs
from .utils.embeds import get_admin_channel_embed, get_message_embed, get_settings_embed

logger = get_logger(__name__)


@app_commands.default_permissions(administrator=True)
class Admin(commands.GroupCog, name="admin"):
    """Cog for the admin commands."""

    def __init__(self, bot: commands.bot) -> None:
        """Init method for management.

        Args:
            bot: The discord.py bot representation.

        Returns:
            None.
        """
        super(Admin, self).__init__()
        self.bot = bot
        bot.tree.on_error = self.on_app_command_error

    async def on_app_command_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        """Handles errors raised by the app commands.

        Args:
            interaction: The interaction passed.
            error: The error raised.
        """
        async with self.bot.db_session() as session:
            guild_repo = GuildRepository(session)
            if isinstance(error, discord.app_commands.errors.MissingPermissions):
                if "administrator" in error.missing_permissions:
                    embed = get_message_embed(
                        "You do not have permission to use this command.",
                        msg_type="error",
                    )

                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    logger.error(error)

                    # Send message to log_channel if it is in use
                    log_channel_id = await guild_repo.get_log_channel(
                        interaction.guild.id
                    )
                    if log_channel_id != -1:
                        log_channel = get(
                            interaction.guild.channels, id=int(log_channel_id)
                        )
                        embed = snorlax_logs.attempted_app_command_embed(
                            interaction.command, interaction.channel, interaction.user
                        )
                        await log_channel.send(embed=embed)
                        logger.info(
                            "Unauthorised command attempt notification "
                            "sent to log channel."
                        )
                else:
                    embed = get_message_embed(
                        "You do not have the correct permissions to use this command.",
                        msg_type="error",
                    )

                    await interaction.response.send_message(embed=embed, ephemeral=True)

            elif isinstance(error, snorlax_checks.AdminChannelError):
                logger.warning(
                    "Command '%s' attempted in non-admin channel (%s).",
                    interaction.command.name,
                    interaction.guild.name,
                )

                admin_channel_id = await guild_repo.get_admin_channel(
                    interaction.guild.id
                )
                embed = get_admin_channel_embed(admin_channel_id)
                if interaction.command.name == "create-schedule":
                    embed.set_footer(
                        text=(
                            "Does not apply when '/schedules create-schedule' is used"
                            " to create a schedule for the channel where the command is"
                            " issued."
                        )
                    )
                await interaction.response.send_message(embed=embed, ephemeral=True)

            elif isinstance(error, app_commands.CheckFailure):
                if interaction.command.name == "create-time-channel":
                    if (
                        "manage_channels" in error.missing_permissions
                        or "connect" in error.missing_permissions
                    ):
                        embed = get_message_embed(
                            msg=(
                                "Permission error! Snorlax is missing the following"
                                " permissions to create a time"
                                f" channel:\n`{', '.join(error.missing_permissions)}`"
                                " (`connect` may also be required)."
                            ),
                            msg_type="error",
                        )

                        await interaction.response.send_message(
                            embed=embed, ephemeral=True
                        )
                    else:
                        embed = get_message_embed(
                            "You can't use that here.", msg_type="error"
                        )

                        await interaction.response.send_message(
                            embed=embed, ephemeral=True
                        )
                else:
                    embed = get_message_embed(
                        "You can't use that here.", msg_type="error"
                    )

                    await interaction.response.send_message(embed=embed, ephemeral=True)

            elif isinstance(
                error, app_commands.errors.CommandInvokeError
            ) and "Missing Permissions" in str(error):
                err_embed = get_message_embed(
                    (
                        "A permissions error has occurred. Does Snorlax have the"
                        " correct permissions?"
                    ),
                    msg_type="error",
                )
                await interaction.response.send_message(embed=err_embed, ephemeral=True)
                logger.error(error, exc_info=True)
            else:
                err_embed = get_message_embed(
                    "Unexpected error occurred, contact administrator.",
                    msg_type="error",
                )
                await interaction.response.send_message(embed=err_embed, ephemeral=True)
                logger.error(type(error))
                logger.error(error, exc_info=True)

    @app_commands.command(
        name="set-admin-channel",
        description="Set the channel for where snorlax admin commands can be used.",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.checks.has_permissions(administrator=True)
    async def setAdminChannel(
        self, interaction: discord.Interaction, channel: discord.TextChannel
    ) -> None:
        """Set the admin channel for a guild.

        Args:
            interaction: The interaction that triggered the request.
            channel: The channel to be used as the admin channel.

        Returns:
            None
        """
        guild = interaction.guild
        try:
            async with self.bot.db_session() as session:
                guild_repo = GuildRepository(session)
                guild = await guild_repo.get(guild.id)
                guild.admin_channel = channel.id
            embed = get_message_embed(
                f"{channel.mention} set as the Snorlax admin channel successfully.",
                msg_type="success",
            )
        except Exception as e:
            logger.exception("Error when setting the admin channel: %s", e)
            embed = get_message_embed(
                "Error when setting the admin channel.", msg_type="error"
            )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="set-log-channel",
        description="Set the channel for where snorlax will send log messages.",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.check(snorlax_checks.check_admin_channel)
    @app_commands.checks.has_permissions(administrator=True)
    async def setLogChannel(
        self, interaction: discord.Interaction, channel: discord.TextChannel
    ) -> None:
        """Sets the log channel for a guild.

        Args:
            interaction: The interaction that triggered the request.
            channel: The channel to be used as the log channel.

        Returns:
            None
        """
        guild = interaction.guild
        try:
            async with self.bot.db_session() as session:
                guild_repo = GuildRepository(session)
                guild = await guild_repo.get(guild.id)
                guild.log_channel = channel.id
            embed = get_message_embed(
                f"{channel.mention} set as the Snorlax log channel successfully.",
                msg_type="success",
            )
        except Exception as e:
            logger.exception("Error when setting the log channel: %s", e)
            embed = get_message_embed(
                "Error when setting the log channel.", msg_type="error"
            )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="set-pokenav-raid-category",
        description=(
            "Sets the Pokenav raid category for the guild where Snorlax"
            " will make sure not to eat friend codes."
        ),
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.check(snorlax_checks.check_admin_channel)
    @app_commands.checks.has_permissions(administrator=True)
    async def setPokenavRaidCategory(
        self, interaction: discord.Interaction, category: discord.CategoryChannel
    ) -> None:
        """Sets the Pokenav raid category for a guild.

        Args:
            interaction: The interaction that triggered the request.
            category: The category to be set as the Pokenav category.

        Returns:
            None
        """
        guild = interaction.guild
        cat_name = category.name
        try:
            async with self.bot.db_session() as session:
                guild_repo = GuildRepository(session)
                guild = await guild_repo.get(guild.id)
                guild.meowth_raid_category = category.id
        except Exception as e:
            logger.exception("Error when setting the Pokenav raid category: %s", e)
            embed = get_message_embed(
                "Error when setting the Pokenav raid category.", msg_type="error"
            )
        else:
            msg = (
                f"**{cat_name.upper()}** set as the Pokenav raid category successfully."
                " Make sure Snorlax has the correct permissions!"
            )
            embed = get_message_embed(msg, msg_type="success")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="reset-pokenav-raid-category",
        description="Resets the Pokenav raid category (disables).",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.check(snorlax_checks.check_admin_channel)
    @app_commands.checks.has_permissions(administrator=True)
    async def resetPokenavRaidCategory(self, interaction: discord.Interaction) -> None:
        """Resets the Pokenav raid category for a guild.

        Args:
            interaction: The interaction that triggered the request.

        Returns:
            None
        """
        guild = interaction.guild
        try:
            async with self.bot.db_session() as session:
                guild_repo = GuildRepository(session)
                guild = await guild_repo.get(guild.id)
                guild.meowth_raid_category = -1

        except Exception as e:
            logger.exception("Error when resetting the Pokenav raid category: %s", e)
            embed = get_message_embed(
                "Error when resetting the Pokenav raid category.", msg_type="error"
            )
        else:
            embed = get_message_embed(
                "Pokenav raid category has been reset.", msg_type="success"
            )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="set-timezone", description="Set the timezone for the guild."
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.check(snorlax_checks.check_admin_channel)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.autocomplete(tz=snorlax_autocompletes.timezones_autocomplete)
    async def setTimezone(self, interaction: discord.Interaction, tz: str) -> None:
        """Sets the timezone for a guild.

        Args:
            interaction: The interaction that triggered the request.
            tz: The timezone in string form. Uses format from the tz database
                of timezones e.g. 'Australia/Sydney', 'America/Los_Angeles'.

        Returns:
            None
        """
        logger.debug("Setting timezone for guild %s to %s.", interaction.guild.name, tz)
        try:
            async with self.bot.db_session() as session:
                guild_repo = GuildRepository(session)
                guild = await guild_repo.get(interaction.guild.id)
                guild.tz = tz
            embed = get_message_embed(
                f"{tz} set as the timezone successfully.", msg_type="success"
            )
        except Exception as e:
            logger.exception("Error when setting the timezone: %s", e)
            embed = get_message_embed(
                "Error when setting the timezone.", msg_type="error"
            )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="show-settings",
        description="Show all the current settings for the bot and guild.",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.check(snorlax_checks.check_admin_channel)
    @app_commands.checks.has_permissions(administrator=True)
    async def showSettings(self, interaction: discord.Interaction) -> None:
        """Shows the bot settings for the guild using an embed.

        Args:
            interaction: The interaction containing the request.

        Returns:
            None
        """
        guild_id = interaction.guild.id
        async with self.bot.db_session() as session:
            guild_repo = GuildRepository(session)
            guild = await guild_repo.get(guild_id)

        if guild is None:
            await interaction.response.send_message(
                embed=get_message_embed(
                    "Settings have not been configured for this guild.",
                    msg_type="error",
                ),
                ephemeral=True,
            )
        else:
            async with self.bot.db_session() as session:
                guild_schedule_repo = GuildScheduleSettingsRepository(session)
                guild_schedule_settings = await guild_schedule_repo.get(guild_id)
            if guild_schedule_settings is None:
                await interaction.response.send_message(
                    embed=get_message_embed(
                        "Guild schedule settings failed to load! Contact admin.",
                        msg_type="error",
                    ),
                    ephemeral=True,
                )
            else:
                embed = get_settings_embed(
                    interaction.guild, guild, guild_schedule_settings
                )

                await interaction.response.send_message(embed=embed)

    @commands.command(help="Shutdown the bot.", brief="Shutdown the bot.")
    @commands.guild_only()
    @commands.check(snorlax_checks.check_bot)
    @commands.is_owner()
    async def shutdown(self, ctx: commands.context) -> None:
        """Force the bot to shutdown.

        Args:
            ctx: The command context containing the message content and other
                metadata.

        Returns:
            None
        """
        embed = get_message_embed("Snorlax is shutting down.", msg_type="info")
        await ctx.channel.send(embed=embed)

        await self.bot.close()

    @commands.command(
        help=(
            "Sync the command tree.\n Examples:\n!sync -> global sync\n!sync ~ -> sync"
            " current guild\n!sync * -> copies all global app commands to current guild"
            " and syncs\n!sync ^ -> clears all commands from the current guild target"
            " and syncs (removes guild commands)\n!sync id_1 id_2 -> syncs guilds with"
            " id 1 and 2"
        ),
        brief="Sync the command tree.",
    )
    @commands.guild_only()
    @commands.check(snorlax_checks.check_bot)
    @commands.is_owner()
    async def sync(
        self,
        ctx: commands.context,
        guilds: commands.Greedy[discord.Object],
        spec: Optional[Literal["~", "*", "^"]] = None,
    ) -> None:
        """A normal command to sync the command tree.

        Examples:
            "!sync -> global sync"
            "!sync ~ -> sync current guild"
            "!sync * -> copies all global app commands to current guild and syncs"
            "!sync ^ -> clears all commands from the current guild target and
                syncs (removes guild commands)"
            "!sync id_1 id_2 -> syncs guilds with id 1 and 2"

        Args:
            ctx: The command context.
            guilds: The list of guilds to sync the tree to.
            spec: What 'spec' to sync the command tree to. See examples.
        """
        if not guilds:
            if spec == "~":
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "*":
                ctx.bot.tree.copy_global_to(guild=ctx.guild)
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "^":
                ctx.bot.tree.clear_commands(guild=ctx.guild)
                await ctx.bot.tree.sync(guild=ctx.guild)
                synced = []
            else:
                synced = await ctx.bot.tree.sync()

            await ctx.send(
                embed=get_message_embed(
                    (
                        f"Synced {len(synced)} commands"
                        f" {'globally' if spec is None else 'to the current guild.'}"
                    ),
                    msg_type="info",
                )
            )
            return

        ret = 0
        for guild in guilds:
            try:
                await ctx.bot.tree.sync(guild=guild)
            except discord.HTTPException:
                pass
            else:
                ret += 1

        await ctx.send(
            embed=get_message_embed(
                f"Synced the tree to {ret} / {len(guilds)}.", msg_type="success"
            )
        )

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild) -> None:
        """Process to complete when the bot joins a new guild.

        Args:
            guild: The guild object representing the new guild.

        Returns:
            None
        """
        # check if the new guild is already in the database
        async with self.bot.db_session() as session:
            guild_repo = GuildRepository(session)
            guild_schedule_repo = GuildScheduleSettingsRepository(session)
            schedule_repo = ScheduleRepository(session)
            guild_db = await guild_repo.get(guild.id)
            if guild_db is not None:
                logger.info(f"Setting guild {guild.name} to active.")
                guild_db.active = True

                # Then go through admin_channel, log_channel, time_channel, schedules
                # and raid category to see if the channels still exist.
                # Reset or drop if they don't.
                if guild_db.admin_channel != -1:
                    admin_channel = get(guild.channels, id=int(guild_db.admin_channel))
                    if admin_channel is None:
                        logger.warning(
                            f"Admin channel not found for {guild.name}, resetting."
                        )
                        guild_db.admin_channel = -1

                if guild_db.log_channel != -1:
                    log_channel = get(guild.channels, id=int(guild_db.log_channel))
                    if log_channel is None:
                        logger.warning(
                            f"Log channel not found for {guild.name}, resetting."
                        )
                        guild_db.log_channel = -1

                if guild_db.time_channel != -1:
                    time_channel = get(guild.channels, id=int(guild_db.time_channel))
                    if time_channel is None:
                        logger.warning(
                            f"Time channel not found for {guild.name}, resetting."
                        )
                        guild_db.time_channel = -1

                if guild_db.meowth_raid_category != -1:
                    raid_category = get(
                        guild.categories, id=int(guild_db.meowth_raid_category)
                    )
                    if raid_category is None:
                        logger.warning(
                            f"Raid category not found for {guild.name}, resetting."
                        )
                        guild_db.meowth_raid_category = -1

                # Check for schedule settings and create if not found.
                guild_schedule_settings_db = await guild_schedule_repo.get(guild.id)
                if guild_schedule_settings_db is None:
                    guild_schedule_settings_db = GuildScheduleSettings.create_default(
                        guild.id
                    )
                    guild_schedule_repo.create(guild_schedule_settings_db)

                schedules = await schedule_repo.get_all(guild_id=guild.id)
                if not schedules:
                    for schedule in schedules:
                        sched_channel_id = schedule.channel
                        sched_channel = get(guild.channels, id=int(sched_channel_id))
                        if sched_channel is None:
                            logger.warning(
                                f"Dropping schedule {schedule.rowid} in {guild.name} as"
                                " channel not found."
                            )
                            await schedule_repo.delete(schedule)

            # if not then create the new entry in the db
            else:
                logger.info(f"Adding {guild.name} to database.")
                guild_db = Guild.create_from_discord_guild(guild)
                guild_repo.create_guild(guild_db)

                # create admin channel
                overwrites = {}

                bot_role = guild.self_role
                overwrites[bot_role] = discord.PermissionOverwrite(
                    read_messages=True, send_messages=True
                )

                # block everybody from viewing channel
                default_role = guild.default_role
                overwrites[default_role] = discord.PermissionOverwrite(
                    read_messages=False
                )

                admin_channel = await guild.create_text_channel(
                    "snorlax-admin",
                    overwrites=overwrites,
                    reason="Admin channel for the snorlax bot.",
                )

                guild_db.admin_channel = admin_channel.id

                # Create schedules settings
                guild_schedule_settings_db = GuildScheduleSettings.create_default(
                    guild.id
                )
                await guild_schedule_repo.create(guild_schedule_settings_db)

                welcome_message = (
                    "This is where admin commands for Snorlax can be used."
                    "\n\nIf you would"
                    " like to use an existing channel instead, use the the '/admin"
                    " set-admin-channel' slash command to change it."
                    "\n\nAvailable commands"
                    " can be seen using the slash command interface.\n\nBelow are the"
                    " default settings for the server."
                )

                welcome_embed = get_message_embed(
                    welcome_message, msg_type="info", title="Hello!"
                )

                embed = get_settings_embed(guild, guild_db, guild_schedule_settings_db)

                await admin_channel.send(embeds=[welcome_embed, embed])

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild) -> None:
        """Process to complete when a guild is removed.

        Args:
            guild: The guild object representing the removed guild.

        Returns:
            None
        """
        # check if the new guild is already in the database
        async with self.bot.db_session() as session:
            guild_repo = GuildRepository(session)
            schedule_repo = ScheduleRepository(session)
            guild_db = await guild_repo.get(guild.id)
            if guild_db is not None:
                logger.info(f"Setting guild {guild.name} to not active.")
                # Set guild to inactive
                guild_db.active = False
                # Check for schedules and deactivate them all
                schedules_db = await schedule_repo.get_all(guild_id=guild.id)
                if schedules_db:
                    logger.info(f"Deactivating all schedules for {guild.name}.")
                    for schedule in schedules_db:
                        schedule.active = False

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel) -> None:
        """Checks on a channel deletion whether the channel was the log channel.

        Args:
            channel: The deleted channel object.

        Returns:
            None
        """
        async with self.bot.db_session() as session:
            guild_repo = GuildRepository(session)
            guild_db = await guild_repo.get(channel.guild.id)
            if guild_db is None:
                logger.warning(
                    f"Guild {channel.guild.name} not found in database when checking"
                    " channel deletion."
                )
                return

            if guild_db.admin_channel == channel.id:
                guild_db.admin_channel = -1
                logger.info(f"admin channel reset for guild {channel.guild.name}.")

            if guild_db.log_channel == channel.id:
                guild_db.log_channel = -1
                logger.info(f"Log channel reset for guild {channel.guild.name}.")


async def setup(bot: commands.bot) -> None:
    """The setup function to initiate the cog.

    Args:
        bot: The bot for which the cog is to be added.
    """
    if bot.test_guild is not None:
        await bot.add_cog(Admin(bot), guild=discord.Object(id=bot.test_guild))
    else:
        await bot.add_cog(Admin(bot))
