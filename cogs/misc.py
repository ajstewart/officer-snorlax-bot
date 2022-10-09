"""
The misc cog which contains miscellaneous commands.
"""
import discord
import os
import logging

from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv, find_dotenv

from .utils import checks as snorlax_checks
from .utils import db as snorlax_db
from .utils.embeds import get_schedule_embed_for_user, get_message_embed
from .utils.utils import get_current_time, get_hour_emoji


logger = logging.getLogger()
load_dotenv(find_dotenv())


class Miscellaneous(commands.Cog):
    """
    Cog for the miscellaneous commands.
    """
    def __init__(self, bot: commands.bot) -> None:
        """
        Init method for management.

        Args:
            bot: The discord.py bot representation.

        Returns:
            None.
        """
        super(Miscellaneous, self).__init__()
        self.bot = bot

    @app_commands.command(
        name='current-time',
        description="Shows the current local time for the guild."
    )
    @app_commands.check(snorlax_checks.interaction_check_bot)
    async def currentTime(self, interaction: discord.Interaction) -> None:
        """
        Command to ask the bot to send a message containing the current time.

        Args:
            interaction: The interaction that triggered the request.

        Returns:
            None
        """
        guild_tz = await snorlax_db.get_guild_tz(interaction.guild.id)
        the_time = get_current_time(guild_tz)
        emoji = get_hour_emoji(the_time.strftime("%I:%M"))
        msg = f"{emoji} **{the_time.strftime('%I:%M %p %Z')}**."

        embed = get_message_embed(msg=msg, msg_type='info')

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name='ping',
        description="Get a pong!"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.checks.has_permissions(administrator=True)
    async def ping(self, interaction: discord.Interaction) -> None:
        """
        Command to return a pong to a ping.

        Args:
            interaction: The interaction that triggered the request.

        Returns:
            None
        """
        await interaction.response.send_message("Pong!", ephemeral=True)

    @app_commands.command(
        name='show-schedule',
        description="Display the schedule for the current channel."
    )
    @app_commands.check(snorlax_checks.interaction_check_bot)
    async def schedule(self, interaction: discord.Interaction) -> None:
        """
        Communicates the schedule for the current channel to the user.

        Args:
            interaction: The interaction that triggered the request.

        Returns:
            None
        """
        schedule_df = await snorlax_db.load_schedule_db(
            guild_id=interaction.guild.id,
            active=True
        )

        schedule_df = schedule_df.loc[schedule_df['channel'] == interaction.channel.id]

        embed = get_schedule_embed_for_user(schedule_df, interaction.channel)

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.bot) -> None:
    """The setup function to initiate the cog.

    Args:
        bot: The bot for which the cog is to be added.
    """
    if bot.test_guild is not None:
        await bot.add_cog(
            Miscellaneous(bot),
            guild=discord.Object(id=bot.test_guild)
        )
    else:
        await bot.add_cog(Miscellaneous(bot))
