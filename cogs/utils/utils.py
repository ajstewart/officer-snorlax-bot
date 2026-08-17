"""Misc. utility functions used throughout the bot."""

import datetime
import re
import string

from typing import Callable

import pytz

from discord import Client, Message, User
from discord.ext import commands

from repositories import GuildRepository


def get_current_time(tz: str) -> datetime.datetime:
    """Returns the current time in the selected time zone.

    Args:
        tz: The requested timezone.

    Returns:
        The current time as a datetime.datetime object.
    """
    tz = pytz.timezone(tz)
    return datetime.datetime.now(tz=tz)


def strip_url(content: str) -> str:
    """Strip URLs from message string content.

    Args:
        content: The message content.

    Returns:
        The message content with URLs removed.
    """
    return re.sub(r"http\S+", "", content)


def strip_mentions(content: str) -> str:
    """Strip discord mentions from message string content.

    Args:
        content: The message content.

    Returns:
        The message content with mentions removed.
    """
    return re.sub(r"<(?:[^\d>]+|:[A-Za-z0-9]+:)\w+>", "", content)


def strip_punctuation(content: str) -> str:
    """Remove punctuation from the message content.

    Args:
        content: The message content.

    Returns:
        The message content with punctuation removed.
    """
    return content.translate(str.maketrans("", "", string.punctuation))


def get_hour_emoji(time: str) -> str:
    """Get the relevant emoji to represent the current time.

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
        "01:00": "🕐",
        "02:00": "🕑",
        "03:00": "🕒",
        "04:00": "🕓",
        "05:00": "🕔",
        "06:00": "🕕",
        "07:00": "🕖",
        "08:00": "🕗",
        "09:00": "🕘",
        "10:00": "🕙",
        "11:00": "🕚",
        "12:00": "🕛",
        "01:30": "🕜",
        "02:30": "🕝",
        "03:30": "🕞",
        "04:30": "🕟",
        "05:30": "🕠",
        "06:30": "🕡",
        "07:30": "🕢",
        "08:30": "🕣",
        "09:30": "🕤",
        "10:30": "🕥",
        "11:30": "🕦",
        "12:30": "🕧",
    }

    return emojis[key]


async def get_prefix(client: User, message: Message) -> Callable[[Client], list[str]]:
    """Fetch the current prefix of the guild and check whether it has been called.

    Args:
        client: The user that represents the bot.
        message: The Message object that represents the message of the command.

    Returns:
        The callable to be passed to the bot initialisation.
    """
    async with client.db_session() as session:
        guild_repo = GuildRepository(session)
        guild_db = await guild_repo.get(message.guild.id)

    prefix = guild_db.prefix

    return commands.when_mentioned_or(*prefix)(client, message)
