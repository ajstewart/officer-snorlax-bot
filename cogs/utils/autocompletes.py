"""
Contains all the autocomplete functions used in app_commands.
"""

from discord import Interaction, app_commands
from pytz import common_timezones
from typing import List


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
