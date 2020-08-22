import discord
import os
from dotenv import load_dotenv
from discord.ext import commands, tasks
from discord.utils import get
from discord import TextChannel, Role
from typing import Optional
from discord import Embed
import traceback
import datetime
import pandas as pd
import pytz
import time
import sys

# LOADS THE .ENV FILE THAT RESIDES ON THE SAME LEVEL AS THE SCRIPT.
load_dotenv()

# GRAB THE API TOKEN FROM THE .ENV FILE.
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
SCHEDULE_FILE = os.getenv('SCHEDULE_FILE')
GUILD_FILE = os.getenv('GUILD_FILE')


def load_dbs(sched_file, tz_file):
    if os.path.isfile(sched_file):
        schedule = pd.read_csv(sched_file, index_col=[0,1,2])
    else:
        schedule = pd.DataFrame(
            columns=[
                'channel_name',
                'role_name',
                'open',
                'close',
            ],
            index=pd.MultiIndex(
                levels=[[],[],[]],
                codes=[[],[],[]],
                names=[u'guild', u'channel', u'role']
            )
        )

    if os.path.isfile(tz_file):
        guilds = pd.read_csv(tz_file, index_col=[0])
    else:
        guilds = pd.DataFrame(
            columns=['guild', 'tz', 'admin_channel']
        ).set_index('guild')

    return schedule, guilds


def check_admin(ctx):
    """
    Checks whether the user is an admin.
    """
    if ctx.author.guild_permissions.administrator:
        return True
    else:
        return False


def check_admin_channel(ctx):
    """
    Checks if the channel is the set admin channel
    """
    if ctx.guild.id in GUILD_DB.index:
        admin_channel = GUILD_DB.loc[
            ctx.guild.id, 'admin_channel'
        ]
        if ctx.channel.id == admin_channel:
            return True
        else:
            return False
    else:
        return False


def add_guild_admin_channel(guild, channel):
    """
    Sets the admin channel for a guild and saves
    the updated dataframe to disk.
    """
    try:
        GUILD_DB.loc[guild.id, 'admin_channel'] = channel.id
        GUILD_DB.to_csv(GUILD_FILE)
        return True
    except Exception as e:
        return False


def add_guild_tz(guild, tz):
    """
    Sets the timezone for a guild and saves
    the updated dataframe to disk.
    """
    try:
        GUILD_DB.loc[guild.id, 'tz'] = tz
        GUILD_DB.to_csv(GUILD_FILE)
        return True
    except Exception as e:
        return False


def check_valid_timezone(tz):
    """
    Checks whether the tz sting is a valid
    timezone using pytz.
    """
    if tz in pytz.all_timezones:
        return True
    else:
        return False


def check_guild_tz(guild):
    try:
        tz = GUILD_DB.loc[guild.id, 'tz']
        if isinstance(tz, str):
            return True, tz
        else:
            return False, None
    except Exception as e:
        return False, None


def get_current_time(tz):
    """
    Returns the current time in the selected time zone.
    """
    tz = pytz.timezone(tz)
    return datetime.datetime.now(tz=tz)


def check_time_format(time_input):
    """
    Checks user time input.
    """
    try:
        time.strptime(time_input, '%H:%M')
        return True
    except ValueError:
        return False


def create_schedule(ctx, channel, open_time, close_time):
    """
    Append to the schedule.
    """
    role = ctx.guild.default_role

    try:
        SCHEDULE_DB.loc[
            (ctx.guild.id, channel.id, role.id)
        ] = [
            channel.name, role.name, open_time, close_time
        ]
        SCHEDULE_DB.to_csv(SCHEDULE_FILE)
        return True

    except Exception as e:
        return False


def drop_schedule(ctx, channel):
    """
    Remove a channel from the schedule.
    """
    role = ctx.guild.default_role

    try:
        SCHEDULE_DB.drop(
            (ctx.guild.id, channel.id, role.id),
            inplace=True
        )
        if SCHEDULE_DB.empty:
            os.remove(SCHEDULE_FILE)
        else:
            SCHEDULE_DB.to_csv(SCHEDULE_FILE)

        return True

    except Exception as e:
        return False


def get_schedule_embed(ctx):
    """
    Create an embed to show the schedules.
    """
    timezone_known, tz = check_guild_tz(ctx.guild)
    tz = pytz.timezone(tz)
    now = datetime.datetime.now(tz=tz)
    embed = Embed(
        title='Active Schedules',
        timestamp=now,
        color=2061822
    )
    for i, row in SCHEDULE_DB.loc[
        ctx.guild.id, ['channel_name', 'open', 'close']
    ].iterrows():
        embed.add_field(
            name='#' + row.channel_name,
            value="Open: {}\tClose: {}".format(
                row.open, row.close
            ),
            inline=False
        )

    return embed


# def do_opening_or_closing(row, now):



SCHEDULE_DB, GUILD_DB = load_dbs(
    SCHEDULE_FILE, GUILD_FILE
)


# GETS THE CLIENT OBJECT FROM DISCORD.PY. CLIENT IS SYNONYMOUS WITH BOT.
bot = commands.Bot(command_prefix=commands.when_mentioned_or('!'))
bot.help_command.add_check(check_admin)

# EVENT LISTENER FOR WHEN THE BOT HAS SWITCHED FROM OFFLINE TO ONLINE.
@bot.event
async def on_ready():
    guild_count = 0

    # LOOPS THROUGH ALL THE GUILD / SERVERS THAT THE BOT IS ASSOCIATED WITH.
    for guild in bot.guilds:
        # PRINT THE SERVER'S ID AND NAME.
        print(f"- {guild.id} (name: {guild.name})")

        # INCREMENTS THE GUILD COUNTER.
        guild_count = guild_count + 1

    # PRINTS HOW MANY GUILDS / SERVERS THE BOT IS IN.
    print("Snorlax is in " + str(guild_count) + " guilds.")

    await bot.change_presence(
        activity=discord.Game(
            name="Blocking channels in {} servers".format(guild_count)
        )
    )

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.CheckFailure):
        print('Check failure occurred.')
    else:
        print('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)


@bot.command(
    help=(
        "Will print the current time for the guild if the"
        " timezone has been set (see setTimezone)."
    ),
    brief="Shows the current time for the guild."
)
@commands.check(check_admin_channel)
@commands.check(check_admin)
async def currentTime(ctx):
    """
    Docstring goes here.
    """
    timezone_known, tz = check_guild_tz(ctx.guild)
    if timezone_known:
        the_time = get_current_time(tz)
        msg = (
            "The current time is {}.".format(
                the_time.strftime("%H:%M")
            )
        )
    else:
        msg = (
            "Timezone not known for this guild!"
            " Use 'setTimezone' to set it."
        )

    await ctx.channel.send(msg)


@bot.command(
    help=(
        "Will list all the active schedules for the"
        " guild, showing the open and close times."
    ),
    brief="Show a list of active schedules."
)
@commands.check(check_admin_channel)
@commands.check(check_admin)
async def listSchedules(ctx):
    """
    Docstring goes here.
    """
    if ctx.guild.id not in SCHEDULE_DB.index.get_level_values(0):
        await ctx.channel.send("There are no schedules set.")
    else:
        embed = get_schedule_embed(ctx)

        await ctx.channel.send(embed=embed)


@bot.command(
    help=(
        "Receive a pong from the bot."
    ),
    brief="Get a pong."
)
@commands.check(check_admin_channel)
@commands.check(check_admin)
async def ping(ctx):
    await ctx.channel.send("pong")


@bot.command(
    help=(
        "Remove a channel from the active schedules."
    ),
    brief="Remove a channel from the active schedules."
)
@commands.check(check_admin_channel)
@commands.check(check_admin)
async def removeSchedule(ctx, channel: Optional[TextChannel]):
    """
    Docstring goes here.
    """
    ok = drop_schedule(ctx, channel)

    if ok:
        msg = 'Schedule for {} removed successfully'.format(
            channel.mention
        )
    else:
        msg = 'Error during removal of {} schedule.'.format(
            channel.mention
        )

    await ctx.channel.send(msg)


@bot.command(
    help=(
        "Sets the command channel for the guild where Snorlax"
        " will listen for commands. This is the only command that"
        " can be run from any channel."
    ),
    brief="Set the command channel for the bot."
)
@commands.check(check_admin)
async def setCommandChannel(ctx, channel: Optional[TextChannel]):
    """
    Docstring goes here.
    """
    guild = ctx.guild
    ok = add_guild_admin_channel(guild, channel)
    if ok:
        msg = (
            "{} set as the Snorlax admin channel successfully."
            " Make sure Snorlax has the correct permissions!".format(
                channel.mention
            )
        )
    else:
        msg = (
            "Error when setting the admin channel."
        )
    await ctx.channel.send(msg)


@bot.command(
    help=(
        "Create an opening and closing schedule for a channel"
        " in the guild. Times must be provided in 24 hour format"
        " e.g. '21:00'."
    ),
    brief="Create an opening and closing schedule for a channel."
)
@commands.check(check_admin_channel)
@commands.check(check_admin)
async def setSchedule(
    ctx, channel: Optional[TextChannel], open_time: str, close_time: str
):
    """
    Docstring goes here.
    """
    timezone_known, tz = check_guild_tz(ctx.guild)
    if not timezone_known:
        msg = (
            "Timezone not known for this guild!"
            " Use 'setTimezone' to set it first."
        )
        await ctx.channel.send(msg)
        return

    if not check_time_format(open_time):
        msg = (
            "{} is not a valid time.".format(
                open_time
            )
        )
        await ctx.channel.send(msg)
        return

    if not check_time_format(close_time):
        msg = (
            "{} is not a valid time.".format(
                close_time
            )
        )
        await ctx.channel.send(msg)
        return

    ok = create_schedule(ctx, channel, open_time, close_time)

    if ok:
        msg = "Schedule set successfully."
    else:
        msg = "Error when setting schedule."

    await ctx.channel.send(msg)


@bot.command(
    help=(
        "Set the timezone for the guild. Use standard tz"
        " timezones, e.g. 'Australia/Sydney'."
    ),
    brief="Set the timezone for the guild."
)
@commands.check(check_admin_channel)
@commands.check(check_admin)
async def setTimezone(ctx, tz: str):
    """
    Docstring goes here.
    """
    if not check_valid_timezone(tz):
        msg = '{} is not a valid timezone'.format(
            tz
        )
    else:
        ok = add_guild_tz(ctx.guild, tz)
        if ok:
            msg = (
                "{} set as the timezone successfully.".format(
                    tz
                )
            )
        else:
            msg = (
                "Error when setting the timezone."
            )
    await ctx.channel.send(msg)


@tasks.loop(seconds=61)
async def channel_manager():
    await bot.wait_until_ready()
    for tz in GUILD_DB['tz'].unique():
        timezone = pytz.timezone(tz)
        now = datetime.datetime.now(tz=timezone).strftime(
            "%H:%M"
        )
        guilds = GUILD_DB.loc[GUILD_DB['tz'] == tz].index.values

        guild_mask = [
            g in guilds for g in SCHEDULE_DB.index.get_level_values(0).values
        ]

        scheds_to_check = SCHEDULE_DB.loc[guild_mask, :]

        for i,row in scheds_to_check.iterrows():
            if row.open == now:
                channel = bot.get_channel(i[1])
                role = get(channel.guild.roles, id=i[2])
                await channel.set_permissions(role, send_messages=None)
                await channel.send("Used the Poke Fluté, Snorlax woke up! Channel open!")

            if row.close == now:
                channel = bot.get_channel(i[1])
                role = get(channel.guild.roles, id=i[2])
                await channel.send(
                    "Snorlax is blocking the path! "
                    "Channel closed! Will reopen at {}.".format(
                        row.open
                    )
                )
                await channel.set_permissions(role, send_messages=False)



channel_manager.start()

# EXECUTES THE BOT WITH THE SPECIFIED TOKEN. TOKEN HAS BEEN REMOVED AND USED JUST AS AN EXAMPLE.
bot.run(DISCORD_TOKEN)