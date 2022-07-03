"""
Contains all the options used in dropdown commands.
"""
import pandas as pd

from discord import Guild, SelectOption
from typing import Optional

from . import db as snorlax_db


async def schedule_options(
    guild: Guild,
    active: Optional[bool] = None
) -> list[SelectOption]:
    """Fetches schedules to present to user.

    The options are formed by creating strings for the user to recognise the schedule
    while these are attached to the database id value.

    Args:
        guild: The guild of the interaction request.
        active: The active parameter that is passed to the load_schedule_db function.

    Returns:
        The list of SelectOptions with the schedule choices.
    """
    schedules_db = await snorlax_db.load_schedule_db(guild_id=guild.id, active=active)
    options = []

    if schedules_db.empty:
        return options

    for i, row in schedules_db[['rowid', 'channel_name', 'open', 'close']].iloc[:25].iterrows():
        label = f"#{row['channel_name']}"
        description = f"Opens @ {row['open']} & Closes @ {row['close']}"
        value = row['rowid']

        options.append(SelectOption(label=label, description=description, value=value, emoji='⏰'))

    return options
