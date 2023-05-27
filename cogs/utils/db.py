"""Contains all the database operations performed by the bot."""

import logging
import os

from typing import Any, Optional, Union

import aiosqlite
import pandas as pd

from discord import Guild, TextChannel
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())
DATABASE = os.getenv("DATABASE")
DEFAULT_TZ = os.getenv("DEFAULT_TZ")
DEFAULT_PREFIX = os.getenv("DEFAULT_PREFIX")
DEFAULT_OPEN_MESSAGE = os.getenv("DEFAULT_OPEN_MESSAGE")
DEFAULT_CLOSE_MESSAGE = os.getenv("DEFAULT_CLOSE_MESSAGE")
DEFAULT_WARNING_TIME = os.getenv("DEFAULT_WARNING_TIME")
DEFAULT_INACTIVE_TIME = os.getenv("DEFAULT_INACTIVE_TIME")
DEFAULT_DELAY_TIME = os.getenv("DEFAULT_DELAY_TIME")


async def _get_schedule_db() -> tuple[tuple[Any], tuple[str]]:
    """Loads entire schedule database table.

    Returns:
        The rows of the database table.
        The columns of the database table.
    """
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute("PRAGMA table_info(schedules);") as cursor:
            columns = ["rowid"] + [i[1] for i in await cursor.fetchall()]
        async with db.execute("SELECT rowid, * FROM schedules") as cursor:
            rows = await cursor.fetchall()

    return rows, columns


async def _get_single_schedule(rowid: int) -> tuple[tuple[Any], tuple[str]]:
    """Gets a single schedule from the database schedules table.

    Args:
        rowid: The rowid to fetch.

    Returns:
        The rows of the database table.
        The columns of the database table.
    """
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute("PRAGMA table_info(schedules);") as cursor:
            columns = ["rowid"] + [i[1] for i in await cursor.fetchall()]
        query = "SELECT rowid, * FROM schedules WHERE rowid = ?"
        async with db.execute(query, (rowid,)) as cursor:
            rows = await cursor.fetchall()

    return rows, columns


async def _get_guild_schedule_settings(guild_id: int) -> tuple[tuple[Any], tuple[str]]:
    """Gets the settings row from the guild schedule settings database table.

    Args:
        guild_id: The guild to fetch.

    Returns:
        The rows of the database table.
        The columns of the database table.
    """
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute("PRAGMA table_info(guild_schedule_settings);") as cursor:
            columns = [i[1] for i in await cursor.fetchall()]
        query = "SELECT * FROM guild_schedule_settings WHERE guild = ?"
        async with db.execute(query, (guild_id,)) as cursor:
            rows = await cursor.fetchall()

    return rows, columns


async def _get_guild_db():
    """Loads entire guild database table.

    Returns:
        The rows of the database table.
        The columns of the database table.
    """
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute("PRAGMA table_info(guilds);") as cursor:
            columns = [i[1] for i in await cursor.fetchall()]
        async with db.execute("SELECT * FROM guilds") as cursor:
            rows = await cursor.fetchall()

    return rows, columns


async def _get_fc_channels_db():
    """Loads the friend code filter database table.

    Returns:
        The rows of the database table.
        The columns of the database table.
    """
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute("PRAGMA table_info(fc_channels);") as cursor:
            columns = [i[1] for i in await cursor.fetchall()]
        async with db.execute("SELECT * FROM fc_channels") as cursor:
            rows = await cursor.fetchall()

    return rows, columns


async def load_schedule_db(
    guild_id: Optional[int] = None,
    active: Optional[bool] = None,
    rowid: Optional[int] = None,
) -> pd.DataFrame:
    """Loads the schedules database table and returns it as a pandas dataframe.

    Args:
        guild_id: If provided, the returned schedules will be limited to only
            that specific guild id.
        active: If provided the schedule will be filtered by the provided
            active status. E.g. if `True` then only active schedules will be returned,
            `False` will return inactive.
        rowid: Select a single schedule to return. 'guild_id' and 'active' will be
            set to 'None' regardless of input.

    Returns:
        A pandas dataframe containing the contents of the table.
    """
    if rowid is None:
        rows, columns = await _get_schedule_db()
    else:
        rows, columns = await _get_single_schedule(rowid=rowid)
        guild_id = active = None

    # Sort into a pandas dataframe as it's just much easier to deal with.
    schedules = pd.DataFrame(rows, columns=columns)

    schedules["active"] = schedules["active"].astype(bool)
    schedules["warning"] = schedules["warning"].astype(bool)
    schedules["dynamic"] = schedules["dynamic"].astype(bool)
    schedules["silent"] = schedules["silent"].astype(bool)

    if guild_id is not None:
        schedules = schedules.loc[schedules["guild"] == guild_id]

    if active is not None:
        if active:
            schedules = schedules.loc[schedules["active"]]
        else:
            schedules = schedules.loc[~schedules["active"]]

    return schedules


async def load_guild_schedule_settings(guild_id: int) -> pd.DataFrame:
    """Loads the guild_schedule_settings for the required guild.

    Args:
        guild_id: The guild to load.

    Returns:
        A pandas dataframe containing the settings.
    """
    rows, columns = await _get_guild_schedule_settings(guild_id)
    guild_schedule_settings = pd.DataFrame(rows, columns=columns)

    return guild_schedule_settings


async def load_friend_code_channels_db(guild_id: Optional[int] = None) -> pd.DataFrame:
    """Load the friend code channels database table and returns as a pandas dataframe.

    Args:
        guild_id: The guild id to load specifically. Will load all if not provided.

    Returns:
        A pandas dataframe containing the table.
    """
    rows, columns = await _get_fc_channels_db()

    fc_channels = pd.DataFrame(rows, columns=columns)

    fc_channels["secret"] = fc_channels["secret"].astype(bool)
    fc_channels["guild"] = fc_channels["guild"].astype(int)
    fc_channels["channel"] = fc_channels["channel"].astype(int)

    if guild_id is not None:
        fc_channels = fc_channels[fc_channels["guild"] == guild_id].reset_index(
            drop=True
        )

    return fc_channels


async def load_guild_db(active_only: bool = False) -> pd.DataFrame:
    """Loads the guilds database table and returns as a pandas dataframe.

    Args:
        active_only: If True, only active guilds are returned.

    Returns:
        A pandas dataframe containing the table.
    """
    rows, columns = await _get_guild_db()

    guilds = pd.DataFrame(rows, columns=columns)

    guilds["any_raids_filter"] = guilds["any_raids_filter"].astype(bool)
    guilds["join_name_filter"] = guilds["join_name_filter"].astype(bool)
    guilds["active"] = guilds["active"].astype(bool)

    if active_only:
        guilds = guilds.loc[guilds["active"]]

    guilds = guilds.set_index("id")

    return guilds


async def get_guild_prefix(guild_id: int) -> str:
    """Fetches the string prefix of the requested guild.

    TODO: Does this fail when the guild is not present?

    Args:
        guild_id: The id of the guild to obtain the prefix for.

    Returns:
        The prefix of the server.
    """
    async with aiosqlite.connect(DATABASE) as db:
        query = "SELECT prefix FROM guilds WHERE id = ?;"
        async with db.execute(query, (guild_id,)) as cursor:
            prefix = await cursor.fetchone()

    return prefix[0]


async def add_allowed_friend_code_channel(
    guild: Guild, channel: TextChannel, secret: bool = False
) -> bool:
    """Adds an allowed friend code channel to the database.

    Args:
        guild: The discord guild object.
        channel: The discord TextChannel object.
        secret: Whether the channel should be marked as secret in the database.

    Returns:
        A bool to signify that the database transaction was successful
        ('True') or not ('False').
    """
    # TODO: This is an awkward way of doing it really.
    #       Should change check to be in the actual command code.
    try:
        async with aiosqlite.connect(DATABASE) as db:
            async with db.cursor() as cursor:
                query = "SELECT * FROM fc_channels WHERE guild = ? AND channel = ?"
                await cursor.execute(query, (guild.id, channel.id))
                data = await cursor.fetchone()
                if not data:
                    insert_cmd = (
                        "INSERT INTO fc_channels(guild, channel, channel_name, secret)"
                        " VALUES (?, ?, ?, ?);"
                    )
                    await cursor.execute(
                        insert_cmd, (guild.id, channel.id, channel.name, secret)
                    )

            await db.commit()

        return True

    except Exception:
        return False


async def add_guild_admin_channel(
    guild: Guild, channel: Optional[TextChannel] = None
) -> bool:
    """Records the admin channel for the guild to the database.

    Args:
        guild: The discord guild object.
        channel: The discord textchannel object.

    Returns:
        A bool to signify that the database transaction was successful
        ('True') or not ('False').
    """
    if channel is None:
        channel_id = -1
    else:
        channel_id = channel.id

    try:
        async with aiosqlite.connect(DATABASE) as db:
            sql_command = "UPDATE guilds SET admin_channel = ? WHERE id = ?"
            await db.execute(sql_command, (channel_id, guild.id))
            await db.commit()

        return True

    except Exception:
        return False


async def add_guild_log_channel(
    guild: Guild, channel: Optional[TextChannel] = None
) -> bool:
    """Records the log channel for the guild to the database.

    Args:
        guild: The discord guild object.
        channel: The discord textchannel object.

    Returns:
        A bool to signify that the database transaction was successful
        ('True') or not ('False').
    """
    if channel is None:
        channel_id = -1
    else:
        channel_id = channel.id

    try:
        async with aiosqlite.connect(DATABASE) as db:
            sql_command = "UPDATE guilds SET log_channel = ? WHERE id = ?"
            await db.execute(sql_command, (channel_id, guild.id))
            await db.commit()

        return True

    except Exception:
        return False


async def add_guild_time_channel(
    guild: Guild, channel: Optional[TextChannel] = None
) -> bool:
    """Records the time channel for a guild to the database.

    Args:
        guild: The discord guild object.
        channel: The discord textchannel object.

    Returns:
        A bool to signify that the database transaction was successful
        ('True') or not ('False').
    """
    if channel is None:
        channel_id = -1
    else:
        channel_id = channel.id

    try:
        async with aiosqlite.connect(DATABASE) as db:
            sql_command = "UPDATE guilds SET time_channel = ? WHERE id = ?"
            await db.execute(sql_command, (channel_id, guild.id))
            await db.commit()

        return True

    except Exception:
        return False


async def add_guild_tz(guild: Guild, tz: str) -> bool:
    """Sets the timezone for a guild and saves it to the database.

    Args:
        guild: The discord guild object.
        tz: The string timezone to assign to the guild.

    Returns:
        A bool to signify that the database transaction was successful
        ('True') or not ('False').
    """
    try:
        async with aiosqlite.connect(DATABASE) as db:
            sql_command = "UPDATE guilds SET tz = ? WHERE id = ?"
            await db.execute(sql_command, (tz, guild.id))
            await db.commit()

        return True

    except Exception:
        return False


async def add_guild_meowth_raid_category(
    guild: Guild, channel: Optional[TextChannel] = None
) -> bool:
    """Sets the Meowth/Pokenav raid category for the guild and writes it to the db.

    Args:
        guild: The discord guild object.
        channel: The discord textchannel object, but representing a category.

    Returns:
        A bool to signify that the database transaction was successful
        ('True') or not ('False').
    """
    if channel is None:
        channel_id = -1
    else:
        channel_id = channel.id

    try:
        async with aiosqlite.connect(DATABASE) as db:
            sql_command = "UPDATE guilds SET meowth_raid_category = ? WHERE id = ?"
            await db.execute(sql_command, (channel_id, guild.id))
            await db.commit()

        return True

    except Exception:
        return False


async def create_schedule(
    guild_id: int,
    channel_id: int,
    channel_name: str,
    role_id: int,
    role_name: str,
    open_time: str,
    close_time: str,
    open_message: Optional[str] = None,
    close_message: Optional[str] = None,
    warning: bool = False,
    dynamic: bool = False,
    max_num_delays: int = 1,
    silent: bool = False,
) -> tuple[bool, int]:
    """Save a new channel schedule to the database.

    Args:
        guild_id: The id of the associated guild.
        channel_id: The id of the channel for the schedule.
        channel_name: The name of the channel.
        role_id: The id of the role to close the channel for.
        role_name: The name of the role.
        open_time: The time to set as the open time (must be 24 %H:%M
            format, e.g. '10:00').
        close_time: The time to set as the close time (must be 24 %H:%M
            format, e.g. '20:00').
        open_message: Custom message to add to the opening message.
        close_message: Custom message to add to the closing message.
        warning: True or False setting for the warning option of the schedule.
        dynamic: True or False setting for the dynamic option of the schedule.
        max_num_delays: The maximum number of delays that can occur when using
            the dynamic mode.
        silent: True or False setting for whether the channel should be
            opened and closed silently.

    Returns:
        A bool to signify that the database transaction was successful
        ('True') or not ('False').
    """
    if open_message is None:
        open_message = "None"

    if close_message is None:
        close_message = "None"

    try:
        async with aiosqlite.connect(DATABASE) as db:
            sql_command = (
                "INSERT INTO schedules(guild, channel, role, channel_name, role_name,"
                " open, close, open_message, close_message, warning, dynamic,"
                " dynamic_close, max_num_delays, current_delay_num, silent, active,"
                " last_open_message, last_close_message) VALUES (?, ?, ?, ?, ?, ?, ?,"
                " ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            )
            params = (
                guild_id,
                channel_id,
                role_id,
                channel_name,
                role_name,
                open_time,
                close_time,
                open_message,
                close_message,
                warning,
                dynamic,
                "99:99",
                max_num_delays,
                0,
                silent,
                True,
                0,  # last_open_message
                0,  # last_close_message
            )
            async with db.execute(sql_command, params) as cursor:
                rowid = cursor.lastrowid

            await db.commit()

        return True, rowid

    except Exception:
        return False, 0


async def update_schedule(
    schedule_id: int, column: str, value: Union[str, bool, int]
) -> bool:
    """Update a parameter of an existing schedule.

    Currently entered columns must be valid before use. No checks are
    performed in the method itself.

    Args:
        schedule_id: The database id number of the schedule.
        column: The column name, or key, of the value to update.
        value: The value to set.

    Returns:
        A bool to signify that the database transaction was successful
        ('True') or not ('False').
    """
    try:
        async with aiosqlite.connect(DATABASE) as db:
            sql_command = f"UPDATE schedules SET {column} = ? WHERE rowid = ?"
            await db.execute(sql_command, (value, schedule_id))
            await db.commit()

        return True

    except Exception:
        return False


async def drop_allowed_friend_code_channel(guild_id: int, channel_id: int) -> bool:
    """Drops a channel from the allowed whitelist.

    Arguments have to be id values in the event of a channel being deleted.

    Args:
        guild_id: The discord guild id.
        channel_id: The discord channel id.

    Returns:
        A bool to signify that the database transaction was successful
        ('True') or not ('False').
    """
    try:
        async with aiosqlite.connect(DATABASE) as db:
            sql_query = "SELECT rowid FROM fc_channels WHERE guild = ? AND channel = ?"
            async with db.execute(sql_query, (guild_id, channel_id)) as cursor:
                async for row in cursor:
                    # row is a tuple of the row id only, e.g. (2,)
                    await cursor.execute("DELETE FROM fc_channels WHERE rowid = ?", row)

            await db.commit()

        return True

    except Exception:
        return False


async def check_friend_code_channel(channel_id: int) -> bool:
    """Checks whether the requested channel is in the friend code database.

    Args:
        channel_id: The id of the channel to be checked.

    Returns:
        True if present, False if not.
    """
    async with aiosqlite.connect(DATABASE) as db:
        query = "SELECT channel_name FROM fc_channels WHERE channel = ?;"
        async with db.execute(query, (channel_id,)) as cursor:
            open = await cursor.fetchone()

    return False if open is None else True


async def set_friend_code_channel_secret(
    guild_id: int, channel_id: int, secret: Union[str, bool]
) -> bool:
    """Set the friend code whitelist entry secret value to the desired value.

    Args:
        guild_id: The discord guild object.
        channel_id: The channel it applies to.
        secret: The boolean value of True or False.

    Returns:
        A bool to signify that the database transaction was successful
        ('True') or not ('False').
    """
    try:
        async with aiosqlite.connect(DATABASE) as db:
            sql_command = (
                "UPDATE fc_channels SET secret = ? WHERE guild = ? AND channel = ?"
            )
            await db.execute(sql_command, (secret, guild_id, channel_id))
            await db.commit()

        return True

    except Exception:
        return False


async def drop_schedule(id_to_drop: int) -> bool:
    """Remove a channel from the schedule table.

    Args:
        id_to_drop: The database id of the schedule to drop.

    Returns:
        A bool to signify that the database transaction was successful
        ('True') or not ('False').
    """
    try:
        async with aiosqlite.connect(DATABASE) as db:
            sql_command = "DELETE FROM schedules WHERE rowid = ?"
            await db.execute(sql_command, (id_to_drop,))
            await db.commit()

        return True

    except Exception:
        return False


async def update_dynamic_close(schedule_id: int, new_close_time: str = "99:99") -> None:
    """Update the dynamic close time field of a schedule in the database.

    Args:
        schedule_id: The database id of the schedule to update.
        new_close_time: The new dynamic close time of the schedule in 24h %H:%M
            format.

    Returns:
        None
    """
    async with aiosqlite.connect(DATABASE) as db:
        sql_command = "UPDATE schedules SET dynamic_close = ? WHERE rowid = ?"
        await db.execute(sql_command, (new_close_time, schedule_id))
        await db.commit()


async def update_current_delay_num(schedule_id: int, new_delay_num: int = 0) -> None:
    """Update the current delay number of a schedule in the database.

    Args:
        schedule_id: The database id of the schedule to update.
        new_delay_num: The new delay_num of the schedule.

    Returns:
        None
    """
    async with aiosqlite.connect(DATABASE) as db:
        sql_command = "UPDATE schedules SET current_delay_num = ? WHERE rowid = ?"
        await db.execute(sql_command, (new_delay_num, schedule_id))
        await db.commit()


async def toggle_any_raids_filter(guild: Guild, any_raids: Union[str, bool]) -> bool:
    """Sets the 'any raids' filter to be on or off.

    Args:
        guild: The discord guild object.
        any_raids: The setting for the any raids filter to set.

    Returns:
        A bool to signify that the database transaction was successful
        ('True') or not ('False').
    """
    try:
        async with aiosqlite.connect(DATABASE) as db:
            sql_command = "UPDATE guilds SET any_raids_filter = ? WHERE id = ?"
            await db.execute(sql_command, (any_raids, guild.id))
            await db.commit()

        return True

    except Exception:
        return False


async def toggle_join_name_filter(guild: Guild, join_name: str) -> bool:
    """Toggles the join name filter on and off.

    Args:
        guild: The discord guild object.
        join_name: The setting for the join name filter to set.

    Returns:
        A bool to signify that the database transaction was successful
        ('True') or not ('False').
    """
    try:
        async with aiosqlite.connect(DATABASE) as db:
            sql_command = "UPDATE guilds SET join_name_filter = ? WHERE id = ?"
            await db.execute(sql_command, (join_name, guild.id))
            await db.commit()

        return True

    except Exception:
        return False


async def set_guild_active(guild_id: int, value: Union[str, bool]) -> bool:
    """Toggles the guild active status on and off.

    Args:
        guild_id: The id of the guild to set the value for.
        value: The True or False setting for the guild.

    Returns:
        A bool to signify that the database transaction was successful
        ('True') or not ('False').
    """
    try:
        async with aiosqlite.connect(DATABASE) as db:
            sql_command = "UPDATE guilds SET active = ? WHERE id = ?"
            await db.execute(sql_command, (value, guild_id))
            await db.commit()

    except Exception:
        return False


async def add_guild(guild: Guild) -> bool:
    """Adds a guild to the database.

    Args:
        guild: The discord guild object.

    Returns:
        A bool to signify that the database transaction was successful
        ('True') or not ('False').
    """
    try:
        async with aiosqlite.connect(DATABASE) as db:
            sql_command = (
                "INSERT INTO guilds(id, tz, meowth_raid_category, any_raids_filter,"
                " log_channel, time_channel, join_name_filter, active, prefix,"
                " admin_channel) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            )
            params = (
                guild.id,
                DEFAULT_TZ,
                -1,
                False,
                -1,
                -1,
                False,
                True,
                DEFAULT_PREFIX,
                -1,
            )
            await db.execute(sql_command, params)
            await db.commit()

        return True

    except Exception as e:
        logging.error(e)
        return False


async def set_guild_prefix(guild_id: int, value: str) -> bool:
    """Sets the guild prefix.

    Args:
        guild_id: The discord guild object.
        value: The prefix to set.

    Returns:
        A bool to signify that the database transaction was successful
        ('True') or not ('False').
    """
    try:
        async with aiosqlite.connect(DATABASE) as db:
            sql_command = "UPDATE guilds SET prefix = ? WHERE id = ?"
            await db.execute(sql_command, (value, guild_id))
            await db.commit()

        return True

    except Exception:
        return False


async def get_schedule_open(schedule_id: int) -> str:
    """Fetches the open time of the requested schedule.

    Args:
        schedule_id: The id of the schedule to obtain the open time for.

    Returns:
        The schedule open time.
    """
    async with aiosqlite.connect(DATABASE) as db:
        query = "SELECT open FROM schedules WHERE rowid = ?;"
        async with db.execute(query, (schedule_id,)) as cursor:
            open = await cursor.fetchone()

    return open[0]


async def get_schedule_close(schedule_id: int) -> str:
    """Fetches the close time of the requested schedule.

    Args:
        schedule_id: The id of the schedule to obtain the close time for.

    Returns:
        The schedule close time.
    """
    async with aiosqlite.connect(DATABASE) as db:
        query = "SELECT close FROM schedules WHERE rowid = ?;"
        async with db.execute(query, (schedule_id,)) as cursor:
            close = await cursor.fetchone()

    return close[0]


async def get_schedule_channel(schedule_id: int) -> str:
    """Fetches the channel id of the requested schedule.

    Args:
        schedule_id: The id of the schedule to obtain the close time for.

    Returns:
        The schedule channel id.
    """
    async with aiosqlite.connect(DATABASE) as db:
        query = "SELECT channel FROM schedules WHERE rowid = ?;"
        async with db.execute(query, (schedule_id,)) as cursor:
            channel = await cursor.fetchone()

    return channel[0]


async def get_schedule_ids_by_channel_id(channel_id: int) -> list[tuple[int]]:
    """Fetches the schedule(s) of the requested channel id.

    Args:
        channel_id: The channel_id to get the schedules for.

    Returns:
        The schedule rows.
    """
    async with aiosqlite.connect(DATABASE) as db:
        query = "SELECT rowid FROM schedules WHERE channel = ?"
        async with db.execute(query, (channel_id,)) as cursor:
            schedule_ids = await cursor.fetchall()

    return schedule_ids


async def check_schedule_exists_with_times(
    channel_id: int, open: str, close: str
) -> bool:
    """Checks if the schedule with the channel and open and close times exists.

    Args:
        channel_id: The channel id to check.
        open: The open time to check.
        close: The close time to check

    Returns:
        'True' if exists, 'False' if not.
    """
    async with aiosqlite.connect(DATABASE) as db:
        query = (
            "SELECT EXISTS(SELECT 1 FROM schedules WHERE channel = ? AND open = ? and"
            " close = ?)"
        )
        async with db.execute(query, (channel_id, open, close)) as cursor:
            exists = await cursor.fetchone()

    return bool(exists[0])


async def check_schedule_exists(schedule_id: int) -> bool:
    """Fetches the schedule(s) of the requested channel id.

    Args:
        schedule_id: The schedule id (rowid) to check.

    Returns:
        'True' if exists, 'False' if not.
    """
    async with aiosqlite.connect(DATABASE) as db:
        query = "SELECT EXISTS(SELECT 1 FROM schedules WHERE rowid = ?)"
        async with db.execute(query, (schedule_id,)) as cursor:
            exists = await cursor.fetchone()

    return bool(exists[0])


async def get_guild_admin_channel(guild_id: int) -> str:
    """Fetches the admin channel of the requested guild.

    Args:
        guild_id: The id of the guild to obtain the admin channel for.

    Returns:
        The guild admin channel.
    """
    async with aiosqlite.connect(DATABASE) as db:
        query = "SELECT admin_channel FROM guilds WHERE id = ?;"
        async with db.execute(query, (guild_id,)) as cursor:
            admin_channel = await cursor.fetchone()

    return admin_channel[0]


async def get_guild_log_channel(guild_id: int) -> str:
    """Fetches the log channel of the requested guild.

    Args:
        guild_id: The id of the guild to obtain the log channel for.

    Returns:
        The guild log channel.
    """
    async with aiosqlite.connect(DATABASE) as db:
        query = "SELECT log_channel FROM guilds WHERE id = ?;"
        async with db.execute(query, (guild_id,)) as cursor:
            log_channel = await cursor.fetchone()

    return log_channel[0]


async def get_guild_time_channel(guild_id: int) -> str:
    """Fetches the time channel of the requested guild.

    Args:
        guild_id: The id of the guild to obtain the time channel for.

    Returns:
        The guild time channel.
    """
    async with aiosqlite.connect(DATABASE) as db:
        query = "SELECT time_channel FROM guilds WHERE id = ?;"
        async with db.execute(query, (guild_id,)) as cursor:
            time_channel = await cursor.fetchone()

    return time_channel[0]


async def get_guild_tz(guild_id: int) -> str:
    """Fetches the time channel of the requested guild.

    Args:
        guild_id: The id of the guild to obtain the time channel for.

    Returns:
        The guild time channel.
    """
    async with aiosqlite.connect(DATABASE) as db:
        query = "SELECT tz FROM guilds WHERE id = ?;"
        async with db.execute(query, (guild_id,)) as cursor:
            guild_tz = await cursor.fetchone()

    return guild_tz[0]


async def get_guild_any_raids_active(guild_id: int) -> bool:
    """Fetches the any raids filter value of the requested guild.

    Args:
        guild_id: The id of the guild to obtain the any raids value.

    Returns:
        The guild time channel.
    """
    async with aiosqlite.connect(DATABASE) as db:
        query = "SELECT any_raids_filter FROM guilds WHERE id = ?;"
        async with db.execute(query, (guild_id,)) as cursor:
            any_raids = await cursor.fetchone()

    return bool(any_raids[0])


async def get_guild_join_name_active(guild_id: int) -> bool:
    """Fetches the join name filter value of the requested guild.

    Args:
        guild_id: The id of the guild to obtain the any raids value.

    Returns:
        The guild time channel.
    """
    async with aiosqlite.connect(DATABASE) as db:
        query = "SELECT join_name_filter FROM guilds WHERE id = ?;"
        async with db.execute(query, (guild_id,)) as cursor:
            join_name = await cursor.fetchone()

    return bool(join_name[0])


async def get_guild_raid_category(guild_id: int) -> bool:
    """Fetches the Meowth raid category value of the requested guild.

    Args:
        guild_id: The id of the guild to obtain the raid category.

    Returns:
        The guild raid category.
    """
    async with aiosqlite.connect(DATABASE) as db:
        query = "SELECT meowth_raid_category FROM guilds WHERE id = ?;"
        async with db.execute(query, (guild_id,)) as cursor:
            raid_category = await cursor.fetchone()

    return raid_category[0]


async def check_schedule_settings_exists(guild_id: int) -> bool:
    """Checks whether an entry exists for the guild in the guild_schedule_settings db.

    Args:
        guild_id: The guild id to check.

    Returns:
        'True' if exists, 'False' if not.
    """
    async with aiosqlite.connect(DATABASE) as db:
        query = "SELECT EXISTS(SELECT 1 FROM guild_schedule_settings WHERE guild = ?)"
        async with db.execute(query, (guild_id,)) as cursor:
            exists = await cursor.fetchone()

    return bool(exists[0])


async def add_default_schedule_settings(guild_id: int) -> bool:
    """Enters a row into the guild_schedule_settings table with default settings.

    Args:
        guild_id: The guild to enter.

    Returns:
        'True' if entry was successful, 'False' if not.
    """
    try:
        async with aiosqlite.connect(DATABASE) as db:
            sql_command = (
                "INSERT INTO guild_schedule_settings(guild, base_open_message,"
                " base_close_message, warning_time, inactive_time, delay_time) VALUES"
                " (?, ?, ?, ?, ?, ?)"
            )
            params = (
                guild_id,
                DEFAULT_OPEN_MESSAGE,
                DEFAULT_CLOSE_MESSAGE,
                DEFAULT_WARNING_TIME,
                DEFAULT_INACTIVE_TIME,
                DEFAULT_DELAY_TIME,
            )
            await db.execute(sql_command, params)
            await db.commit()

        return True

    except Exception as e:
        logging.error(e)
        return False


async def update_guild_schedule_settings(
    guild_id: int, column: str, value: Union[str, bool, int]
) -> bool:
    """Update a parameter of the guild schedule settings db.

    Currently entered columns must be valid before use. No checks are
    performed in the method itself.

    Args:
        guild_id: The guild_id to update.
        column: The column name, or key, of the value to update.
        value: The value to set.

    Returns:
        A bool to signify that the database transaction was successful
        ('True') or not ('False').
    """
    try:
        async with aiosqlite.connect(DATABASE) as db:
            sql_command = (
                f"UPDATE guild_schedule_settings SET {column} = ? WHERE guild = ?"
            )
            await db.execute(sql_command, (value, guild_id))
            await db.commit()

        return True

    except Exception:
        return False


async def get_schedule_last_open_message(schedule_id: int) -> str:
    """Fetches the channel id of the requested schedule.

    Args:
        schedule_id: The id of the schedule to obtain the close time for.

    Returns:
        The schedule channel id.
    """
    async with aiosqlite.connect(DATABASE) as db:
        query = "SELECT last_open_message FROM schedules WHERE rowid = ?;"
        async with db.execute(query, (schedule_id,)) as cursor:
            last_open_message = await cursor.fetchone()

    last_open_message = last_open_message[0]

    if last_open_message is not None:
        last_open_message = int(last_open_message)

    return last_open_message


async def get_schedule_last_close_message(schedule_id: int) -> str:
    """Fetches the channel id of the requested schedule.

    Args:
        schedule_id: The id of the schedule to obtain the close time for.

    Returns:
        The schedule channel id.
    """
    async with aiosqlite.connect(DATABASE) as db:
        query = "SELECT last_close_message FROM schedules WHERE rowid = ?;"
        async with db.execute(query, (schedule_id,)) as cursor:
            last_close_message = await cursor.fetchone()

    last_close_message = last_close_message[0]

    if last_close_message is not None:
        last_close_message = int(last_close_message)

    return last_close_message
