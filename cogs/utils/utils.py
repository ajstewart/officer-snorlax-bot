import pytz
import datetime
from discord import Embed


def get_current_time(tz):
    """
    Returns the current time in the selected time zone.
    """
    tz = pytz.timezone(tz)
    return datetime.datetime.now(tz=tz)


def get_schedule_embed(ctx, schedule_db, tz):
    """
    Create an embed to show the schedules.
    """
    tz = pytz.timezone(tz)
    now = datetime.datetime.now(tz=tz)
    embed = Embed(
        title='Active Schedules',
        timestamp=now,
        color=2061822
    )
    for i, row in schedule_db.iterrows():
        embed.add_field(
            name='ID: {}'.format(row.rowid),
            value=(
                "Channel: <#{}>\nOpen: **{}**\nOpen Custom Message: **{}**\n"
                "Close: **{}**\nClose Custom Message: **{}**".format(
                    row.channel, row.open, row.open_message,
                    row.close, row.close_message
                )
            ),
            inline=False
        )

    return embed

def get_friend_channels_embed(ctx, friend_db):
    """
    Create an embed to show the schedules.
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