import datetime
import pytz
from discord import Embed
from dotenv import load_dotenv, find_dotenv


load_dotenv(find_dotenv())


def filter_delete_log_embed(message, tz, reason="None") -> Embed:
    """
    Create an embed to send to the logging channel
    """
    tz = pytz.timezone(tz)
    now = datetime.datetime.now(tz=tz)
    user = message.author
    embed = Embed(
        description=f'**Message from {user.mention} deleted in {message.channel.mention}**\n{message.content}',
        timestamp=now,
        color=2061822
    )
    embed.set_author(
        name=f"{user.name}#{user.discriminator}",
        icon_url=user.avatar_url
    )
    embed.add_field(
        name="Reason",
        value=reason
    )
    embed.set_footer(
        text=f"Author: {message.author.id} | Message ID: {message.id}"
    )

    return embed


def schedule_log_embed(
    channel, tz, stype, delay_mins=-1, delay_num=-1, max_delay_num=-1,
) -> Embed:
    """
    Create an embed to send to the logging channel
    """

    if stype not in [
        'close', 'open', 'delay', 'close_skip', 'open_skip', 'warning'
    ]:
        raise ValueError('The schedule type is not recongised!')

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

    return embed