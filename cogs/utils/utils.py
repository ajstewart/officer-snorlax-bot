import pytz
import datetime
import os
import re
import logging
import string
from discord import Embed
from dotenv import load_dotenv, find_dotenv


load_dotenv(find_dotenv())
DEFAULT_OPEN_MESSAGE = os.getenv('DEFAULT_OPEN_MESSAGE')
DEFAULT_CLOSE_MESSAGE = os.getenv('DEFAULT_CLOSE_MESSAGE')
WARNING_TIME = os.getenv('WARNING_TIME')
INACTIVE_TIME = os.getenv('INACTIVE_TIME')
DELAY_TIME = os.getenv('DELAY_TIME')


def get_current_time(tz):
    """
    Returns the current time in the selected time zone.
    """
    tz = pytz.timezone(tz)
    return datetime.datetime.now(tz=tz)


def get_schedule_embed(ctx, schedule_db, tz):
    """
    Create an embed to show the schedules.
    """
    tz = pytz.timezone(tz)
    now = datetime.datetime.now(tz=tz)
    embed = Embed(
        title='Active Schedules',
        timestamp=now,
        color=2061822
    )
    for i, row in schedule_db.iterrows():
        embed.add_field(
            name='ID: {}'.format(row.rowid),
            value=(
                "Channel: <#{}>\nOpen: **{}**\nOpen Custom Message: **{}**\n"
                "Close: **{}**\nClose Custom Message: **{}**"
                "\nWarning: **{}**\nDynamic: **{}**\n"
                "Max number of delays: **{}**".format(
                    row.channel, row.open, row.open_message,
                    row.close, row.close_message, row.warning, row.dynamic,
                    row.max_num_delays
                )
            ),
            inline=False
        )

    return embed


def get_friend_channels_embed(ctx, friend_db):
    """
    Create an embed to show the schedules.
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


def get_settings_embed(ctx, guild_settings):
    """
    Create an embed to show the schedules.
    """
    if guild_settings['meowth_raid_category'] != -1:
        cat_name = ctx.guild.get_channel(guild_settings['meowth_raid_category']).name
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
            'Any raids filter: **{}**'.format(
                guild_settings['tz'],
                guild_settings['admin_channel'],
                log_channel,
                time_channel,
                cat_name,
                guild_settings['any_raids_filter']
            )
        ),
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


def get_logger(logfile=None):
    '''
    Set up the logger

    :param logfile: File to output log to
    :type logfile: str

    :returns: Logger
    :rtype: `logging.RootLogger`
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


def strip_url(content):
    return re.sub(r'http\S+', '', content)


def strip_mentions(content):
    return re.sub(r'<(?:[^\d>]+|:[A-Za-z0-9]+:)\w+>', '', content)


def strip_punctuation(content):
    return content.translate(str.maketrans('', '', string.punctuation))


def get_hour_emoji(hour: str):

    emojis = {
        "01" : '🕐',
        "02" : '🕑',
        "03" : '🕒',
        "04" : '🕓',
        "05" : '🕔',
        "06" : '🕕',
        "07" : '🕖',
        "08" : '🕗',
        "09" : '🕘',
        "10" : '🕙',
        "11" : '🕚',
        "12" : '🕛',
    }

    return emojis[hour]