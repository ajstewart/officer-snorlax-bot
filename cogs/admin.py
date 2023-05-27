"""The admin cog which contains commands related to administrating the bot."""
import logging

from typing import Literal, Optional

import discord

from discord import app_commands
from discord.abc import GuildChannel
from discord.ext import commands
from discord.utils import get
from dotenv import find_dotenv, load_dotenv

from .utils import autocompletes as snorlax_autocompletes
from .utils import checks as snorlax_checks
from .utils import db as snorlax_db
from .utils import log_msgs as snorlax_logs
from .utils.embeds import get_admin_channel_embed, get_message_embed, get_settings_embed

logger = logging.getLogger()
load_dotenv(find_dotenv())


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
        if isinstance(error, discord.app_commands.errors.MissingPermissions):
            if "administrator" in error.missing_permissions:
                embed = get_message_embed(
                    "You do not have permission to use this command.", msg_type="error"
                )

                await interaction.response.send_message(embed=embed, ephemeral=True)
                logger.error(error)

                # Send message to log_channel if it is in use
                log_channel_id = await snorlax_db.get_guild_log_channel(
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
                        "Unauthorised command attempt notification sent to log channel."
                    )
            else:
                embed = get_message_embed(
                    "You do not have the correct permissions to use this command.",
                    msg_type="error",
                )

                await interaction.response.send_message(embed=embed, ephemeral=True)

        elif isinstance(error, snorlax_checks.AdminChannelError):
            logger.error(
                f"Command '{interaction.command.name}' attempted in non-admin channel"
                f" ({interaction.guild.name})."
            )
            admin_channel_id = await snorlax_db.get_guild_admin_channel(
                interaction.guild.id
            )
            embed = get_admin_channel_embed(admin_channel_id)
            if interaction.command.name == "create-schedule":
                embed.set_footer(
                    text=(
                        "Does not apply when '/schedules create-schedule' is used to"
                        " create a schedule for the channel where the command is"
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
                            (
                                "Permission error! Snorlax is missing the following"
                                " permissions to create a time"
                                f" channel:\n`{', '.join(error.missing_permissions)}`"
                                " (`connect` may also be required)."
                            ),
                        ),
                        msg_type="error",
                    )

                    await interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    embed = get_message_embed(
                        "You can't use that here.", msg_type="error"
                    )

                    await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                embed = get_message_embed("You can't use that here.", msg_type="error")

                await interaction.response.send_message(embed=embed, ephemeral=True)

        elif isinstance(
            error, app_commands.errors.CommandInvokeError
        ) and "Missing Permissions" in str(error):
            err_embed = get_message_embed(
                (
                    "A permissions error has occurred. Does Snorlax have the correct"
                    " permissions?"
                ),
                msg_type="error",
            )
            await interaction.response.send_message(embed=err_embed, ephemeral=True)
            logger.error(error, exc_info=True)
        else:
            err_embed = get_message_embed(
                "Unexpected error occurred, contact administrator.", msg_type="error"
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
        ok = await snorlax_db.add_guild_admin_channel(guild, channel)
        if ok:
            embed = get_message_embed(
                f"{channel.mention} set as the Snorlax admin channel successfully.",
                msg_type="success",
            )
        else:
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
        ok = await snorlax_db.add_guild_log_channel(guild, channel)
        if ok:
            embed = get_message_embed(
                f"{channel.mention} set as the Snorlax log channel successfully.",
                msg_type="success",
            )
        else:
            embed = get_message_embed(
                "Error when setting the log channel.", msg_type="success"
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
        ok = await snorlax_db.add_guild_meowth_raid_category(guild, category)
        if ok:
            msg = (
                f"**{cat_name.upper()}** set as the Pokenav raid category successfully."
                " Make sure Snorlax has the correct permissions!"
            )
            embed = get_message_embed(msg, msg_type="success")
        else:
            embed = get_message_embed(
                "Error when setting the Pokenav raid channel.", msg_type="error"
            )

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
        ok = await snorlax_db.add_guild_meowth_raid_category(guild)
        if ok:
            embed = get_message_embed(
                "Pokenav raid category has been reset.", msg_type="success"
            )
        else:
            embed = get_message_embed(
                "Error when setting the Pokenav raid channel.", msg_type="error"
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
        ok = await snorlax_db.add_guild_tz(interaction.guild, tz)
        if ok:
            embed = get_message_embed(
                f"{tz} set as the timezone successfully.", msg_type="success"
            )
        else:
            embed = get_message_embed(
                "Error when setting the timezone.", msg_type="error"
            )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="set-prefix",
        description="Set the prefix for the server. Will soon be deprecated.",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.check(snorlax_checks.check_admin_channel)
    @app_commands.checks.has_permissions(administrator=True)
    async def setPrefix(self, interaction: discord.Interaction, prefix: str) -> None:
        """Sets the command prefix for a guild.

        Will soon be deprecated.

        Args:
            interaction: The interaction that triggered the request.
            prefix: The prefix to use. Must be 3 or less characters in length!

        Returns:
            None
        """
        guild_id = interaction.guild.id

        if len(prefix) > 3:
            embed = get_message_embed(
                "Prefix must be 3 or less characters.", msg_type="warning"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        ok = await snorlax_db.set_guild_prefix(guild_id, prefix)
        if ok:
            embed = get_message_embed(
                f"`{prefix}` set as the prefix for Snorlax successfully.",
                msg_type="success",
            )
        else:
            embed = get_message_embed(
                "Error when setting the prefix.", msg_type="error"
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
        guild_db = await snorlax_db.load_guild_db()
        if guild_id not in guild_db.index:
            await interaction.response.send_message(
                embed=get_message_embed(
                    "Settings have not been configured for this guild.",
                    msg_type="error",
                ),
                ephemeral=True,
            )
        else:
            guild_settings = guild_db.loc[guild_id]
            guild_schedule_settings = await snorlax_db.load_guild_schedule_settings(
                guild_id
            )
            if guild_schedule_settings.empty:
                await interaction.response.send_message(
                    embed=get_message_embed(
                        "Guild schedule settings failed to load! Contact admin.",
                        msg_type="error",
                    ),
                    ephemeral=True,
                )
            else:
                embed = get_settings_embed(
                    interaction.guild, guild_settings, guild_schedule_settings
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
        if await snorlax_checks.check_guild_exists(guild.id):
            logger.info(f"Setting guild {guild.name} to active.")
            await snorlax_db.set_guild_active(guild.id, 1)

            # Then go through admin_channel, log_channel, time_channel, schedules
            # and raid category to see if the channels still exist.
            # Reset or drop if they don't.
            admin_channel_id = await snorlax_db.get_guild_admin_channel(guild.id)
            if admin_channel_id != -1:
                admin_channel = get(guild.channels, id=int(admin_channel_id))
                if admin_channel is None:
                    logger.warning(
                        f"Admin channel not found for {guild.name}, resetting."
                    )
                    await snorlax_db.add_guild_admin_channel(guild)

            log_channel_id = await snorlax_db.get_guild_log_channel(guild.id)
            if log_channel_id != -1:
                log_channel = get(guild.channels, id=int(log_channel_id))
                if log_channel is None:
                    logger.warning(
                        f"Log channel not found for {guild.name}, resetting."
                    )
                    await snorlax_db.add_guild_log_channel(guild)

            time_channel_id = await snorlax_db.get_guild_time_channel(guild.id)
            if time_channel_id != -1:
                time_channel = get(guild.channels, id=int(time_channel_id))
                if time_channel is None:
                    logger.warning(
                        f"Time channel not found for {guild.name}, resetting."
                    )
                    await snorlax_db.add_guild_time_channel(guild)

            raid_category_id = await snorlax_db.get_guild_raid_category(guild.id)
            if raid_category_id != -1:
                raid_category = get(guild.categories, id=int(raid_category_id))
                if raid_category is None:
                    logger.warning(
                        f"Raid category not found for {guild.name}, resetting."
                    )
                    await snorlax_db.add_guild_meowth_raid_category(guild)

            # Check for schedule settings and create if not found.
            guild_schedule_settings = await snorlax_db.load_guild_schedule_settings(
                guild.id
            )
            if guild_schedule_settings.empty:
                await snorlax_db.add_default_schedule_settings(guild.id)

            schedules = await snorlax_db.load_schedule_db(guild_id=guild.id)
            if not schedules.empty:
                for _, row in schedules.iterrows():
                    sched_channel_id = row["channel"]
                    sched_channel = get(guild.channels, id=int(sched_channel_id))
                    if sched_channel is None:
                        logger.warning(
                            f"Dropping schedule {row['rowid']} in {guild.name} as"
                            " channel not found."
                        )
                        await snorlax_db.drop_schedule(row["rowid"])

        # if not then create the new entry in the db
        else:
            logger.info(f"Adding {guild.name} to database.")
            await snorlax_db.add_guild(guild)
            # create admin channel
            overwrites = {}

            bot_role = guild.self_role
            overwrites[bot_role] = discord.PermissionOverwrite(
                read_messages=True, send_messages=True
            )

            # block everybody from viewing channel
            default_role = guild.default_role
            overwrites[default_role] = discord.PermissionOverwrite(read_messages=False)

            admin_channel = await guild.create_text_channel(
                "snorlax-admin",
                overwrites=overwrites,
                reason="Admin channel for the snorlax bot.",
            )

            await snorlax_db.add_guild_admin_channel(guild, admin_channel)

            # Create schedules settings
            await snorlax_db.add_default_schedule_settings(guild.id)

            welcome_message = (
                "This is where admin commands for Snorlax can be used.\n\nIf you would"
                " like to use an existing channel instead, use the the '/admin"
                " set-admin-channel' slash command to change it.\n\nAvailable commands"
                " can be seen using the slash command interface.\n\nBelow are the"
                " default settings for the server."
            )

            welcome_embed = get_message_embed(
                welcome_message, msg_type="info", title="Hello!"
            )

            guild_db = await snorlax_db.load_guild_db(active_only=True)
            guild_settings = guild_db.loc[int(guild.id)]
            guild_schedule_settings = await snorlax_db.load_guild_schedule_settings(
                guild.id
            )
            embed = get_settings_embed(guild, guild_settings, guild_schedule_settings)

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
        if await snorlax_checks.check_guild_exists(guild.id):
            logger.info(f"Setting guild {guild.name} to not active.")
            # Set guild to inactive
            await snorlax_db.set_guild_active(guild.id, 0)
            # Check for schedules and deactivate them all
            schedules = await snorlax_db.load_schedule_db(guild_id=guild.id)
            if not schedules.empty:
                logger.info(f"Deactivating all schedules for {guild.name}.")
                for rowid in schedules["rowid"]:
                    await snorlax_db.update_schedule(
                        schedule_id=rowid, column="active", value=False
                    )

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: GuildChannel) -> None:
        """Checks on a channel deletion whether the channel was the log channel.

        Args:
            channel: The deleted channel object.

        Returns:
            None
        """
        admin_channel = await snorlax_db.get_guild_admin_channel(channel.guild.id)

        if admin_channel == channel.id:
            await snorlax_db.add_guild_admin_channel(channel.guild)
            logger.info(f"admin channel reset for guild {channel.guild.name}.")

        log_channel = await snorlax_db.get_guild_log_channel(channel.guild.id)

        if log_channel == channel.id:
            await snorlax_db.add_guild_log_channel(channel.guild)
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
