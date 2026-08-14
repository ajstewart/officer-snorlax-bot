"""The time channel cog."""

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
from repositories import GuildRepository

from .utils import checks as snorlax_checks
from .utils import utils as snorlax_utils
from .utils.embeds import get_message_embed
from .utils.log_msgs import time_channel_reset_log_embed

logger = get_logger(__name__)


@app_commands.default_permissions(administrator=True)
class TimeChannel(commands.Cog):
    """The cog that manages all aspects of the Time channel.

    There can be one per server.
    """

    def __init__(self, bot: commands.bot) -> None:
        """The initialisation method.

        Args:
            bot: The discord.py bot representation.

        Returns:
            None
        """
        super(TimeChannel, self).__init__()
        self.bot = bot
        self.time_channels_manager.add_exception_type(DiscordServerError, Forbidden)
        self.time_channels_manager.start()

    @app_commands.command(
        name="create-time-channel",
        description=(
            "Create a voice channel that will display the local time (according to the "
            "server timezone setting."
        ),
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.check(snorlax_checks.check_admin_channel)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.checks.bot_has_permissions(manage_channels=True, connect=True)
    async def createTimeChannel(
        self,
        interaction: discord.Interaction,
        category: Optional[discord.CategoryChannel] = None,
    ) -> None:
        """Creates a voice channel that will display the local server time.

        Time is determined using the set server timezone.

        Args:
            interaction: The interaction containing the request.
            category: The category to create the channel in.
        """
        async with self.bot.db_session() as session:
            guild_repo = GuildRepository(session)
            guild_db = await guild_repo.get(interaction.guild.id)
            # Check if time channel already exists.
            time_channel_id = guild_db.time_channel

            if time_channel_id != -1:
                time_channel = self.bot.get_channel(time_channel_id)

                msg = (
                    f"Time channel {time_channel.mention} already exists!"
                    " Delete this channel before creating a new one."
                )
                embed = get_message_embed(msg, msg_type="warning")
                await interaction.response.send_message(embed=embed)

            else:
                overwrites = {}

                # Give bot permission to connect to channel
                bot_role = interaction.guild.self_role
                overwrites[bot_role] = discord.PermissionOverwrite(connect=True)

                # block everybody from connecting
                default_role = interaction.guild.default_role
                overwrites[default_role] = discord.PermissionOverwrite(connect=False)

                time_channel = await interaction.guild.create_voice_channel(
                    "temp-time-channel",
                    overwrites=overwrites,
                    category=category,
                    reason="Channel created for Snorlax to display time.",
                )

                try:
                    guild_db.time_channel = time_channel.id

                    msg = (
                        f"{time_channel.mention} set as the Snorlax time channel"
                        " successfully. The time is updated every 10 minutes."
                    )
                    embed = get_message_embed(msg, msg_type="success")
                except Exception:
                    msg = "Error when setting the time channel."
                    embed = get_message_embed(msg, msg_type="error")

                await interaction.response.send_message(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: GuildChannel) -> None:
        """Checks on a channel deletion whether the channel was the time channel.

        Args:
            channel: The deleted channel object.

        Returns:
            None
        """
        guild_id = channel.guild.id

        async with self.bot.db_session() as session:
            guild_repo = GuildRepository(session)
            guild_db = await guild_repo.get(guild_id)

            if channel.id == guild_db.time_channel:
                # No channel entry resets the time channel.
                guild_db.time_channel = -1
                log_channel = guild_db.log_channel
                if log_channel != -1:
                    log_channel = get(channel.guild.channels, id=int(log_channel))
                    log_embed = time_channel_reset_log_embed(channel)
                    await log_channel.send(embed=log_embed)
                logger.info(f"Time channel reset for guild {channel.guild.name}.")

    async def set_time_channel_name(self, time_channel_id: int, guild_tz: str) -> None:
        """Sets the name of the time channel to the current time.

        Args:
            time_channel_id: The ID of the time channel.
            guild_tz: The timezone of the guild.

        Returns:
            None
        """
        time_channel = self.bot.get_channel(time_channel_id)
        now = snorlax_utils.get_current_time(tz=guild_tz)

        new_name = now.strftime("%I:%M %p %Z")
        new_name = snorlax_utils.get_hour_emoji(new_name[:5]) + " " + new_name

        try:
            await time_channel.edit(name=new_name)
            logger.info(f"Updated time channel in {time_channel.guild.name}")
        except Exception as e:
            logger.exception(
                f"Updating the time channel for {time_channel.guild.name} failed."
                " Are the permissions correct?"
            )
            raise e

    @tasks.loop(minutes=10)
    async def time_channels_manager(self) -> None:
        """The main time channel loop to update the time.

        Does so by updating the channel name.

        Returns:
            None
        """
        async with self.bot.db_session() as session:
            guild_repo = GuildRepository(session)
            active_guilds = await guild_repo.get_all(active_only=True)

            # check if there are actually any time channels set
            time_channel_guilds = [g for g in active_guilds if g.time_channel != -1]
            tasks = [
                self.set_time_channel_name(g.time_channel, g.tz)
                for g in time_channel_guilds
            ]
            await asyncio.gather(*tasks, return_exceptions=True)

    @time_channels_manager.before_loop
    async def before_timer(self):
        """Method to process before the time channel manager loop is started.

        The purpose is to make sure the loop is started at the top of an even
        ten minutes.

        Returns:
            None
        """
        await self.bot.wait_until_ready()
        # Make sure the loop starts at the top of a ten minute interval
        now = datetime.datetime.now()
        mins = int(now.strftime("%M")[-1:])
        sleep_time = (10 - mins) * 60
        sleep_time -= now.second
        logger.info(
            f"Waiting {sleep_time} seconds to start the time channel manager loop."
        )

        await asyncio.sleep(sleep_time)


async def setup(bot: commands.bot) -> None:
    """The setup function to initiate the cog.

    Args:
        bot: The bot for which the cog is to be added.
    """
    if bot.test_guild is not None:
        await bot.add_cog(TimeChannel(bot), guild=discord.Object(id=bot.test_guild))
    else:
        await bot.add_cog(TimeChannel(bot))
