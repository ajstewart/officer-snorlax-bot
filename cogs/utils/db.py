import pandas as pd
import sqlite3
import os
from dotenv import load_dotenv, find_dotenv

from .utils import str2bool


load_dotenv(find_dotenv())
DATABASE = os.getenv('DATABASE')
DEFAULT_TZ = os.getenv('DEFAULT_TZ')
DEFAULT_PREFIX = os.getenv('DEFAULT_PREFIX')


def load_schedule_db(guild_id: int = None, active_only: bool = False):

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


def load_friend_code_channels_db():
    conn = sqlite3.connect(DATABASE)
    query = "SELECT * FROM fc_channels;"

    fc_channels = pd.read_sql_query(query, conn)

    fc_channels['secret'] = fc_channels['secret'].astype(bool)

    conn.close()

    return fc_channels


def load_guild_db(active_only=False):
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


def get_guild_prefix(guild_id: int):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    query = "SELECT prefix FROM guilds WHERE id={};".format(guild_id)
    c.execute(query)

    prefix = c.fetchone()[0]

    return prefix


def add_allowed_friend_code_channel(guild, channel, secret="False"):
    """
    Adds an allowed friend code channel.
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


def add_guild_admin_channel(guild, channel):
    """
    Sets the admin channel for a guild and saves
    the updated dataframe to disk.
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


def add_guild_log_channel(guild, channel):
    """
    Sets the log channel for a guild and saves
    the updated dataframe to disk.
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


def add_guild_time_channel(guild, channel):
    """
    Sets the time channel for a guild and saves
    the updated dataframe to disk.
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


def add_guild_tz(guild, tz):
    """
    Sets the timezone for a guild and saves
    the updated dataframe to disk.
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


def add_guild_meowth_raid_category(guild, channel):
    """
    Sets the Meowth raid category for Meowth such that
    the friend code filter can play nice with the created channels.
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
    guild_id, channel_id, channel_name, role_id, role_name, open_time,
    close_time, open_message="None", close_message="None", warning="False",
    dynamic="True", max_num_delays=1, silent="False"
):
    """
    Append to the schedule.
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


def update_schedule(schedule_id, column, value):
    """Update a parameter of a schedule."""
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


def drop_allowed_friend_code_channel(guild, channel):
    """
    Drops a channel from the allowed whitelist.
    """
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        for row in c.execute(
            "SELECT rowid FROM fc_channels WHERE guild = {} AND channel = {};".format(
                guild.id, channel.id
            )
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


def drop_schedule(ctx, id_to_drop):
    """
    Remove a channel from the schedule.
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


def update_dynamic_close(schedule_id, new_close_time="99:99"):
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


def update_current_delay_num(schedule_id, new_delay_num=0):
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


def toggle_any_raids_filter(guild, any_raids):
    """
    Sets the Meowth raid category for Meowth such that
    the friend code filter can play nice with the created channels.
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


def toggle_join_name_filter(guild, join_name):
    """
    Toggles the join name filter on and off.
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


def set_guild_active(guild_id, value):
    """
    Toggles the guild active status on and off
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


def add_guild(guild):
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        sql_command = (
            """INSERT INTO guilds VALUES ({}, "{}", -1, -1, False, -1, -1, False, True, '{}');""".format(
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


def set_guild_prefix(guild_id, value: str):
    """
    Sets the guild prefix.
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