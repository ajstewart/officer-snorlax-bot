"""
Contains the embeds that are used as part of the logging.
"""
import datetime
import pytz

from discord import TextChannel, Embed, Message, User
from dotenv import load_dotenv, find_dotenv
from typing import Optional


load_dotenv(find_dotenv())


def filter_delete_log_embed(
    message: Message,
    tz: str,
    reason: Optional[str] = "None"
) -> Embed:
    """
    Create an embed to send to the logging channel upon a filter message
    deletion.

    Args:
        message: The message that triggered the filter.
        tz: The timezone of the guild.
        reason: The reason of the deletion.

    Returns:
        The Discord Embed object to send to the log channel.
    """
    tz = pytz.timezone(tz)
    now = datetime.datetime.now(tz=tz)
    user = message.author
    embed = Embed(
        description=(
            f'**Message from {user.mention} deleted in '
            f'{message.channel.mention}**\n{message.content}'
        ),
        timestamp=now,
        color=2061822
    )
    embed.set_author(
        name=f"{user.name}#{user.discriminator}",
        icon_url=user.avatar
    )
    embed.add_field(
        name="Reason",
        value=reason
    )
    embed.set_footer(
        text=f"Author: {message.author.id} | Message ID: {message.id}"
    )

    return embed


def ban_log_embed(
    user: User,
    tz: str,
    reason: Optional[str] = "None"
) -> Embed:
    """
    Create an embed to send to the logging channel on the event of a member
    being banned using the join name filter.

    Args:
        user: The user that triggered the filter.
        tz: The timezone of the guild.
        reason: The reason of the ban.

    Returns:
        The Discord Embed object to send to the log channel.
    """
    tz = pytz.timezone(tz)
    now = datetime.datetime.now(tz=tz)
    embed = Embed(
        description=f'**New joiner {user.mention} banned**',
        timestamp=now,
        color=10038562
    )
    embed.set_author(
        name=f"{user.name}#{user.discriminator}",
        icon_url=user.avatar
    )
    embed.add_field(
        name="Reason",
        value=reason
    )
    embed.set_footer(
        text=f"Snorlax is keeping you safe!"
    )

    return embed


def schedule_log_embed(
    channel: TextChannel,
    tz: str,
    stype: str,
    delay_mins: int = -1,
    delay_num: int = -1,
    max_delay_num: int = -1
) -> Embed:
    """
    Create an embed to send to the logging channel for channel schedule events.

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

    if stype not in [
        'close', 'open', 'delay', 'close_skip', 'open_skip', 'warning'
    ]:
        raise ValueError('The schedule type is not recognised!')

    titles = {
        'close': 'Channel Closed!',
        'open': 'Channel Opened!',
        'delay': 'Channel Closing Delayed!',
        'close_skip': 'Skipped Schedule',
        'open_skip': 'Skipped Schedule',
        'warning': 'Closing Warning!'
    }

    descriptions = {
        'close': f'{channel.mention} has been closed!',
        'open': f'{channel.mention} has been opened!',
        'delay': (
            f'Closing of {channel.mention} has been delayed by '
            f'{delay_mins} mins! This is delay number {delay_num}/'
            f'{max_delay_num}.'
        ),
        'close_skip': f'{channel.mention} is already closed!',
        'open_skip': f'{channel.mention} is already open!',
        'warning': (
            f'Close warning message sent to {channel.mention} due to activity.'
        )
    }

    colors = {
        'close': 15158332,
        'open': 3066993,
        'delay': 15844367,
        'close_skip': 3447003,
        'open_skip': 3447003,
        'warning': 15105570
    }

    tz = pytz.timezone(tz)
    now = datetime.datetime.now(tz=tz)
    embed = Embed(
        title=titles[stype],
        description=descriptions[stype],
        timestamp=now,
        color=colors[stype]
    )

    embed.set_author(
        name=f"{channel.guild.name}",
        icon_url=channel.guild.icon
    )

    return embed
