"""Contains all the non-log embed messages used by the bot.
"""

import datetime
import os
import pandas as pd

from discord import Embed, User, Member, Role, Interaction
from discord.utils import utcnow
from dotenv import load_dotenv, find_dotenv
from typing import List, Union


load_dotenv(find_dotenv())
DEFAULT_OPEN_MESSAGE = os.getenv('DEFAULT_OPEN_MESSAGE')
DEFAULT_CLOSE_MESSAGE = os.getenv('DEFAULT_CLOSE_MESSAGE')
WARNING_TIME = os.getenv('WARNING_TIME')
INACTIVE_TIME = os.getenv('INACTIVE_TIME')
DELAY_TIME = os.getenv('DELAY_TIME')


def get_schedule_embed(schedule_db: pd.DataFrame) -> Embed:
    """
    Create an embed to show the saved schedules.

    Args:
        schedule_db: The schedule database table as a pandas dataframe.
        tz: The guild timezone, e.g., 'Australia/Sydney'.

    Returns:
        The embed containing the list of schedules.
    """
    embed = Embed(
        title='Schedules',
        timestamp=utcnow(),
        color=2061822
    )
    for _, row in schedule_db.iterrows():
        embed.add_field(
            name=f'Channel: #{row.channel_name}',
            value=(
                f"Active: **{row.active}**\n"
                f"Open: **{row.open}**\nOpen Custom Message: **{row.open_message}**\n"
                f"Close: **{row.close}**\nClose Custom Message: **{row.close_message}**"
                f"\nWarning: **{row.warning}**\nDynamic: **{row.dynamic}**\n"
                f"Max number of delays: **{row.max_num_delays}**\nSilent: **{row.silent}**"
            ).replace('True', '✅').replace('False', '❌'),
            inline=False
        )

    return embed


def get_friend_channels_embed(friend_db: pd.DataFrame) -> Embed:
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
    interaction: Interaction,
    guild_settings: pd.DataFrame
) -> Embed:
    """
    Create an embed to show the settings of the bot on the guild the command
    was used from.

    Args:
        interaction: The interaction that triggered the request.
        guild_settings: The guild settings database table as a pandas dataframe.

    Returns:
        The embed containing the guild settings.
    """
    if guild_settings['meowth_raid_category'] != -1:
        cat_name = interaction.guild.get_channel(
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
            'Log Channel: **{}**\n'
            'Time Channel: **{}**\n'
            'Pokenav Raid Category: **{}**\n'
            'Any raids filter: **{}**\n'
            'Join name filter: **{}**\n'
            'Prefix: **{}**'.format(
                guild_settings['tz'],
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


def get_open_embed(
    close: str,
    now: datetime.datetime,
    custom_open_message: str,
    client_user: User,
    time_format_fill: str
) -> Embed:
    """Produces the open embed that is sent when a channel opens.

    Args:
        close: The string representation of the future closing time, e.g. '12:00'.
        now: The datetime object of the opening time.
        custom_open_message: The custom open message of the schedule.
        client_user: The bot user object.
        time_format_fill: The string time channel mention, or 'Unavailable' if the time channel
            is not configured.

    Returns:
        The open channel embed containing the next close time and the current time.
    """
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

    embed.set_footer(text="Current time updates every 10 min.")
    embed.set_thumbnail(url=client_user.display_avatar)

    return embed


def get_close_embed(
    open: str,
    now: datetime.datetime,
    custom_close_message: str,
    client_user: User,
    time_format_fill: str
) -> Embed:
    """Produces the open embed that is sent when a channel opens.

    Args:
        open: The string representation of the future opening time, e.g. '12:00'.
        now: The datetime object of the closing time.
        custom_close_message: The custom close message of the schedule.
        client_user: The bot user object.
        time_format_fill: The string time channel mention, or 'Unavailable' if the time channel
            is not configured.

    Returns:
        The close channel embed containing the next open time and the current time.
    """
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

    embed.set_footer(text="Current time updates every 10 min.")
    embed.set_thumbnail(url=client_user.display_avatar)

    return embed


def get_warning_embed(
    close: str,
    now: datetime.datetime,
    client_user: User,
    time_format_fill: str,
    dynamic: bool,
    delay: bool
) -> Embed:
    """Produces the warning embed that is sent when a is to close and warnings are enabled.

    Args:
        close: The string representation of the future closing time, e.g. '12:00'.
        now: The datetime object of the warning time.
        client_user: The bot user object.
        time_format_fill: The string time channel mention, or 'Unavailable' if the time channel
            is not configured.
        dynamic: Whether dynamic mode is activated on the schedule (True) or not (False).
        delay: Whether the warning is because of a previous delay. No dynamic addition
            will be made if True.

    Returns:
        The warning embed containing the next close time and the current time.
    """
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


def get_schedule_overwrites_embed(
    roles_allow: List[Union[Role, Member]],
    roles_deny: List[Union[Role, Member]]
) -> Embed:
    """Produces the warning embed of roles that will not be affected by a schedule.

    Args:
        roles_allow: List or roles or members with explicit 'True' send_messages.
        roles_deny: List or roles or members with explicit 'False' send_messages.

    Returns:
        The warning embed containing the roles.
    """
    embed = Embed(
        title="️⚠️  Roles Will Ignore Schedule",
        description=(
            "The following roles will not respect the created schedule due to their 'send messages' permission."
        ),
        color=15105570,
        timestamp=utcnow(),
    )

    if len(roles_allow) > 0:
        allow_value = ""
        for role in roles_allow:
            allow_value += f"\n{role.mention}"

        embed.add_field(
            name="✅ Roles always able to send messages:",
            value=allow_value,
            inline=False
        )

    if len(roles_deny) > 0:
        deny_value = ""
        for role in roles_deny:
            deny_value += f"\n{role.mention}"

        embed.add_field(
            name="❌ Roles never able to send messages:",
            value=deny_value,
            inline=False
        )

    embed.add_field(
        name="How to fix?",
        value="Change the 'send messages' permission to neutral so it follows the @everybody role."
    )

    return embed
