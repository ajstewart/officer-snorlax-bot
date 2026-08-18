"""Contains all the autocomplete functions used in app_commands."""

from discord import Interaction, app_commands
from pytz import common_timezones

from bot_logger import get_logger
from repositories import FriendCodeChannelRepository, ScheduleRepository

logger = get_logger(__name__)


async def timezones_autocomplete(
    interaction: Interaction, current: str
) -> list[app_commands.Choice[str]]:
    """Obtain the searchable choices for the timezone entry.

    Uses pytz.common_timezones() to populate the list.

    Args:
        interaction: The interaction that triggered the command and choice call.
        current: The current typed entry by the user.

    Returns:
        The list of filtered choices.
    """
    choices = [
        app_commands.Choice(name=tz, value=tz)
        for tz in common_timezones
        if current.lower() in tz.lower()
    ]

    if len(choices) > 25:
        choices = choices[:25]

    return choices


async def schedule_selection_autocomplete(
    interaction: Interaction, current: str
) -> list[app_commands.Choice[str]]:
    """Fetch schedules to present to the user.

    A string is built from the schedule information so the user can recognise the
    schedule they want. This is linked to the database id value.

    Args:
        interaction: The interaction that triggered the command and choice call.
        current: The current typed entry by the user.

    Returns:
        The list of filtered schedule choices.
    """
    if interaction.command.name in ["activate-schedule"]:
        active = False
    elif interaction.command.name in ["deactivate-schedule"]:
        active = True
    else:
        active = None

    async with interaction.client.db_session() as session:
        schedule_repo = ScheduleRepository(session)
        schedules_db = await schedule_repo.get_all(
            guild_id=interaction.guild.id, active=active
        )

    if not schedules_db:
        return []

    choices = [
        app_commands.Choice(name=schedule.label, value=str(schedule.rowid))
        for schedule in schedules_db
        if current.lower() in schedule.label.lower()
    ]

    if len(choices) > 25:
        choices = choices[:25]

    return choices


async def friend_code_channel_autocomplete(
    interaction: Interaction, current: str
) -> list[app_commands.Choice[str]]:
    """Fetch the friend code channels to present to the user to toggle secret.

    The options are formed by creating strings for the user to recognise the channel
    while the values are the channel id.

    Args:
        interaction: The interaction that is performing the command.
        current: The current typed entry by the user.

    Returns:
        The list of SelectOptions with the friend code channels.
    """
    guild = interaction.guild

    async with interaction.client.db_session() as session:
        fc_channel_repo = FriendCodeChannelRepository(session)
        fc_channels_db = await fc_channel_repo.get_all(guild_id=guild.id)

    choices = []

    if not fc_channels_db:
        return choices

    secret_human = {True: "Secret ✅", False: "Secret ❌"}

    for channel_db in fc_channels_db:
        # Check if the channel still exists
        try:
            channel = channel_db.channel
            interaction.guild.get_channel(channel)
        except Exception as e:
            logger.error(
                f"Channel fetch failed for channel {channel} in guild"
                f" {interaction.guild.name} (error: {e})."
            )
            continue

        secret = channel_db.secret
        label = (
            f"#{channel_db.channel_name}: {secret_human[secret]} ->"
            f" {secret_human[not secret]}"
        )
        value = f"{channel}-{not secret}"

        if current.lower() in label.lower():
            choices.append(app_commands.Choice(name=label, value=value))

    if len(choices) > 25:
        choices = choices[:25]

    return choices
