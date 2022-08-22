"""
Contains all the autocomplete functions used in app_commands.
"""
import pandas as pd

from discord import Interaction, app_commands
from pytz import common_timezones

from . import db as snorlax_db


async def timezones_autocomplete(
    interaction: Interaction,
    current: str
) -> list[app_commands.Choice[str]]:
    """The searchable choices for the timezone entry.

    Uses pytz.common_timezones() to populate the list.

    Args:
        interaction: The interaction that triggered the command and choice call.
        current: The current typed entry by the user.

    Returns:
        The list of filtered choices.
    """
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
) -> list[app_commands.Choice[str]]:
    """Fetches schedules to present to the user.

    A string is built from the schedule information so the user can recognise the
    schedule they want. This is linked to the database id value.

    Args:
        interaction: The interaction that triggered the command and choice call.
        current: The current typed entry by the user.

    Returns:
        The list of filtered schedule choices.
    """
    if interaction.command.name in ['activate-schedule']:
        active = False
    elif interaction.command.name in ['deactivate-schedule']:
        active = True
    else:
        active = None

    schedules_db = await snorlax_db.load_schedule_db(guild_id=interaction.guild.id, active=active)

    if schedules_db.empty:
        return []

    # create a label so humans can see the schedule
    # TODO: Is this worth being a database column?
    schedules_db['label'] = schedules_db[['channel_name', 'open', 'close']].apply(
        lambda x: f"{x['channel_name']}: Opens @ {x['open']} & Closes @ {x['close']}",
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
