"""
Cog for the join name filter.
"""

import discord
import os
import logging

from discord.ext import commands
from discord import Forbidden, Member, app_commands
from discord.utils import get
from dotenv import load_dotenv, find_dotenv

from .utils import checks as snorlax_checks
from .utils import db as snorlax_db
from .utils.embeds import get_message_embed
from .utils.log_msgs import ban_log_embed


load_dotenv(find_dotenv())
BAN_NAMES = os.getenv('BAN_NAMES').split(",")
logger = logging.getLogger()


@app_commands.default_permissions(administrator=True)
class JoinNameFilter(commands.GroupCog, name="join-name-filter"):
    """
    Cog for immediately banning a user that joins the server that matches a
    specified name.
    """
    def __init__(self, bot: commands.bot) -> None:
        """
        The initialisation method.

        Args:
            bot: The discord.py bot representation.

        Returns:
            None
        """
        super(JoinNameFilter, self).__init__()
        self.bot = bot

    @app_commands.command(
        name='activate',
        description="Turns on the 'join name' filter."
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.check(snorlax_checks.check_admin_channel)
    @app_commands.checks.has_permissions(administrator=True)
    async def activateJoinNameFilter(self, interaction: discord.Interaction) -> None:
        """
        Command to activate the join name filter.

        Args:
            interaction: The interaction that triggered the request.

        Returns:
            None
        """
        join_filter = snorlax_db.get_guild_join_name_active(interaction.guild.id)
        if join_filter:
            msg = "The 'join name' filter is already activated."
            embed = get_message_embed(msg, msg_type='warning')
            ephemeral = True
        else:
            ok = await snorlax_db.toggle_join_name_filter(interaction.guild, True)
            if ok:
                msg = "'Join name' filter activated."
                embed = get_message_embed(msg, msg_type='success')
                ephemeral = False
            else:
                msg = "Error when attempting to activate the 'Join name' filter"
                embed = get_message_embed(msg, msg_type='error')
                ephemeral = True

        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)

    @app_commands.command(
        name='deactivate',
        description="Turns off the 'join name' filter."
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.check(snorlax_checks.check_admin_channel)
    @app_commands.checks.has_permissions(administrator=True)
    async def deactivateJoinNameFilter(self, interaction: discord.Interaction) -> None:
        """
        Command to deactivate the join name filter.

        Args:
            interaction: The interaction that triggered the request.

        Returns:
            None
        """
        join_filter = snorlax_db.get_guild_join_name_active(interaction.guild.id)
        if not join_filter:
            msg = "The 'join name' filter is already deactivated."
            embed = get_message_embed(msg, msg_type='warning')
            ephemeral = True
        else:
            ok = await snorlax_db.toggle_join_name_filter(interaction.guild, False)
            if ok:
                msg = "'Join name' filter deactivated."
                embed = get_message_embed(msg, msg_type='success')
                ephemeral = False
            else:
                msg = "Error when attempting to deactivate the 'Join name' filter"
                embed = get_message_embed(msg, msg_type='error')
                ephemeral = True

        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)

    # Handle new members
    @commands.Cog.listener()
    async def on_member_join(self, member: Member) -> None:
        """
        The main method that checks for and then bans any new members that
        match a name provided.

        Names are defined in the dotenv settings file.

        Args:
            member: The member object of the user who has joined.

        Returns:
            None
        """
        member_guild_id = member.guild.id
        member_guild_name = member.guild.name
        guild_db = await snorlax_db.load_guild_db()

        if guild_db.loc[member.guild.id]['join_name_filter']:

            for pattern in BAN_NAMES:
                if pattern.lower() in member.name.lower():
                    try:
                        await member.ban(
                            reason="Triggered Snorlax name pattern detection."
                        )
                        logger.info(
                            f'Banned member {member.name}'
                            f' from {member_guild_name}'
                        )
                        log_channel_id = (
                            guild_db.loc[member_guild_id]['log_channel']
                        )
                        if log_channel_id != -1:
                            tz = guild_db.loc[member_guild_id]['tz']
                            log_channel = get(
                                member.guild.channels, id=int(log_channel_id)
                            )
                            embed = ban_log_embed(
                                member,
                                tz,
                                f"Name filter matched with '{pattern}'."
                            )
                            await log_channel.send(embed=embed)
                    except Forbidden:
                        logger.error(
                            f'Failed to ban member {member.name}'
                            f' from {member_guild_name}'
                        )


async def setup(bot: commands.bot) -> None:
    """The setup function to initiate the cog.

    Args:
        bot: The bot for which the cog is to be added.
    """
    if bot.test_guild is not None:
        await bot.add_cog(
            JoinNameFilter(bot),
            guild=discord.Object(id=bot.test_guild)
        )
    else:
        await bot.add_cog(JoinNameFilter(bot))
