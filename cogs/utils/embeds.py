"""Contains all the non-log embed messages used by the bot."""

import datetime
import discord
import pandas as pd

from discord import Embed
from discord.utils import utcnow
from typing import Optional, Union


def get_schedule_embed(schedule_db: pd.DataFrame, num_warning_roles: int = 0) -> Embed:
    """
    Create an embed to show the saved schedules.

    Args:
        schedule_db: The schedule database table as a pandas dataframe.
        num_warning_roles: If greater than 0 then a warning field will be placed in the
            creation embed to warn of the number of roles with overwrites.

    Returns:
        The embed containing the list of schedules.
    """
    embed_title = "Schedules Details" if len(schedule_db) > 1 else "Schedule Details"

    embed = Embed(
        title=embed_title,
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

    if num_warning_roles > 0:
        embed.add_field(
            name="⚠️  Roles Warning",
            value=(
                f"There are {num_warning_roles} roles(s) in <#{row.channel}> that the schedule will not apply to."
                " Use the `/check-schedule-roles` command for more information!"
            )
        )

    return embed


def get_schedule_embed_for_user(schedule_db: pd.DataFrame, channel: discord.TextChannel) -> Embed:
    """
    Create an embed to show the channel schedule to the user.

    Args:
        schedule_db: The schedule database table as a pandas dataframe.
        channel: The channel object for the interaction channel.

    Returns:
        The embed containing the list of schedules.
    """
    embed_title = f"⏰ Schedule for #{channel.name}"

    embed = Embed(
        title=embed_title,
        timestamp=utcnow(),
        color=2061822
    )

    if schedule_db.empty:
        embed.add_field(
            name="No schedule!",
            value=f"There is no schedule set for {channel.mention}."
        )
    else:
        for _, row in schedule_db.iterrows():
            open_hour = int(row['open'].split(":")[0])
            p_open = "PM" if open_hour >= 12 else "AM"

            close_hour = int(row['close'].split(":")[0])
            p_close = "PM" if close_hour >= 12 else "AM"

            embed.add_field(
                name='Open ✅',
                value=f"{row['open']} {p_open}",
                inline=True
            )

            embed.add_field(
                name='Close ❌',
                value=f"{row['close']} {p_close}",
                inline=True
            )

            # Dummy field to push any other schedules to next row.
            embed.add_field(
                name='\u200b',
                value='\u200b',
                inline=True
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
    guild: discord.Guild,
    guild_settings: pd.DataFrame,
    guild_schedule_settings: pd.DataFrame
) -> Embed:
    """
    Create an embed to show the settings of the bot on the guild the command
    was used from.

    Args:
        interaction: The interaction that triggered the request.
        guild_settings: The guild settings database table as a pandas dataframe.
        guild_schedule_settings: The server schedule settings for the guild.

    Returns:
        The embed containing the guild settings.
    """
    guild_schedule_settings = guild_schedule_settings.iloc[0]

    if guild_settings['meowth_raid_category'] != -1:
        cat_name = guild.get_channel(
            guild_settings['meowth_raid_category']
        ).name
    else:
        cat_name = 'Not set'

    embed = Embed(
        title='Settings',
        color=16756290
    )

    admin_channel_id = guild_settings['admin_channel']
    if admin_channel_id == -1:
        admin_channel = "Not set"
    else:
        admin_channel = "<#{}>".format(admin_channel_id)

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
            'Timezone: **{}**\n'
            'Admin Channel: **{}**\n'
            'Log Channel: **{}**\n'
            'Time Channel: **{}**\n'
            'Pokenav Raid Category: **{}**\n'
            'Any raids filter: **{}**\n'
            'Join name filter: **{}**\n'
            'Prefix: **{}**'.format(
                guild_settings['tz'],
                admin_channel,
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
        name="Server Schedules Settings",
        value=(
            'Open Message: **{}**\n'
            'Close Message: **{}**\n'
            'Warning Time: **{}** min\n'
            'Inactive Time: **{}** min\n'
            'Delay Time: **{}** min'.format(
                guild_schedule_settings['base_open_message'],
                guild_schedule_settings['base_close_message'],
                guild_schedule_settings['warning_time'],
                guild_schedule_settings['inactive_time'],
                guild_schedule_settings['delay_time'],
            )
        ),
        inline=False
    )

    return embed


def get_open_embed(
    close: str,
    now: datetime.datetime,
    base_open_message: str,
    custom_open_message: str,
    client_user: discord.User,
    time_format_fill: str
) -> Embed:
    """Produces the open embed that is sent when a channel opens.

    Args:
        close: The string representation of the future closing time, e.g. '12:00'.
        now: The datetime object of the opening time.
        base_open_message: The base open message for the server.
        custom_open_message: The custom open message of the schedule.
        client_user: The bot user object.
        time_format_fill: The string time channel mention, or 'Unavailable' if the time channel
            is not configured.

    Returns:
        The open channel embed containing the next close time and the current time.
    """
    if custom_open_message != "None":
        base_open_message += f"\n\n{custom_open_message}"

    embed = Embed(
        title="✅  Channel Open!",
        description=base_open_message,
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
    base_close_message: str,
    custom_close_message: str,
    client_user: discord.User,
    time_format_fill: str
) -> Embed:
    """Produces the open embed that is sent when a channel opens.

    Args:
        open: The string representation of the future opening time, e.g. '12:00'.
        now: The datetime object of the closing time.
        base_close_message: The guild base close message.
        custom_close_message: The custom close message of the schedule.
        client_user: The bot user object.
        time_format_fill: The string time channel mention, or 'Unavailable' if the time channel
            is not configured.

    Returns:
        The close channel embed containing the next open time and the current time.
    """
    if custom_close_message != "None":
        base_close_message += f"\n\n{custom_close_message}"

    embed = Embed(
        title="️⛔  Channel Closed!",
        description=base_close_message,
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
    client_user: discord.User,
    time_format_fill: str,
    dynamic: bool,
    delay: bool,
    delay_time: int,
    warning_time: int
) -> Embed:
    """Produces the warning embed that is sent when a is to close and warnings are enabled.

    Args:
        close: The string representation of the future closing time, e.g. '12:00'.
        client_user: The bot user object.
        time_format_fill: The string time channel mention, or 'Unavailable' if the time channel
            is not configured.
        dynamic: Whether dynamic mode is activated on the schedule (True) or not (False).
        delay: Whether the warning is because of a previous delay. No dynamic addition
            will be made if True.
        delay_time: The guild delay time in minutes.
        warning_time: The guild warning time in minutes.

    Returns:
        The warning embed containing the next close time and the current time.
    """
    embed = Embed(
        title="️⚠️  Snorlax is approaching!",
        color=15105570
    )

    close_time_str = datetime.datetime.strptime(close, '%H:%M').strftime('%I:%M %p')

    buffer_time = delay_time if delay else warning_time

    warning_string = f"Channel is due to close in {buffer_time} minute"

    if int(buffer_time) > 1:
        warning_string += "s at"
    else:
        warning_string += " at"

    embed.add_field(name=warning_string, value=f"{close_time_str}")

    embed.add_field(name="Current Time", value=time_format_fill, inline=False)

    if dynamic:
        embed.add_field(
            name="Delay Active",
            value="Closing will be delayed by a short time if the channel is active.",
            inline=False
        )

    embed.set_footer(text="Current time updates every 10 min.", icon_url=client_user.display_avatar)

    return embed


def get_schedule_overwrites_embed(
    roles_allow: list[Union[discord.Role, discord.Member]],
    roles_deny: list[Union[discord.Role, discord.Member]],
    channel: discord.TextChannel
) -> Embed:
    """Produces the warning embed of roles that will not be affected by a schedule.

    Args:
        roles_allow: List or roles or members with explicit 'True' send_messages.
        roles_deny: List or roles or members with explicit 'False' send_messages.
        channel: THe channel for which the overwrites apply to.

    Returns:
        The warning embed containing the roles.
    """
    embed = Embed(
        title="️⚠️  Roles Will Ignore Schedule",
        description=(
            f"The following roles will not respect any schedule in {channel.mention}"
            " due to their `send messages` permission."
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


def get_schedule_overwrites_embed_all_ok(channel: discord.TextChannel) -> Embed:
    """Produces an embed to communicate that no roles will schedule doge.

    Args:
        channel: The channel checked.

    Returns:
        The information embed.
    """
    embed = Embed(
        title="️✅  All Roles Ok",
        description=(
            f"Any schedule in {channel.mention} will apply to all roles!"
        ),
        color=3066993,
        timestamp=utcnow(),
    )

    return embed


def get_admin_channel_embed(
    admin_channel
) -> Embed:
    """Produces the embed message when the admin channel is not set.

    Args:
        admin_channel: The admin channel for the guild.

    Returns:
        The embed that says that the admin channel must be used.
    """
    if admin_channel == -1:
        admin_mention = "admin channel not set, use the '/set-admin-channel command!'"
    else:
        admin_mention = f"<#{admin_channel}>."

    description = f"This command must be used in the admin channel: {admin_mention}"

    embed = Embed(
        title="️Command cannot be used here!",
        description=description,
        color=15158332
    )

    return embed


def get_message_embed(msg: str, msg_type: str, title: Optional[str] = None) -> Embed:
    """Return a generic embed with the provided message and type.


    """
    msg_colors = {
        'info': 2061822,
        'error': 15158332,
        'success': 3066993
    }

    msg_type = msg_type.lower()

    if msg_type not in msg_colors:
        raise ValueError(
            f"Message type '{msg_type}' is not valid! (valid: {', '.join(msg_colors.keys())})"
        )

    embed = Embed(
        color=msg_colors[msg_type],
        timestamp=utcnow(),
        description=msg
    )

    if title is not None:
        embed.title = title

    return embed
