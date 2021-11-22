#!/usr/bin/env python
"""
Script to initialise an empty database for the bot.

The database will be named 'database.db'.

Example:
    python initdb.py
"""

import sqlite3

from pathlib import Path

db_name = 'database.db'
db = Path(db_name)

if db.is_file():
    print('Database already present!')
    print('Will not overwrite.')
else:
    conn = sqlite3.connect(db_name)
    c = conn.cursor()

    # Create the table, read the article below if you
    # are unsure of what they mean
    # https://www.w3schools.com/sql/sql_datatypes.asp
    SQL_STATEMENT = """CREATE TABLE schedules (
        guild INTEGER,
        channel INTEGER,
        role INTEGER,
        channel_name VARCHAR(30),
        role_name VARCHAR(30),
        open CHAR(5),
        close CHAR(5),
        open_message VARCHAR(255),
        close_message VARCHAR(255),
        warning BOOLEAN,
        dynamic BOOLEAN,
        dynamic_close CHAR(5),
        max_num_delays INTEGER,
        current_delay_num INTEGER,
        silent BOOLEAN,
        active BOOLEAN
    );
    """

    c.execute(SQL_STATEMENT)

    SQL_STATEMENT = """CREATE TABLE guilds (
        id INTEGER PRIMARY KEY,
        tz VARCHAR(40),
        admin_channel INTEGER,
        meowth_raid_category INTEGER,
        any_raids_filter BOOLEAN,
        log_channel INTEGER,
        time_channel INTEGER,
        join_name_filter BOOLEAN,
        active BOOLEAN,
        prefix CHAR(3)
    );
    """

    c.execute(SQL_STATEMENT)

    SQL_STATEMENT = """CREATE TABLE fc_channels (
        guild INTEGER,
        channel INTEGER,
        channel_name VARCHAR(40),
        secret BOOLEAN
    );
    """

    c.execute(SQL_STATEMENT)

    # Remember to save + close
    conn.commit()
    conn.close()
