"""Contains all the database operations performed by the bot."""

import aiosqlite
import os
import pandas as pd

from discord import Guild, TextChannel
from dotenv import load_dotenv, find_dotenv
from typing import Optional, Union

from .utils import str2bool


load_dotenv(find_dotenv())
DATABASE = os.getenv('DATABASE')
DEFAULT_TZ = os.getenv('DEFAULT_TZ')
DEFAULT_PREFIX = os.getenv('DEFAULT_PREFIX')


async def _get_schedule_db():
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute(f'PRAGMA table_info(schedules);') as cursor:
            columns = ['rowid'] + [i[1] for i in await cursor.fetchall()]
        async with db.execute("SELECT rowid, * FROM schedules") as cursor:
            rows = await cursor.fetchall()

    return rows, columns


async def _get_guild_db():
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute(f'PRAGMA table_info(guilds);') as cursor:
            columns = [i[1] for i in await cursor.fetchall()]
        async with db.execute("SELECT * FROM guilds") as cursor:
            rows = await cursor.fetchall()

    return rows, columns


async def _get_fc_channels_db():
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute(f'PRAGMA table_info(fc_channels);') as cursor:
            columns = [i[1] for i in await cursor.fetchall()]
        async with db.execute("SELECT * FROM fc_channels") as cursor:
            rows = await cursor.fetchall()

    return rows, columns


async def load_schedule_db(
    guild_id: Optional[int] = None,
    active_only: bool = False
) -> pd.DataFrame:
    """
    Loads the schedules database table and returns it as a pandas dataframe.

    Args:
        guild_id: If provided, the returned schedules will be limited to only
            that specific guild id.
        active_only: If True, only schedules from active guilds are returned.

    Returns:
        A pandas dataframe containing the contents of the table.
    """
    rows, columns = await _get_schedule_db()

    # Sort into a pandas dataframe as it's just much easier to deal with.
    schedules = pd.DataFrame(rows, columns=columns)

    schedules['active'] = schedules['active'].astype(bool)
    schedules['warning'] = schedules['warning'].astype(bool)
    schedules['dynamic'] = schedules['dynamic'].astype(bool)
    schedules['silent'] = schedules['silent'].astype(bool)

    if guild_id is not None:
        schedules = schedules.loc[schedules['guild'] == guild_id]

    if active_only:
        schedules = schedules.loc[schedules['active']]

    return schedules


async def load_friend_code_channels_db() -> pd.DataFrame:
    """
    Loads the friend code channels database table and returns as a pandas
    dataframe.

    Returns:
        A pandas dataframe containing the table.
    """
    rows, columns = await _get_fc_channels_db()

    fc_channels = pd.DataFrame(rows, columns=columns)

    fc_channels['secret'] = fc_channels['secret'].astype(bool)

    return fc_channels


async def load_guild_db(active_only: bool = False) -> pd.DataFrame:
    """
    Loads the guilds database table and returns as a pandas dataframe.

    Args:
        active_only: If True, only active guilds are returned.

    Returns:
        A pandas dataframe containing the table.
    """
    rows, columns = await _get_guild_db()

    guilds = pd.DataFrame(rows, columns=columns)

    guilds['any_raids_filter'] = guilds['any_raids_filter'].astype(bool)
    guilds['join_name_filter'] = guilds['join_name_filter'].astype(bool)
    guilds['active'] = guilds['active'].astype(bool)

    if active_only:
        guilds = guilds.loc[guilds['active']]

    guilds = guilds.set_index('id')

    return guilds


async def get_guild_prefix(guild_id: int) -> str:
    """
    Fetches the string prefix of the requested guild.

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
    guild: Guild,
    channel: TextChannel,
    secret: bool = False
) -> bool:
    """
    Adds an allowed friend code channel to the database.

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
                    insert_cmd = "INSERT INTO fc_channels VALUES (?, ?, ?, ?);"
                    await cursor.execute(insert_cmd, (guild.id, channel.id, channel.name, secret))

            await db.commit()

        return True

    except Exception as e:
        return False


async def add_guild_log_channel(guild: Guild, channel: Optional[TextChannel] = None) -> bool:
    """
    Records the log channel for the guild to the database.

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

    except Exception as e:
        return False


async def add_guild_time_channel(guild: Guild, channel: Optional[TextChannel] = None) -> bool:
    """
    Records the time channel for a guild to the database.

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

    except Exception as e:
        return False


async def add_guild_tz(guild: Guild, tz: str) -> bool:
    """
    Sets the timezone for a guild and saves it to the database.

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

    except Exception as e:
        return False


async def add_guild_meowth_raid_category(guild: Guild, channel: Optional[TextChannel] = None) -> bool:
    """
    Sets the Meowth/Pokenav raid category for the guild and writes it to the
    database.

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

    except Exception as e:
        return False


async def create_schedule(
    guild_id: int,
    channel_id: int,
    channel_name: str,
    role_id: int,
    role_name: str,
    open_time: str,
    close_time: str,
    open_message: Optional[str] = "None",
    close_message: Optional[str] = "None",
    warning: str = "False",
    dynamic: str = "True",
    max_num_delays: int = 1,
    silent: str = "False"
) -> bool:
    """
    Save a new channel schedule to the database.

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
    try:
        warning = str2bool(warning)
        dynamic = str2bool(dynamic)
        silent = str2bool(silent)

        async with aiosqlite.connect(DATABASE) as db:
            sql_command = "INSERT INTO schedules VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
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
                True
            )
            async with db.execute(sql_command, params) as cursor:
                rowid = cursor.lastrowid

            await db.commit()

        return True, rowid

    except Exception as e:
        return False, 0


async def update_schedule(
    schedule_id: int,
    column: str,
    value: Union[str, bool, int]
) -> bool:
    """
    Update a parameter of an existing schedule.

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

    except Exception as e:
        return False


async def drop_allowed_friend_code_channel(
    guild: Guild,
    channel: TextChannel
) -> bool:
    """
    Drops a channel from the allowed whitelist.

    Args:
        guild: The discord guild object.
        channel: The discord TextChannel object.

    Returns:
        A bool to signify that the database transaction was successful
        ('True') or not ('False').
    """
    try:
        async with aiosqlite.connect(DATABASE) as db:
            sql_query = "SELECT rowid FROM fc_channels WHERE guild = ? AND channel = ?"
            async with db.execute(sql_query, (guild.id, channel.id)) as cursor:
                async for row in cursor:
                    # row is a tuple of the row id only, e.g. (2,)
                    await cursor.execute("DELETE FROM fc_channels WHERE rowid = ?", row)

            await db.commit()

        return True

    except Exception as e:
        return False


async def check_friend_code_channel(channel_id: int) -> bool:
    """
    Checks whether the requested channel is in the friend code database.

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


async def drop_schedule(id_to_drop: int) -> bool:
    """
    Remove a channel from the schedule table.

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

    except Exception as e:
        return False


async def update_dynamic_close(
    schedule_id: int,
    new_close_time: str = "99:99"
) -> None:
    """
    Update the dynamic close time field of a schedule in the database.

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
    """
    Update the current delay number of a schedule in the database.

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
    """
    Sets the 'any raids' filter to be on or off.

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

    except Exception as e:
        return False


async def toggle_join_name_filter(guild: Guild, join_name: str) -> bool:
    """
    Toggles the join name filter on and off.

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

    except Exception as e:
        return False


async def set_guild_active(guild_id: int, value: Union[str, bool]) -> bool:
    """
    Toggles the guild active status on and off.

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

    except Exception as e:
        return False


async def add_guild(guild: Guild) -> bool:
    """
    Adds a guild to the database.

    Args:
        guild: The discord guild object.

    Returns:
        A bool to signify that the database transaction was successful
        ('True') or not ('False').
    """
    try:
        async with aiosqlite.connect(DATABASE) as db:
            sql_command = "INSERT INTO guilds VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            params = (
                guild.id,
                DEFAULT_TZ,
                -1,
                -1,
                False,
                -1,
                -1,
                False,
                True,
                DEFAULT_PREFIX
            )
            await db.execute(sql_command, params)
            await db.commit()

        return True

    except Exception as e:
        return False


async def set_guild_prefix(guild_id: int, value: str) -> bool:
    """
    Sets the guild prefix.

    Args:
        guild: The discord guild object.
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

    except Exception as e:
        return False


async def get_schedule_open(schedule_id: int) -> str:
    """
    Fetches the open time of the requested schedule.

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
    """
    Fetches the close time of the requested schedule.

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


async def get_guild_log_channel(guild_id: int) -> str:
    """
    Fetches the log channel of the requested guild.

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
    """
    Fetches the time channel of the requested guild.

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
    """
    Fetches the time channel of the requested guild.

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
    """
    Fetches the any raids filter value of the requested guild.

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
    """
    Fetches the join name filter value of the requested guild.

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
    """
    Fetches the Meowth raid category value of the requested guild.

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
