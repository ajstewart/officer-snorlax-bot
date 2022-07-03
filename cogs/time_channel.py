"""The time channel cog.
"""
import asyncio
import datetime
import discord
import logging


from discord.ext import commands, tasks
from discord import app_commands
from discord.abc import GuildChannel
from discord.utils import get
from discord.errors import DiscordServerError, Forbidden
from typing import Optional

from .utils import checks as snorlax_checks
from .utils import utils as snorlax_utils
from .utils import db as snorlax_db
from .utils.log_msgs import time_channel_reset_log_embed


logger = logging.getLogger()


class TimeChannel(commands.Cog):
    """
    The cog that manages all aspects of the Time channel, for which there
    can be one per server.
    """
    def __init__(self, bot: commands.bot) -> None:
        """
        The initialisation method.

        Args:
            bot: The discord.py bot representation.

        Returns:
            None
        """
        super(TimeChannel, self).__init__()
        self.bot = bot
        self.time_channels_manager.add_exception_type(
            DiscordServerError,
            Forbidden
        )
        self.time_channels_manager.start()

    @app_commands.command(
        name='create-time-channel',
        description=(
            'Create a voice channel that will display the local time (according to the '
            'server timezone setting.'
        )
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.checks.has_permissions(administrator=True)
    # TODO: Add connect back in
    @app_commands.checks.bot_has_permissions(manage_channels=True)
    async def createTimeChannel(
        self,
        interaction: discord.Interaction,
        category: Optional[discord.CategoryChannel] = None
    ) -> None:
        """Creates a voice channel that will display the local server time.

        Time is determined using the set server timezone.

        Args:
            interaction: The interaction containing the request.
        """
        # Check if time channel already exists.
        time_channel_id = await snorlax_db.get_guild_time_channel(interaction.guild.id)

        if time_channel_id != -1:
            time_channel = self.bot.get_channel(time_channel_id)
            await interaction.response.send_message(
                f'Time channel {time_channel.mention} already exists!'
                ' Delete this channel before creating a new one.'
            )

        else:
            overwrites = {}

            # Give bot permission to connect to channel
            bot_role = interaction.guild.self_role
            overwrites[bot_role] = discord.PermissionOverwrite(
                connect=True
            )

            # block everybody from connecting
            default_role = interaction.guild.default_role
            overwrites[default_role] = discord.PermissionOverwrite(
                connect=False
            )

            time_channel = await interaction.guild.create_voice_channel(
                'temp-time-channel',
                overwrites=overwrites,
                category=category,
                reason='Channel created for Snorlax to display time.'
            )

            ok = await snorlax_db.add_guild_time_channel(interaction.guild, time_channel)

            if ok:
                msg = (
                    "{} set as the Snorlax time channel successfully."
                    " The time is updated every 10 minutes.".format(
                        time_channel.mention
                    )
                )
            else:
                msg = (
                    "Error when setting the time channel."
                )

            await interaction.response.send_message(msg, ephemeral=True)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: GuildChannel) -> None:
        """
        Checks on a channel deletion whether the channel was the time channel.

        Args:
            channel: The deleted channel object.

        Returns:
            None
        """
        guild_id = channel.guild.id

        if channel.id == await snorlax_db.get_guild_time_channel(guild_id):
            # No channel entry resets the time channel.
            ok = await snorlax_db.add_guild_time_channel(channel.guild)
            if ok:
                log_channel = await snorlax_db.get_guild_log_channel(channel.guild.id)
                if log_channel != -1:
                    log_channel = get(channel.guild.channels, id=int(log_channel))
                    log_embed = time_channel_reset_log_embed(channel)
                    await log_channel.send(embed=log_embed)
                logger.info(f'Time channel reset for guild {channel.guild.name}.')

    @tasks.loop(minutes=10)
    async def time_channels_manager(self) -> None:
        """
        The main time channel loop to update the time of the channel by
        updating the channel name.

        Returns:
            None
        """
        guild_db = await snorlax_db.load_guild_db(active_only=True)

        # check if there are actually any time channels set
        guild_db = guild_db.loc[guild_db['time_channel'] != -1]
        if not guild_db.empty:
            for tz in guild_db['tz'].unique():
                guilds = guild_db.loc[guild_db['tz'] == tz]

                now = snorlax_utils.get_current_time(tz=tz)

                for i in guilds['time_channel']:
                    try:
                        time_channel_id = int(i)
                        time_channel = self.bot.get_channel(time_channel_id)

                        new_name = now.strftime("%I:%M %p %Z")
                        new_name = snorlax_utils.get_hour_emoji(new_name[:5]) + " " + new_name

                        await time_channel.edit(name=new_name)

                        logger.info(
                            f'Updated time channel in {time_channel.guild.name}')
                    except Exception as e:
                        logger.error(
                            'Updating the time channel for '
                            f'{time_channel.guild.name} failed.'
                            ' Are the permissions correct?'
                        )
                        logger.error(f'Error: {e}')
        else:
            logger.warning('No time channels set skipping loop.')

    @time_channels_manager.before_loop
    async def before_timer(self):
        """
        Method to process before the time channel manager loop is started.

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
            f'Waiting {sleep_time} seconds to start the time channel manager loop.'
        )

        await asyncio.sleep(sleep_time)


async def setup(bot: commands.bot) -> None:
    """The setup function to initiate the cog.

    Args:
        bot: The bot for which the cog is to be added.
    """
    if bot.test_guild is not None:
        await bot.add_cog(
            TimeChannel(bot),
            guild=discord.Object(id=bot.test_guild)
        )
    else:
        await bot.add_cog(TimeChannel(bot))
