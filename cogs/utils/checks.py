"""
Contains all the various checks that the commands need to perform.
"""

import pytz
import re
import time

from discord import Message
from discord.abc import User
from discord.ext import commands
from typing import Iterable, Tuple

from .db import load_guild_db, load_schedule_db, set_guild_active
from .utils import strip_url, strip_mentions, strip_punctuation


def check_bot(ctx: commands.context) -> bool:
    """
    Checks whether the context came from a bot.

    Args:
        ctx: The command context containing the message content and other
            metadata.

    Returns:
        'True' when the context originated from a bot account. 'False' if not.
    """
    if ctx.author.bot:
        return False
    else:
        return True


def check_admin(ctx: commands.context) -> bool:
    """
    Checks whether the user is an admin.

    Args:
        ctx: The command context containing the message content and other
            metadata.

    Returns:
        'True' when the context originated from a user with the admin
        permissions. 'False' otherwise.
    """
    if ctx.author.guild_permissions.administrator:
        return True
    else:
        return False


async def check_admin_channel(ctx: commands.context) -> bool:
    """
    Checks if the channel of the command is the set admin channel.

    Args:
        ctx: The command context containing the message content and other
            metadata.

    Returns:
        'True' when the context originated from the set admin channel.
        'False' if not.
    """
    guild_db = await load_guild_db()
    if ctx.guild.id in guild_db.index:
        admin_channel = guild_db.loc[
            ctx.guild.id, 'admin_channel'
        ]
        if ctx.channel.id == admin_channel:
            return True
        else:
            return False
    else:
        return False


def check_if_channel_active(
    messages: Iterable[Message], client_user: User
) -> bool:
    """
    Check if the list of messaged passed contains any non-bot activity.

    TODO: This is not very repeat friendly, perhaps needs refactor.

    Args:
        messages: The iterator object containing the messages. Usually the
            output from the '.history' method.
        client_user: The user object of the bot.

    Returns:
        'True' when the messages contains one from a non bot user. 'False' if
        not.
    """
    active = False

    if messages:
        for m in messages:
            if m.author == client_user:
                continue
            elif m.author.bot:
                continue
            else:
                active = True
                break

    return active


def check_for_friend_code(content: str) -> bool:
    """
    Checks the message content for a friend code.

    Args:
        content: The string representation of the message.

    Returns:
        'True' when the message contains a friend code. 'False' if not.
    """
    pattern = re.compile(r"\d{4}.*\d{4}.*\d{4}(?!(\d*\>))")
    content = strip_mentions(content)
    content = strip_url(content)
    match = re.search(pattern, content)

    if match:
        return True
    else:
        return False


def check_valid_timezone(tz: str) -> bool:
    """
    Checks whether the tz sting is a valid timezone using pytz.

    Args:
        tz: The string timezone. E.g. 'Australia/Sydney'.

    Returns:
        'True' when the tz is valid. 'False' if not.
    """
    if tz in pytz.all_timezones:
        return True
    else:
        return False


def check_time_format(time_input: str) -> Tuple[bool, str]:
    """
    Checks user time input is in the %H:%M format.

    Also checks for single hour and minute entries and returns the correct
    zero-padded entry. E.g. '6:00' is returned as '06:00'.

    Args:
        time_input: The user time input string.

    Returns:
        Tuple containing a bool, signifying whether the time was valid or not,
        and a string with the correct zero-padded format.
    """
    try:
        thetime = time.strptime(time_input, '%H:%M')
        # check for single hour entries, e.g. 6:00
        thetime = time.strftime('%H:%M', thetime)
        return True, thetime
    except ValueError:
        return False, '99:99'


def check_for_any_raids(content: str) -> bool:
    """
    Checks the message string content for any strings matching to the 'any
    raids' filter.

    Args:
        content: The message string content.

    Returns:
        'True' if the content contains an any raids question. 'False' if not.
    """
    content = strip_punctuation(content)
    content_strip = content.strip().split(" ")

    if content_strip[0] == 'any' and content_strip[-1] in ['raid', 'raids']:
        return True
    else:
        return False


async def check_schedule_exists(sched_id: int) -> bool:
    """
    Checks whether a schedule exists with the provided id number.

    Args:
        sched_id: The provided schedule id to check.

    Returns:
        'True' when the content contains a match. 'False' if not.
    """
    schedules = await load_schedule_db()
    exists = sched_id in schedules['rowid'].astype(int).tolist()

    return exists


async def check_remove_schedule(ctx: commands.context, sched_id: int) -> bool:
    """
    Checks whether the provided schedule id is attached to the guild where
    the command originated.

    Args:
        ctx: The command context containing the message content and other
            metadata.
        sched_id: The schedule id.

    Returns:
        'True' when the schedule id is from the same guild as the command.
        'False' if not.
    """
    schedules = await load_schedule_db()
    schedules = schedules.set_index('rowid')

    schedule_guild = schedules.loc[sched_id]['guild']
    ctx_guild_id = ctx.guild.id

    allowed = schedule_guild == ctx_guild_id

    return allowed


async def check_guild_exists(guild_id: int, check_active: bool = False) -> bool:
    """
    Checks whether a guild exists and, optionally, whether it is set to active.

    It is intended to be used as part of the initial checks at the bot
    start up.

    Args:
        guild_id: The id number of the guild.
        check_active: When True the guild is checked that the status in the
            database is set to 'active'.

    Returns:
        'True' when the guild is contained in the database. 'False' if not.
    """
    guilds = await load_guild_db()

    if guild_id in guilds.index.astype(int).tolist():
        if check_active:
            active = guilds.loc[guild_id]['active']
            if not active:
                set_guild_active(guild_id, 1)
        return True
    else:
        return False
