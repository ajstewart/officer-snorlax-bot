"""Contains the embeds that are used as part of the logging."""
import datetime

from typing import Optional

import discord
import pytz

from discord import app_commands
from discord.utils import utcnow
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())


def filter_delete_log_embed(
    message: discord.Message, reason: Optional[str] = "None"
) -> discord.Embed:
    """Create an embed to send to the logging channel upon a filter message deletion.

    Args:
        message: The message that triggered the filter.
        reason: The reason of the deletion.

    Returns:
        The Discord Embed object to send to the log channel.
    """
    now = utcnow()
    user = message.author
    embed = discord.Embed(
        description=(
            f"**Message from {user.mention} deleted in "
            f"{message.channel.mention}**\n{message.content}"
        ),
        timestamp=now,
        color=2061822,
    )

    embed.set_author(
        name=f"{user.name}#{user.discriminator}", icon_url=user.display_avatar
    )
    embed.add_field(name="Reason", value=reason)
    embed.set_footer(text=f"Author: {message.author.id} | Message ID: {message.id}")

    return embed


def ban_log_embed(
    user: discord.User, tz: str, reason: Optional[str] = "None"
) -> discord.Embed:
    """Create an embed to send to the logging channel on a ban event.

    Triggered by a member being banned using the join name filter.

    Args:
        user: The user that triggered the filter.
        tz: The timezone of the guild.
        reason: The reason of the ban.

    Returns:
        The Discord Embed object to send to the log channel.
    """
    tz = pytz.timezone(tz)
    now = datetime.datetime.now(tz=tz)
    embed = discord.Embed(
        description=f"**New joiner {user.mention} banned**",
        timestamp=now,
        color=10038562,
    )
    embed.set_author(
        name=f"{user.name}#{user.discriminator}", icon_url=user.display_avatar
    )
    embed.add_field(name="Reason", value=reason)
    embed.set_footer(text="Snorlax is keeping you safe!")

    return embed


def schedule_log_embed(
    channel: discord.TextChannel,
    tz: str,
    stype: str,
    delay_mins: int = -1,
    delay_num: int = -1,
    max_delay_num: int = -1,
) -> discord.Embed:
    """Create an embed to send to the logging channel for channel schedule events.

    Args:
        channel: The channel for which the schedule is being applied to.
        tz: The timezone of the guild.
        stype: The schedule event type.
        delay_mins: The number of mins to delay closing.
        delay_num: The delay number of the schedule, i.e. how many times the
            closing has been delayed.
        max_delay_num: The maximum number of delays allowed.

    Returns:
        The Discord Embed object to send to the log channel.
    """
    if stype not in ["close", "open", "delay", "close_skip", "open_skip", "warning"]:
        raise ValueError("The schedule type is not recognised!")

    titles = {
        "close": "Channel Closed!",
        "open": "Channel Opened!",
        "delay": "Channel Closing Delayed!",
        "close_skip": "Skipped Schedule",
        "open_skip": "Skipped Schedule",
        "warning": "Closing Warning!",
    }

    descriptions = {
        "close": f"{channel.mention} has been closed!",
        "open": f"{channel.mention} has been opened!",
        "delay": (
            f"Closing of {channel.mention} has been delayed by "
            f"{delay_mins} mins! This is delay number {delay_num}/"
            f"{max_delay_num}."
        ),
        "close_skip": f"{channel.mention} is already closed!",
        "open_skip": f"{channel.mention} is already open!",
        "warning": f"Close warning message sent to {channel.mention} due to activity.",
    }

    colors = {
        "close": 15158332,
        "open": 3066993,
        "delay": 15844367,
        "close_skip": 3447003,
        "open_skip": 3447003,
        "warning": 15105570,
    }

    tz = pytz.timezone(tz)
    now = datetime.datetime.now(tz=tz)
    embed = discord.Embed(
        title=titles[stype],
        description=descriptions[stype],
        timestamp=now,
        color=colors[stype],
    )

    embed.set_author(name=f"{channel.guild.name}", icon_url=channel.guild.icon)

    return embed


def fc_channel_removed_log_embed(channel: discord.TextChannel) -> discord.Embed:
    """Create an embed to send to the logging channel upon a filter message deletion.

    Args:
        channel: The channel that has been removed.

    Returns:
        The Discord Embed object to send to the log channel.
    """
    now = utcnow()
    embed = discord.Embed(
        description=(
            f"Channel **#{channel.name}** has been removed from the allowed friend"
            " codes list."
        ),
        timestamp=now,
        color=15105570,
    )

    embed.set_author(name=f"{channel.guild.name}", icon_url=channel.guild.icon)
    embed.add_field(name="Reason", value="Channel has been deleted.")

    return embed


def time_channel_reset_log_embed(channel: discord.TextChannel) -> discord.Embed:
    """Create an embed to send to the logging channel upon a time channel deletion.

    Args:
        channel: The channel that has been removed.

    Returns:
        The Discord Embed object to send to the log channel.
    """
    now = utcnow()
    embed = discord.Embed(
        description="Time channel has been reset.", timestamp=now, color=15105570
    )

    embed.set_author(name=f"{channel.guild.name}", icon_url=channel.guild.icon)
    embed.add_field(
        name="Reason", value=f"Deletion of time channel **#{channel.name}**."
    )

    return embed


def schedules_deleted_log_embed(channel: discord.TextChannel, id: int) -> discord.Embed:
    """Create an embed to send to the logging channel upon a channel deletion.

    Only triggered for channels that had an active schedule.

    Args:
        channel: The channel which schedules have been removed.
        id: The id of the schedule removed.

    Returns:
        The Discord Embed object to send to the log channel.
    """
    now = utcnow()
    embed = discord.Embed(
        description=f"Schedule ID {id} has been deleted.", timestamp=now, color=15105570
    )

    embed.set_author(name=f"{channel.guild.name}", icon_url=channel.guild.icon)
    embed.add_field(name="Reason", value=f"Deletion of channel **#{channel.name}**.")

    return embed


def attempted_app_command_embed(
    command: app_commands.Command, channel: discord.TextChannel, user: discord.User
) -> discord.Embed:
    """Create an embed to send to the logging channel on an admin command attempt.

    Args:
        command: The app command that was attempted to be used.
        channel: The channel where it was attempted.
        user: The user who attempted the command.

    Returns:
        The Discord Embed object to send to the log channel.
    """
    now = utcnow()
    embed = discord.Embed(
        description="Unauthorised command attempted!", timestamp=now, color=15105570
    )

    embed.set_author(
        name=f"{user.name}#{user.discriminator}", icon_url=user.display_avatar
    )

    embed.add_field(name="User", value=f"{user.mention} (id: {user.id})", inline=False)

    embed.add_field(name="Command", value=f"{command.name}", inline=False)

    embed.add_field(name="Channel", value=f"{channel.mention}", inline=False)

    return embed
