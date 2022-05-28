from discord.ext import commands, tasks
from discord import VoiceChannel
import logging
import datetime
import discord
import asyncio
from discord.utils import get
from .utils.checks import (
    check_admin,
    check_admin_channel,
    check_bot,
)
from .utils.utils import get_current_time, get_hour_emoji
from .utils.db import add_guild_time_channel, load_guild_db
from discord.errors import DiscordServerError, Forbidden


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

    @commands.command(
        help=(
            "Activates a channel as a 'time channel'. Which means the channel"
            " will become purely a channel to display the current local time"
            " in the channel name."
        ),
        brief="Set a channel as the time channel."
    )
    @commands.check(check_bot)
    @commands.check(check_admin)
    @commands.check(check_admin_channel)
    async def setTimeChannel(
        self,
        ctx: commands.context,
        channel: VoiceChannel
    ) -> None:
        """
        Command to set the time channel for the server.

        Args:
            ctx: The command context containing the message content and other
                metadata.
            channel: The voice channel to set as the time channel.

        Returns:
            None
        """
        guild = ctx.guild
        ok = add_guild_time_channel(guild, channel)
        if ok:
            msg = (
                "{} set as the Snorlax time channel successfully."
                " Make sure Snorlax has the correct permissions!".format(
                    channel.mention
                )
            )
            # Make sure the channel permissions are set
            role = ctx.guild.default_role
            overwrites = channel.overwrites_for(role)
            overwrites.connect = False
            await channel.set_permissions(role, overwrite=overwrites)
        else:
            msg = (
                "Error when setting the time channel."
            )

        await ctx.channel.send(msg)

    @setTimeChannel.error
    async def setTimeChannel_error(self, ctx: commands.context, error) -> None:
        """
        Handles any error from setTimeChannel.

        Args:
            ctx: The command context containing the message content and other
                metadata.
            error (Exception): The actual exception that could be a range of
                error types.

        Returns:
            None
        """
        if isinstance(error, commands.BadArgument):
            await ctx.send(
                'Channel not found. Hint: It must be a voice channel!'
            )

    @tasks.loop(minutes=10)
    async def time_channels_manager(self) -> None:
        """
        The main time channel loop to update the time of the channel by
        updating the channel name.

        Returns:
            None
        """
        client_user = self.bot.user
        guild_db = load_guild_db()

        # check if there are actually any time channels set
        guild_db = guild_db.loc[guild_db['time_channel'] != -1]
        if not guild_db.empty:
            for tz in guild_db['tz'].unique():
                guilds = guild_db.loc[guild_db['tz'] == tz]

                now = get_current_time(tz=tz)

                for i in guilds['time_channel']:
                    try:
                        time_channel_id = int(i)
                        time_channel = self.bot.get_channel(time_channel_id)

                        new_name = now.strftime("%I:%M %p %Z")
                        new_name = get_hour_emoji(new_name[:5]) + " " + new_name

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
