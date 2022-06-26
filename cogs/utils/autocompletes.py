"""
Contains all the autocomplete functions used in app_commands.
"""
import pandas as pd

from discord import Interaction, app_commands
from pytz import common_timezones
from typing import List

from . import db as snorlax_db


async def timezones_autocomplete(
    interaction: Interaction,
    current: str
) -> List[app_commands.Choice[str]]:
    choices = [
        app_commands.Choice(name=tz, value=tz)
        for tz in common_timezones if current.lower() in tz.lower()
    ]

    if len(choices) > 25:
        choices = choices[:25]

    return choices


async def schedule_selection_autocomplete(
    interaction: Interaction,
    current: str
) -> List[app_commands.Choice[str]]:
    """Fetches schedules to present to user.
    """
    if interaction.command.name in ['activate-schedule']:
        active = False
    elif interaction.command.name in ['deactivate-schedule']:
        active = True

    schedules_db = await snorlax_db.load_schedule_db(guild_id=interaction.guild.id, active=active)

    if schedules_db.empty:
        return []

    # create a label so humans can see the schedule
    # TODO: Is this worth being a database column?
    schedules_db['label'] = schedules_db[['channel_name', 'open', 'close']].apply(
        lambda x: f"⏰ #{x['channel_name']}: Opens @ {x['open']} & Closes @ {x['close']}",
        axis=1
    )

    schedule_dict = pd.Series(
        schedules_db['rowid'].astype(str).tolist(), index=schedules_db['label']
    ).to_dict()

    choices = [
        app_commands.Choice(name=label, value=schedule_dict[label])
        for label in schedule_dict if current.lower() in label.lower()
    ]

    if len(choices) > 25:
        choices = choices[:25]

    return choices
