import pytz
import time
from .db import load_guild_db
import re
from discord.utils import escape_mentions


def check_bot(ctx):
    if ctx.author.bot:
        return False
    else:
        return True


def check_admin(ctx):
    """
    Checks whether the user is an admin.
    """
    if ctx.author.guild_permissions.administrator:
        return True
    else:
        return False


def check_admin_channel(ctx):
    """
    Checks if the channel is the set admin channel
    """
    guild_db = load_guild_db()
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


def check_for_friend_code(content):
    pattern = "\d{4}.*\d{4}.*\d{4}(?!(\d*\>))"
    content = escape_mentions(content)
    match = re.search(pattern, content)
    if match:
        return True
    else:
        return False


def check_valid_timezone(tz):
    """
    Checks whether the tz sting is a valid
    timezone using pytz.
    """
    if tz in pytz.all_timezones:
        return True
    else:
        return False


def check_time_format(time_input):
    """
    Checks user time input.
    """
    try:
        time.strptime(time_input, '%H:%M')
        return True
    except ValueError:
        return False


