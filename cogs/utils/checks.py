"""Contains all the various checks that the commands need to perform."""

import re
import time

from typing import Iterable, Tuple, Union

import discord

from discord import app_commands
from discord.abc import User
from discord.ext import commands

from models import Schedule
from repositories import GuildRepository

from . import utils as snorlax_utils


def check_bot(ctx: Union[commands.Context, discord.Interaction]) -> bool:
    """Checks whether the context came from a bot.

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


def interaction_check_bot(interaction: discord.Interaction) -> bool:
    """Checks whether the interaction came from a bot.

    Args:
        interaction: The interaction passed.

    Returns:
        'True' when the context originated from a bot account. 'False' if not.
    """
    return not interaction.user.bot


def check_admin(ctx: Union[commands.Context, discord.Interaction]) -> bool:
    """Checks whether the user is an admin.

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


class AdminChannelError(app_commands.CheckFailure):
    """Raised when the command is not used in the admin channel."""

    pass


async def check_admin_channel(
    ctx: Union[commands.Context, discord.Interaction],
) -> bool:
    """Checks if the channel of the command is the set admin channel.

    Args:
        ctx: The command context containing the message content and other metadata.

    Returns:
        'True' when the context originated from the set admin channel.
        'False' if not.
    """
    async with ctx.client.db_session() as session:
        guild_repo = GuildRepository(session)
        guild_db = await guild_repo.get(ctx.guild.id)
        admin_channel = guild_db.admin_channel

    if ctx.channel.id == admin_channel:
        return True
    else:
        raise AdminChannelError("This must be used in an admin channel!")


def check_if_channel_active(
    messages: Iterable[discord.Message], client_user: User
) -> bool:
    """Check if the list of messaged passed contains any non-bot activity.

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
    """Checks the message content for a friend code.

    Args:
        content: The string representation of the message.

    Returns:
        'True' when the message contains a friend code. 'False' if not.
    """
    pattern = re.compile(r"\d{4}.{0,2}\d{4}.{0,2}\d{4}(?!(\d*\>))")
    content = snorlax_utils.strip_mentions(content)
    content = snorlax_utils.strip_url(content)
    match = re.search(pattern, content)

    if match:
        return True
    else:
        return False


def check_time_format(time_input: str) -> Tuple[bool, str]:
    """Checks user time input is in the %H:%M format.

    Also checks for single hour and minute entries and returns the correct
    zero-padded entry. E.g. '6:00' is returned as '06:00'.

    Args:
        time_input: The user time input string.

    Returns:
        Tuple containing a bool, signifying whether the time was valid or not,
        and a string with the correct zero-padded format.
    """
    try:
        thetime = time.strptime(time_input, "%H:%M")
        # check for single hour entries, e.g. 6:00
        thetime = time.strftime("%H:%M", thetime)
        return True, thetime
    except ValueError:
        return False, "99:99"


def check_for_any_raids(content: str) -> bool:
    """Checks the message string content for strings matching to the 'any raids' filter.

    Args:
        content: The message string content.

    Returns:
        'True' if the content contains an any raids question. 'False' if not.
    """
    content = snorlax_utils.strip_punctuation(content)
    content_strip = content.strip().split(" ")

    if content_strip[0] == "any" and content_strip[-1] in ["raid", "raids"]:
        return True
    else:
        return False


def check_remove_schedule(
    ctx: Union[commands.Context, discord.Interaction], schedule: Schedule
) -> bool:
    """Checks whether the schedule id is for the guild where the command originated.

    Args:
        ctx: The command context containing the message content and other
            metadata.
        schedule: The schedule object.

    Returns:
        'True' when the schedule id is from the same guild as the command.
        'False' if not.
    """
    ctx_guild_id = ctx.guild.id
    allowed = schedule.guild == ctx_guild_id

    return allowed


def check_schedule_perms(member: discord.Member, channel: discord.TextChannel) -> bool:
    """Checks bot permissions for the channel where the schedule is to be created.

    Will return False if the bot does not have the required permissions to correctly
    apply a schedule.

    Args:
        member: The bot guild member.
        channel: The channel for which a schedule is to be created.

    Returns:
        'True' if all permissions are correct, 'False' if not.
    """
    perms = channel.permissions_for(member)
    ok = all(
        [
            perms.view_channel,
            perms.read_messages,
            perms.read_message_history,
            perms.manage_roles,
        ]
    )

    return ok


async def check_schedule_overwrites(
    channel: discord.TextChannel, bot_user: User
) -> discord.Embed:
    """Checks the overwrites on a channel for which a schedule is to be created.

    If any role explicitly has send_messages set to `True` a warning will be sent to
    the command channel.

    Args:
        channel: The channel for which a schedule is to be created.
        bot_user: The bot user.
    """
    no_effect_roles_allow = []
    no_effect_roles_deny = []

    # Get the overwrites
    overwrites = channel.overwrites
    bot_role = channel.guild.self_role
    bot_member = channel.guild.get_member(bot_user.id)
    default_role = channel.guild.default_role

    # Loop over overwrites checking for explicit send_messages in the allow overwrites.
    for role in overwrites:
        # Skip self role/member and default role (@everyone)
        if role == bot_role or role == bot_member or role == default_role:
            continue

        allow, deny = overwrites[role].pair()
        if allow.send_messages:
            no_effect_roles_allow.append(role)
        if deny.send_messages:
            no_effect_roles_deny.append(role)

    return no_effect_roles_allow, no_effect_roles_deny
