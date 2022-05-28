"""
Cog for the join name filter.
"""

import discord
import os
import logging

from discord.ext import commands
from discord import Forbidden, Member
from discord.utils import get
from dotenv import load_dotenv, find_dotenv

from .utils.db import (
    load_guild_db,
)
from .utils.log_msgs import ban_log_embed


load_dotenv(find_dotenv())
BAN_NAMES = os.getenv('BAN_NAMES').split(",")
logger = logging.getLogger()


class JoinNameFilter(commands.Cog):
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
        guild_db = load_guild_db()

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
    if bot.guild_server is not None:
        await bot.add_cog(
            JoinNameFilter(bot),
            guild=discord.Object(id=bot.guild_server)
        )
    else:
        await bot.add_cog(JoinNameFilter(bot))
