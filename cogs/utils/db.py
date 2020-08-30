import pandas as pd
import sqlite3
import os
from dotenv import load_dotenv, find_dotenv


load_dotenv(find_dotenv())
DATABASE = os.getenv('DATABASE')
DEFAULT_TZ = os.getenv('DEFAULT_TZ')


def load_schedule_db():

    conn = sqlite3.connect(DATABASE)
    query = "SELECT rowid, * FROM schedules;"

    schedules = pd.read_sql_query(query, conn)

    schedules['warning'] = schedules['warning'].astype(bool)
    schedules['dynamic'] = schedules['dynamic'].astype(bool)

    conn.close()

    return schedules


def load_friend_code_channels_db():
    conn = sqlite3.connect(DATABASE)
    query = "SELECT * FROM fc_channels;"

    fc_channels = pd.read_sql_query(query, conn)

    fc_channels['secret'] = fc_channels['secret'].astype(bool)

    conn.close()

    return fc_channels


def load_guild_db():
    conn = sqlite3.connect(DATABASE)
    query = "SELECT * FROM guilds;"

    guilds = pd.read_sql_query(query, conn)

    conn.close()

    guilds = guilds.set_index('id')

    return guilds


def add_allowed_friend_code_channel(guild, channel, secret="False"):
    """
    Sets the admin channel for a guild and saves
    the updated dataframe to disk.
    """
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
        return False


def add_guild_admin_channel(guild, channel):
    """
    Sets the admin channel for a guild and saves
    the updated dataframe to disk.
    """
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        for row in c.execute(
            "SELECT * FROM guilds WHERE id = {};".format(guild.id)
        ):
            sql_command = (
                """UPDATE guilds SET admin_channel = '{}' WHERE id = {};""".format(
                    channel.id,
                    guild.id
                )
            )
            c.execute(sql_command)
            break

        else:
            sql_command = (
                """INSERT INTO guilds VALUES ({}, "{}", {});""".format(
                    guild.id, DEFAULT_TZ, channel.id
                )
            )
            c.execute(sql_command)

        conn.commit()
        conn.close()

        return True

    except Exception as e:
        return False


def add_guild_tz(guild, tz):
    """
    Sets the timezone for a guild and saves
    the updated dataframe to disk.
    """
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        for row in c.execute(
            "SELECT * FROM guilds WHERE id={}".format(guild.id)
        ):
            entry_id = row[0]
            sql_command = (
                """UPDATE guilds SET tz = '{}' WHERE ID = {};""".format(
                    tz,
                    entry_id
                )
            )
            c.execute(sql_command)
            break

        else:
            sql_command = (
                """INSERT INTO guilds VALUES ({}, "{}", 0);""".format(
                    guild.id, tz
                )
            )
            c.execute(sql_command)

        conn.commit()
        conn.close()

        return True

    except Exception as e:
        return False


def create_schedule(
    ctx, channel, open_time, close_time, open_message="None",
    close_message="None", warning="True", dynamic="True"
):
    """
    Append to the schedule.
    """
    try:
        role = ctx.guild.default_role

        warning = str2bool(warning)
        dynamic = str2bool(dynamic)

        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()

        sql_command = (
            "INSERT INTO schedules VALUES"
            """ ({}, {}, {}, "{}", "{}", "{}", """
            """"{}", "{}", "{}", {}, {}, "99:99");""".format(
                ctx.guild.id,
                channel.id,
                role.id,
                channel.name,
                role.name,
                open_time,
                close_time,
                open_message,
                close_message,
                warning,
                dynamic
            )
        )

        c.execute(sql_command)

        conn.commit()
        conn.close()

        return True

    except Exception as e:
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
        return False


def str2bool(v):
  return v.lower() in ["yes", "true", "t", "1"]


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
