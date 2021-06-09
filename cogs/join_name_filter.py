from discord.ext import commands
from discord import TextChannel, Forbidden
from typing import Optional
import os
import discord
import logging
from discord.utils import get
from .utils.checks import (
    check_admin,
    check_admin_channel,
    check_time_format,
    check_for_friend_code,
    check_bot,
    check_for_any_raids
)
from .utils.db import (
    load_guild_db,
    load_friend_code_channels_db,
    add_allowed_friend_code_channel,
    drop_allowed_friend_code_channel
)
from .utils.log_msgs import ban_log_embed
from .utils.utils import get_friend_channels_embed
from dotenv import load_dotenv, find_dotenv


load_dotenv(find_dotenv())
BAN_NAMES = os.getenv('BAN_NAMES').split(",")
logger = logging.getLogger()


class JoinNameFilter(commands.Cog):
    """docstring for Initial"""
    def __init__(self, bot):
        super(JoinNameFilter, self).__init__()
        self.bot = bot

    ## Handle new members
    @commands.Cog.listener()
    async def on_member_join(self, member):
        member_guild_id = member.guild.id
        member_guild_name = member.guild.name
        guild_db = load_guild_db()

        if guild_db.loc[member.guild.id]['join_name_filter'] == True:

            for pattern in BAN_NAMES:
                if pattern.lower() in member.name.lower():
                    try:
                        await member.ban(reason="Triggered Snorlax name pattern detection.")
                        logger.info(
                            f'Banned member {member.name} from {member_guild_name}'
                        )
                        log_channel_id = guild_db.loc[member_guild_id]['log_channel']
                        if log_channel_id != -1:
                            tz = guild_db.loc[member_guild_id]['tz']
                            log_channel = get(
                                member.guild.channels, id=int(log_channel_id)
                            )
                            embed = ban_log_embed(member, tz, f"Name filter matched with '{pattern}'.")
                            await log_channel.send(embed=embed)
                    except Forbidden:
                        logger.error(
                            f'Failed to ban member {member.name} from {member_guild_name}'
                        )