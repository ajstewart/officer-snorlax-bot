"""Contains all the options used in dropdown commands."""

from typing import Optional

from discord import Guild, SelectOption
from sqlalchemy.ext.asyncio import AsyncSession

from repositories import ScheduleRepository


async def schedule_options(
    session: AsyncSession, guild: Guild, active: Optional[bool] = None
) -> list[SelectOption]:
    """Fetch the schedules to present to the user.

    The options are formed by creating strings for the user to recognise the schedule
    while these are attached to the database id value.

    Args:
        session: The database session.
        guild: The guild of the interaction request.
        active: The active parameter that is passed to the load_schedule_db function.

    Returns:
        The list of SelectOptions with the schedule choices.
    """
    schedules_repo = ScheduleRepository(session)
    schedules_db = await schedules_repo.get_all(guild.id, active=active)
    options = []

    if not schedules_db:
        return options

    for schedule in schedules_db:
        label = f"#{schedule.channel_name}"
        description = f"Opens @ {schedule.open} & Closes @ {schedule.close}"
        value = schedule.id

        options.append(
            SelectOption(label=label, description=description, value=value, emoji="⏰")
        )

    return options
