"""SQLAlchemy models that match the current database schema."""

import os

from typing import Self

from discord import Guild as DiscordGuild
from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

DEFAULT_TZ = os.environ.get("DEFAULT_TZ", "UTC")
DEFAULT_PREFIX = os.environ.get("DEFAULT_PREFIX", "!")
DEFAULT_OPEN_MESSAGE = os.getenv("DEFAULT_OPEN_MESSAGE")
DEFAULT_CLOSE_MESSAGE = os.getenv("DEFAULT_CLOSE_MESSAGE")
DEFAULT_WARNING_TIME = os.getenv("DEFAULT_WARNING_TIME")
DEFAULT_INACTIVE_TIME = os.getenv("DEFAULT_INACTIVE_TIME")
DEFAULT_DELAY_TIME = os.getenv("DEFAULT_DELAY_TIME")
GUILD_TABLE = "guilds"


class Base(DeclarativeBase):
    """Base class for all ORM models."""


class Guild(Base):
    """Discord guild configuration stored in the guilds table."""

    __tablename__ = GUILD_TABLE

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tz: Mapped[str] = mapped_column(String(40), nullable=False)
    admin_channel: Mapped[int] = mapped_column(Integer, nullable=False)
    meowth_raid_category: Mapped[int] = mapped_column(Integer, nullable=False)
    any_raids_filter: Mapped[bool] = mapped_column(Boolean, nullable=False)
    log_channel: Mapped[int] = mapped_column(Integer, nullable=False)
    time_channel: Mapped[int] = mapped_column(Integer, nullable=False)
    join_name_filter: Mapped[bool] = mapped_column(Boolean, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    prefix: Mapped[str] = mapped_column(String(3), nullable=False)

    @classmethod
    def create_from_discord_guild(cls, guild: DiscordGuild) -> Self:
        """Create a new Guild instance from a Discord guild object.

        Args:
            guild: The Discord guild object.

        Returns:
            Guild: A new Guild instance.
        """
        return cls(
            id=guild.id,
            tz=DEFAULT_TZ,
            admin_channel=-1,
            meowth_raid_category=-1,
            any_raids_filter=False,
            log_channel=-1,
            time_channel=-1,
            join_name_filter=False,
            active=True,
            prefix=DEFAULT_PREFIX,
        )


class Schedule(Base):
    """Channel schedule entries stored in the schedules table."""

    __tablename__ = "schedules"

    rowid: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild: Mapped[int] = mapped_column(ForeignKey(f"{GUILD_TABLE}.id"), nullable=False)
    channel: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[int] = mapped_column(Integer, nullable=False)
    channel_name: Mapped[str] = mapped_column(String(40), nullable=False)
    role_name: Mapped[str] = mapped_column(String(30), nullable=False)
    open: Mapped[str] = mapped_column(String(5), nullable=False)
    close: Mapped[str] = mapped_column(String(5), nullable=False)
    open_message: Mapped[str] = mapped_column(String(255), nullable=False)
    close_message: Mapped[str] = mapped_column(String(255), nullable=False)
    warning: Mapped[bool] = mapped_column(Boolean, nullable=False)
    dynamic: Mapped[bool] = mapped_column(Boolean, nullable=False)
    dynamic_close: Mapped[str] = mapped_column(String(5), nullable=False)
    max_num_delays: Mapped[int] = mapped_column(Integer, nullable=False)
    current_delay_num: Mapped[int] = mapped_column(Integer, nullable=False)
    silent: Mapped[bool] = mapped_column(Boolean, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    last_open_message: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_close_message: Mapped[int | None] = mapped_column(Integer, nullable=True)

    @classmethod
    def create(
        cls,
        guild_id: int,
        channel_id: int,
        channel_name: str,
        role_id: int,
        role_name: str,
        open_time: str,
        close_time: str,
        open_message: str | None = None,
        close_message: str | None = None,
        warning: bool = False,
        dynamic: bool = False,
        max_num_delays: int = 1,
        silent: bool = False,
    ) -> Self:
        """Create a new Schedule instance with the standard defaults applied.

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
            Schedule: A new Schedule instance.
        """
        return cls(
            guild=guild_id,
            channel=channel_id,
            channel_name=channel_name,
            role=role_id,
            role_name=role_name,
            open=open_time,
            close=close_time,
            open_message=open_message if open_message is not None else "None",
            close_message=close_message if close_message is not None else "None",
            warning=warning,
            dynamic=dynamic,
            dynamic_close="99:99",
            max_num_delays=max_num_delays,
            current_delay_num=0,
            silent=silent,
            active=True,
            last_open_message=None,
            last_close_message=None,
        )


class FriendCodeChannel(Base):
    """Allowed friend code channels stored in the fc_channels table."""

    __tablename__ = "fc_channels"

    guild: Mapped[int] = mapped_column(
        ForeignKey(f"{GUILD_TABLE}.id"), primary_key=True
    )
    channel: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel_name: Mapped[str] = mapped_column(String(40), nullable=False)
    secret: Mapped[bool] = mapped_column(Boolean, nullable=False)


class GuildScheduleSettings(Base):
    """Per-guild schedule message and timing defaults."""

    __tablename__ = "guild_schedule_settings"

    guild: Mapped[int] = mapped_column(ForeignKey("guilds.id"), primary_key=True)
    base_open_message: Mapped[str] = mapped_column(String(60), nullable=False)
    base_close_message: Mapped[str] = mapped_column(String(60), nullable=False)
    warning_time: Mapped[int] = mapped_column(Integer, nullable=False)
    inactive_time: Mapped[int] = mapped_column(Integer, nullable=False)
    delay_time: Mapped[int] = mapped_column(Integer, nullable=False)

    @classmethod
    def create_default(cls, guild_id: int) -> Self:
        """Create a new GuildScheduleSettings instance with default values.

        Args:
            guild_id: The ID of the guild.

        Returns:
            GuildScheduleSettings: A new GuildScheduleSettings instance.
        """
        return cls(
            guild=guild_id,
            base_open_message=DEFAULT_OPEN_MESSAGE or "The channel is now open!",
            base_close_message=DEFAULT_CLOSE_MESSAGE or "The channel is now closed!",
            warning_time=int(DEFAULT_WARNING_TIME or 5),
            inactive_time=int(DEFAULT_INACTIVE_TIME or 15),
            delay_time=int(DEFAULT_DELAY_TIME or 5),
        )
