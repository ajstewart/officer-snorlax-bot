import pytz
import time
from .db import load_guild_db, load_schedule_db
import re
from .utils import strip_url, strip_mentions, strip_punctuation
from discord.utils import escape_mentions
import datetime


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


def check_if_channel_active(messages, client_user):
    """
    Check if the channel has seen not client/bot
    activity in the past `past_minutes` minutes.
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


def check_for_friend_code(content):
    pattern = "\d{4}.*\d{4}.*\d{4}(?!(\d*\>))"
    content = strip_mentions(content)
    content = strip_url(content)
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


def check_for_any_raids(content):
    content = strip_punctuation(content)
    content_strip = content.strip().split(" ")
    if content_strip[0] == 'any' and content_strip[-1] in ['raid', 'raids']:
        return True
    else:
        return False


def check_schedule_exists(sched_id: int):
    schedules = load_schedule_db()
    exists = sched_id in schedules['rowid'].astype(int).tolist()

    return exists


def check_remove_schedule(ctx, sched_id: int):
    schedules = load_schedule_db().set_index('rowid')

    schedule_guild = schedules.loc[sched_id]['guild']
    ctx_guild_id = ctx.guild.id

    allowed = schedule_guild == ctx_guild_id

    return allowed
