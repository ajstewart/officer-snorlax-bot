"""
Misc. utility functions used throughout the bot.
"""

import pytz
import datetime
import os
import re
import logging
import string
import pandas as pd

from discord import Client, Embed, Message, User
from discord.ext import commands
from dotenv import load_dotenv, find_dotenv
from typing import Callable, List, Optional


load_dotenv(find_dotenv())
DEFAULT_OPEN_MESSAGE = os.getenv('DEFAULT_OPEN_MESSAGE')
DEFAULT_CLOSE_MESSAGE = os.getenv('DEFAULT_CLOSE_MESSAGE')
WARNING_TIME = os.getenv('WARNING_TIME')
INACTIVE_TIME = os.getenv('INACTIVE_TIME')
DELAY_TIME = os.getenv('DELAY_TIME')


def get_current_time(tz: str) -> datetime.datetime:
    """
    Returns the current time in the selected time zone.

    Args:
        tz: The requested timezone.

    Returns:
        The current time as a datetime.datetime object.
    """
    tz = pytz.timezone(tz)
    return datetime.datetime.now(tz=tz)


def get_schedule_embed(
    ctx: commands.context,
    schedule_db: pd.DataFrame,
    tz: str
) -> Embed:
    """
    Create an embed to show the saved schedules.

    Args:
        ctx: The command context containing the message content and other
            metadata.
        schedule_db: The schedule database table as a pandas dataframe.
        tz: The guild timezone, e.g., 'Australia/Sydney'.

    Returns:
        The embed containing the list of schedules.
    """
    tz = pytz.timezone(tz)
    now = datetime.datetime.now(tz=tz)
    embed = Embed(
        title='Schedules',
        timestamp=now,
        color=2061822
    )
    for i, row in schedule_db.iterrows():
        embed.add_field(
            name='ID: {}'.format(row.rowid),
            value=(
                "Active: **{}**\n"
                "Channel: <#{}>\nOpen: **{}**\nOpen Custom Message: **{}**\n"
                "Close: **{}**\nClose Custom Message: **{}**"
                "\nWarning: **{}**\nDynamic: **{}**\n"
                "Max number of delays: **{}**\nSilent: **{}**".format(
                    row.active, row.channel, row.open, row.open_message,
                    row.close, row.close_message, row.warning, row.dynamic,
                    row.max_num_delays, row.silent
                )
            ).replace('True', '✅').replace('False', '❌'),
            inline=False
        )

    return embed


def get_friend_channels_embed(
    ctx: commands.context,
    friend_db: pd.DataFrame
) -> Embed:
    """
    Create an embed to show the allowed friend code channels.

    Args:
        ctx: The command context containing the message content and other
            metadata.
        friend_db: The friend channels database table as a pandas dataframe.

    Returns:
        The embed containing the list of friend channels.

    """
    embed = Embed(
        title='Friend Code Channels',
        color=1879160
    )

    value = ""
    for i, row in friend_db.iterrows():
        value += '<#{}> ({})\n'.format(
            row.channel, row.secret
        )
    embed.add_field(
        name="Allowed (secret)",
        value=value,
        inline=False
    )

    return embed


def get_settings_embed(
    ctx: commands.context,
    guild_settings: pd.DataFrame
) -> Embed:
    """
    Create an embed to show the settings of the bot on the guild the command
    was used from.

    Args:
        ctx: The command context containing the message content and other
            metadata.
        guild_settings: The guild settings database table as a pandas dataframe.

    Returns:
        The embed containing the guild settings.
    """
    if guild_settings['meowth_raid_category'] != -1:
        cat_name = ctx.guild.get_channel(
            guild_settings['meowth_raid_category']
        ).name
    else:
        cat_name = 'Not set'

    embed = Embed(
        title='Settings',
        color=16756290
    )

    log_channel_id = guild_settings['log_channel']
    if log_channel_id == -1:
        log_channel = "Not set"
    else:
        log_channel = "<#{}>".format(log_channel_id)

    time_channel_id = guild_settings['time_channel']
    if time_channel_id == -1:
        time_channel = "Not set"
    else:
        time_channel = "<#{}>".format(time_channel_id)

    embed.add_field(
        name="Guild Settings",
        value=(
            'TZ: **{}**\n'
            'Admin Channel: **<#{}>**\n'
            'Log Channel: **{}**\n'
            'Time Channel: **{}**\n'
            'Meowth Raid Category: **{}**\n'
            'Any raids filter: **{}**\n'
            'Join name filter: **{}**\n'
            'Prefix: **{}**'.format(
                guild_settings['tz'],
                guild_settings['admin_channel'],
                log_channel,
                time_channel,
                cat_name,
                guild_settings['any_raids_filter'],
                guild_settings['join_name_filter'],
                guild_settings['prefix']
            )
        ).replace('True', '✅').replace('False', '❌'),
        inline=False
    )

    embed.add_field(
        name="Bot Settings",
        value=(
            'Default Open Message: **{}**\n'
            'Default Close Message: **{}**\n'
            'Warning Time: **{}** min\n'
            'Inactive Time: **{}** min\n'
            'Delay Time: **{}** min'.format(
                DEFAULT_OPEN_MESSAGE,
                DEFAULT_CLOSE_MESSAGE,
                WARNING_TIME,
                INACTIVE_TIME,
                DELAY_TIME
            )
        ),
        inline=False
    )

    return embed


def get_logger(logfile: Optional[str] = None) -> logging.RootLogger:
    '''
    Set up the logger.

    Args:
        logfile: File to output log to.

    Returns:
        The root logger object.
    '''
    logger = logging.getLogger()
    s = logging.StreamHandler()
    if logfile is not None:
        fh = logging.FileHandler(logfile)
        fh.setLevel(logging.DEBUG)
    logformat = '[%(asctime)s] - %(levelname)s - %(message)s'

    formatter = logging.Formatter(logformat, datefmt="%Y-%m-%d %H:%M:%S")

    s.setFormatter(formatter)

    s.setLevel(logging.INFO)

    logger.addHandler(s)

    if logfile is not None:
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    logger.setLevel(logging.DEBUG)

    return logger


def strip_url(content: str) -> str:
    """
    Strip URLs from message string content.

    Args:
        content: The message content.

    Returns:
        The message content with URLs removed.
    """
    return re.sub(r'http\S+', '', content)


def strip_mentions(content: str) -> str:
    """
    Strip discord mentions from message string content.

    Args:
        content: The message content.

    Returns:
        The message content with mentions removed.
    """
    return re.sub(r'<(?:[^\d>]+|:[A-Za-z0-9]+:)\w+>', '', content)


def strip_punctuation(content: str) -> str:
    """
    Remove punctuation from the message content.

    Args:
        content: The message content.

    Returns:
        The message content with punctuation removed.
    """
    return content.translate(str.maketrans('', '', string.punctuation))


def get_hour_emoji(time: str) -> str:
    """
    Get the relevant emoji to represent the current time.

    Args:
        time: The time in 24h %H:%M format.

    Returns:
        The emoji for the current time.
    """
    hour, minute = time.split(":")

    if minute[:1] in ["0", "1", "2"]:
        minute = "00"
    else:
        minute = "30"

    key = f"{hour}:{minute}"

    emojis = {
        "01:00" : '🕐',
        "02:00" : '🕑',
        "03:00" : '🕒',
        "04:00" : '🕓',
        "05:00" : '🕔',
        "06:00" : '🕕',
        "07:00" : '🕖',
        "08:00" : '🕗',
        "09:00" : '🕘',
        "10:00" : '🕙',
        "11:00" : '🕚',
        "12:00" : '🕛',
        "01:30" : '🕜',
        "02:30" : '🕝',
        "03:30" : '🕞',
        "04:30" : '🕟',
        "05:30" : '🕠',
        "06:30" : '🕡',
        "07:30" : '🕢',
        "08:30" : '🕣',
        "09:30" : '🕤',
        "10:30" : '🕥',
        "11:30" : '🕦',
        "12:30" : '🕧',
    }

    return emojis[key]


def get_prefix(client: User, message: Message) -> Callable[[Client], List[str]]:
    """
    Fetch the current prefix of the guild and check whether it has been called.

    Args:
        client: The user that represents the bot.
        message: The Message object that represents the message of the command.

    Returns:
        The callable to be passed to the bot initialisation.
    """
    from .db import get_guild_prefix
    prefix = get_guild_prefix(int(message.guild.id))

    return commands.when_mentioned_or(*prefix)(client, message)


def str2bool(v: str) -> bool:
    """
    Converts a string representation of True entry to a bool.

    Args:
        v: The string to convert. True will be recognised by: 'yes', 'true',
            't', '1' or 'on'.

    Returns:
        Bool representation of the string.
    """
    return v.lower() in ["yes", "true", "t", "1", "on"]
