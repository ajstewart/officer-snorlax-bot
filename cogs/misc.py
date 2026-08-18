"""The misc cog which contains miscellaneous commands."""

import discord

from discord import app_commands
from discord.ext import commands
from dotenv import find_dotenv, load_dotenv

from bot_logger import get_logger
from repositories import GuildRepository, ScheduleRepository

from .utils import checks as snorlax_checks
from .utils.embeds import get_message_embed, get_schedule_embed_for_user
from .utils.utils import get_current_time, get_hour_emoji

logger = get_logger(__name__)
load_dotenv(find_dotenv())


class Miscellaneous(commands.Cog):
    """Cog for the miscellaneous commands."""

    def __init__(self, bot: commands.bot) -> None:
        """Init method for management.

        Args:
            bot: The discord.py bot representation.

        Returns:
            None.
        """
        super(Miscellaneous, self).__init__()
        self.bot = bot

    @app_commands.command(
        name="current-time", description="Shows the current local time for the guild."
    )
    @app_commands.check(snorlax_checks.interaction_check_bot)
    async def currentTime(self, interaction: discord.Interaction) -> None:
        """Command to ask the bot to send a message containing the current time.

        Args:
            interaction: The interaction that triggered the request.

        Returns:
            None
        """
        async with self.bot.db_session() as session:
            guild_repo = GuildRepository(session)
            guild_db = await guild_repo.get(interaction.guild.id)
        guild_tz = guild_db.tz
        the_time = get_current_time(guild_tz)
        emoji = get_hour_emoji(the_time.strftime("%I:%M"))
        msg = f"{emoji} **{the_time.strftime('%I:%M %p %Z')}**."

        embed = get_message_embed(msg=msg, msg_type="info")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="ping", description="Get a pong!")
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.checks.has_permissions(administrator=True)
    async def ping(self, interaction: discord.Interaction) -> None:
        """Command to return a pong to a ping.

        Args:
            interaction: The interaction that triggered the request.

        Returns:
            None
        """
        embed = get_message_embed("Pong!", msg_type="info")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="show-schedule",
        description="Display the schedule for the current channel.",
    )
    @app_commands.check(snorlax_checks.interaction_check_bot)
    async def schedule(self, interaction: discord.Interaction) -> None:
        """Communicates the schedule for the current channel to the user.

        Args:
            interaction: The interaction that triggered the request.

        Returns:
            None
        """
        async with self.bot.db_session() as session:
            schedule_repo = ScheduleRepository(session)
            schedule = await schedule_repo.get_by_channel(
                channel_id=interaction.channel.id
            )

        embed = get_schedule_embed_for_user(schedule, interaction.channel)

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.bot) -> None:
    """The setup function to initiate the cog.

    Args:
        bot: The bot for which the cog is to be added.
    """
    if bot.test_guild is not None:
        await bot.add_cog(Miscellaneous(bot), guild=discord.Object(id=bot.test_guild))
    else:
        await bot.add_cog(Miscellaneous(bot))
