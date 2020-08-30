import pytz
import datetime
import os
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
                "\nWarning: **{}**\nDynamic: **{}**".format(
                    row.channel, row.open, row.open_message,
                    row.close, row.close_message, row.warning, row.dynamic
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
    embed = Embed(
        title='Settings',
        color=16756290
    )

    embed.add_field(
        name="Guild Settings",
        value=(
            'TZ: **{}**\n'
            'Admin Channel: **<#{}>**'.format(
                guild_settings['tz'],
                guild_settings['admin_channel']
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
