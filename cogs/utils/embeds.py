
import datetime
import os
import pandas as pd
import pytz

from discord import Embed
from discord.ext import commands
from dotenv import load_dotenv, find_dotenv


load_dotenv(find_dotenv())
DEFAULT_OPEN_MESSAGE = os.getenv('DEFAULT_OPEN_MESSAGE')
DEFAULT_CLOSE_MESSAGE = os.getenv('DEFAULT_CLOSE_MESSAGE')
WARNING_TIME = os.getenv('WARNING_TIME')
INACTIVE_TIME = os.getenv('INACTIVE_TIME')
DELAY_TIME = os.getenv('DELAY_TIME')


def get_schedule_embed(
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
    friend_db: pd.DataFrame
) -> Embed:
    """
    Create an embed to show the allowed friend code channels.

    Args:
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


def get_open_embed(close, now, custom_open_message, client_user, time_format_fill) -> Embed:
    """Get the open embed"""

    open_message = DEFAULT_OPEN_MESSAGE

    if custom_open_message != "None":
        open_message += f"\n\n{custom_open_message}"

    embed = Embed(
        title="✅  Channel Open!",
        description=open_message,
        color=3066993
    )

    close_time_str = datetime.datetime.strptime(close, '%H:%M').strftime('%I:%M %p')

    embed.add_field(
        name="Scheduled Close Time",
        value=f"{close_time_str} {now.tzname()}"
    )

    embed.add_field(
        name="Current Time",
        value=time_format_fill,
        inline=False
    )

    embed.set_footer(text="Current time updates every 10 min.", icon_url=client_user.display_avatar)

    return embed


def get_close_embed(open, now, custom_close_message, client_user, time_format_fill) -> Embed:
    """Get the close embed"""

    close_message = DEFAULT_CLOSE_MESSAGE

    if custom_close_message != "None":
        close_message += f"\n\n{custom_close_message}"

    embed = Embed(
        title="️⛔  Channel Closed!",
        description=close_message,
        color=15158332
    )

    open_time_str = datetime.datetime.strptime(open, '%H:%M').strftime('%I:%M %p')

    embed.add_field(
        name="Scheduled Open Time",
        value=f"{open_time_str} {now.tzname()}"
    )

    embed.add_field(
        name="Current Time",
        value=time_format_fill,
        inline=False
    )

    embed.set_footer(text="Current time updates every 10 min.", icon_url=client_user.display_avatar)

    return embed


def get_warning_embed(close, now, client_user, time_format_fill, dynamic, delay) -> Embed:
    """Get the warning embed"""

    embed = Embed(
        title="️⚠️  Snorlax is approaching!",
        color=15105570
    )

    close_time_str = datetime.datetime.strptime(close, '%H:%M').strftime('%I:%M %p')

    buffer_time = DELAY_TIME if delay else WARNING_TIME

    warning_string = f"Channel is due to close in {buffer_time} minute"

    if int(buffer_time) > 1:
        warning_string += "s at"
    else:
        warning_string += " at"

    embed.add_field(
        name=warning_string,
        value=f"{close_time_str} {now.tzname()}"
    )

    embed.add_field(
        name="Current Time",
        value=time_format_fill,
        inline=False
    )

    if dynamic:
        embed.add_field(
            name="Delay Active",
            value="Closing will be delayed by a short time if the channel is active.",
            inline=False
        )

    embed.set_footer(text="Current time updates every 10 min.", icon_url=client_user.display_avatar)

    return embed
