"""Contains all the database operations performed by the bot."""

import os
import pandas as pd
import sqlite3

from discord import Guild, TextChannel
from discord.ext import commands
from dotenv import load_dotenv, find_dotenv
from typing import Optional, Union

from .utils import str2bool


load_dotenv(find_dotenv())
DATABASE = os.getenv('DATABASE')
DEFAULT_TZ = os.getenv('DEFAULT_TZ')
DEFAULT_PREFIX = os.getenv('DEFAULT_PREFIX')


def load_schedule_db(
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
    conn = sqlite3.connect(DATABASE)
    query = "SELECT rowid, * FROM schedules;"

    schedules = pd.read_sql_query(query, conn)

    conn.close()

    schedules['active'] = schedules['active'].astype(bool)
    schedules['warning'] = schedules['warning'].astype(bool)
    schedules['dynamic'] = schedules['dynamic'].astype(bool)
    schedules['silent'] = schedules['silent'].astype(bool)

    if guild_id is not None:
        schedules = schedules.loc[schedules['guild'] == guild_id]

    if active_only:
        schedules = schedules.loc[schedules['active'] == True]

    return schedules


def load_friend_code_channels_db() -> pd.DataFrame:
    """
    Loads the friend code channels database table and returns as a pandas
    dataframe.

    Returns:
        A pandas dataframe containing the table.
    """
    conn = sqlite3.connect(DATABASE)
    query = "SELECT * FROM fc_channels;"

    fc_channels = pd.read_sql_query(query, conn)

    fc_channels['secret'] = fc_channels['secret'].astype(bool)

    conn.close()

    return fc_channels


def load_guild_db(active_only: bool = False) -> pd.DataFrame:
    """
    Loads the guilds database table and returns as a pandas dataframe.

    Args:
        active_only: If True, only active guilds are returned.

    Returns:
        A pandas dataframe containing the table.
    """
    conn = sqlite3.connect(DATABASE)
    query = "SELECT * FROM guilds;"

    guilds = pd.read_sql_query(query, conn)

    if active_only:
        guilds = guilds.loc[guilds['active']==True]

    conn.close()

    guilds = guilds.set_index('id')

    guilds['any_raids_filter'] = guilds['any_raids_filter'].astype(bool)
    guilds['join_name_filter'] = guilds['join_name_filter'].astype(bool)
    guilds['active'] = guilds['active'].astype(bool)

    return guilds


def get_guild_prefix(guild_id: int) -> str:
    """
    Fetches the string prefix of the requested guild.

    TODO: Does this fail when the guild is not present?

    Args:
        guild_id: The id of the guild to obtain the prefix for.

    Returns:
        The prefix of the server.
    """
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    query = "SELECT prefix FROM guilds WHERE id={};".format(guild_id)
    c.execute(query)

    prefix = c.fetchone()[0]

    return prefix


def add_allowed_friend_code_channel(
    guild: Guild,
    channel: TextChannel,
    secret: str = "False"
) -> bool:
    """
    Adds an allowed friend code channel to the database.

    Args:
        guild: The discord guild object.
        channel: The discord textchannel object.
        secret: Whether the channel should be marked as secret in the database.

    Returns:
        A bool to signify that the database transaction was successful
        ('True') or not ('False').
    """
    # TODO: This is an awkward way of doing it really.
    #       Should change check to be in the actual command code.
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()

        secret = str2bool(secret)

        for row in c.execute(
            "SELECT * FROM fc_channels WHERE guild = {} AND channel = {};".format(
                guild.id, channel.id
            )
        ):
            break

        else:
            sql_command = (
                """INSERT INTO fc_channels VALUES ({}, {}, "{}", {});""".format(
                    guild.id, channel.id, channel.name, secret
                )
            )
            c.execute(sql_command)

        conn.commit()
        conn.close()

        return True

    except Exception as e:
        conn.close()
        return False


def add_guild_admin_channel(guild: Guild, channel: TextChannel) -> bool:
    """
    Records the admin channel for the guild to the database.

    Args:
        guild: The discord guild object.
        channel: The discord textchannel object.

    Returns:
        A bool to signify that the database transaction was successful
        ('True') or not ('False').
    """
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        sql_command = (
            """UPDATE guilds SET admin_channel = '{}' WHERE id = {};""".format(
                channel.id,
                guild.id
            )
        )
        c.execute(sql_command)

        conn.commit()
        conn.close()

        return True

    except Exception as e:
        conn.close()
        return False


def add_guild_log_channel(guild: Guild, channel: TextChannel) -> bool:
    """
    Records the log channel for the guild to the database.

    Args:
        guild: The discord guild object.
        channel: The discord textchannel object.

    Returns:
        A bool to signify that the database transaction was successful
        ('True') or not ('False').
    """
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        sql_command = (
            """UPDATE guilds SET log_channel = '{}' WHERE id = {};""".format(
                channel.id,
                guild.id
            )
        )
        c.execute(sql_command)

        conn.commit()
        conn.close()

        return True

    except Exception as e:
        conn.close()
        return False


def add_guild_time_channel(guild: Guild, channel: TextChannel) -> bool:
    """
    Records the time channel for a guild to the database.

    Args:
        guild: The discord guild object.
        channel: The discord textchannel object.

    Returns:
        A bool to signify that the database transaction was successful
        ('True') or not ('False').
    """
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        sql_command = (
            """UPDATE guilds SET time_channel = '{}' WHERE id = {};""".format(
                channel.id,
                guild.id
            )
        )
        c.execute(sql_command)

        conn.commit()
        conn.close()

        return True

    except Exception as e:
        conn.close()
        return False


def add_guild_tz(guild: Guild, tz: str) -> bool:
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
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        sql_command = (
            """UPDATE guilds SET tz = '{}' WHERE id = {};""".format(
                tz,
                guild.id
            )
        )
        c.execute(sql_command)

        conn.commit()
        conn.close()

        return True

    except Exception as e:
        conn.close()
        return False


def add_guild_meowth_raid_category(guild: Guild, channel: TextChannel) -> bool:
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
    channel_id = channel if channel == -1 else channel.id

    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        sql_command = (
            "UPDATE guilds SET meowth_raid_category"
            " = {} WHERE id = {};".format(channel_id, guild.id)
        )
        c.execute(sql_command)

        conn.commit()
        conn.close()

        return True

    except Exception as e:
        conn.close()
        return False


def create_schedule(
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

        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()

        sql_command = (
            "INSERT INTO schedules VALUES"
            """ ({}, {}, {}, "{}", "{}", "{}", """
            """"{}", "{}", "{}", {}, {}, "99:99", {}, 0, {}, True);""".format(
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
                max_num_delays,
                silent
            )
        )

        c.execute(sql_command)
        rowid = int(c.lastrowid)

        conn.commit()
        conn.close()

        return True, rowid

    except Exception as e:
        conn.close()
        return False, 0


def update_schedule(
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
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()

        if column in [
            "open",
            "close",
            "open_message",
            "close_message",
        ]:
            sql_command = (
                "UPDATE schedules SET {}"
                " = '{}' WHERE rowid = {};".format(
                    column, value, schedule_id
                )
            )
        else:
            sql_command = (
                "UPDATE schedules SET {}"
                " = {} WHERE rowid = {};".format(
                    column, value, schedule_id
                )
            )

        c.execute(sql_command)

        conn.commit()
        conn.close()

        return True
    except Exception as e:
        conn.close()
        return False


def drop_allowed_friend_code_channel(
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
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        for row in c.execute(
            "SELECT rowid FROM fc_channels WHERE guild = {} "
            "AND channel = {};".format(guild.id, channel.id)
        ):
            id_to_drop = row[0]
            sql_command = (
                "DELETE FROM fc_channels WHERE rowid = {};".format(
                    id_to_drop
                )
            )

            c.execute(sql_command)

        conn.commit()
        conn.close()

        return True

    except Exception as e:
        conn.close()
        return False


def drop_schedule(ctx: TextChannel, id_to_drop: int) -> bool:
    """
    Remove a channel from the schedule table.

    Args:
        ctx: The command context containing the message content and other
            metadata.
        id_to_drop: The database id of the schedule to drop.

    Returns:
        A bool to signify that the database transaction was successful
        ('True') or not ('False').
    """
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()

        sql_command = (
            "DELETE FROM schedules WHERE rowid = {};".format(
                id_to_drop
            )
        )

        c.execute(sql_command)

        conn.commit()
        conn.close()

        return True

    except Exception as e:
        conn.close()
        return False


def update_dynamic_close(
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
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    sql_command = (
        "UPDATE schedules SET dynamic_close = '{}' WHERE rowid = {};".format(
            new_close_time, schedule_id
        )
    )

    c.execute(sql_command)

    conn.commit()
    conn.close()


def update_current_delay_num(schedule_id: int, new_delay_num: int = 0) -> None:
    """
    Update the current delay number of a schedule in the database.

    Args:
        schedule_id: The database id of the schedule to update.
        new_delay_num: The new delay_num of the schedule.

    Returns:
        None
    """
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    sql_command = (
        "UPDATE schedules SET current_delay_num"
        " = {} WHERE rowid = {};".format(
            new_delay_num, schedule_id
        )
    )

    c.execute(sql_command)

    conn.commit()
    conn.close()


def toggle_any_raids_filter(guild: Guild, any_raids: Union[str, bool]) -> bool:
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
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()

        sql_command = (
            "UPDATE guilds SET any_raids_filter"
            " = {} WHERE id = {};".format(any_raids, guild.id)
        )
        c.execute(sql_command)

        conn.commit()
        conn.close()

        return True

    except Exception as e:
        conn.close()
        return False


def toggle_join_name_filter(guild: Guild, join_name: str) -> bool:
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
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()

        sql_command = (
            "UPDATE guilds SET join_name_filter"
            " = {} WHERE id = {};".format(join_name, guild.id)
        )
        c.execute(sql_command)

        conn.commit()
        conn.close()

        return True

    except Exception as e:
        conn.close()
        return False


def set_guild_active(guild_id: int, value: Union[str, bool]) -> bool:
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
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()

        sql_command = (
            "UPDATE guilds SET active = {} WHERE id = {};".format(
                value, guild_id
            )
        )

        c.execute(sql_command)

        conn.commit()
        conn.close()

        return True

    except Exception as e:
        conn.close()
        return False


def add_guild(guild: Guild) -> bool:
    """
    Adds a guild to the database.

    Args:
        guild: The discord guild object.

    Returns:
        A bool to signify that the database transaction was successful
        ('True') or not ('False').
    """
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        sql_command = (
            """INSERT INTO guilds VALUES ({}, "{}", -1, -1, """
            """False, -1, -1, False, True, '{}');""".format(
                guild.id, DEFAULT_TZ, DEFAULT_PREFIX
            )
        )
        c.execute(sql_command)

        conn.commit()
        conn.close()

        return True

    except Exception as e:
        conn.close()
        return False


def set_guild_prefix(guild_id: int, value: str) -> bool:
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
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()

        sql_command = (
            "UPDATE guilds SET prefix = '{}' WHERE id = {};".format(
                value, guild_id
            )
        )

        c.execute(sql_command)

        conn.commit()
        conn.close()

        return True

    except Exception as e:
        conn.close()
        return False
