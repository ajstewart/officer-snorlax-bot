"""Repositories for database access."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import FriendCodeChannel, Guild, GuildScheduleSettings, Schedule


class GuildRepository:
    """Repository for accessing guilds in the database."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialise the repository with a database session."""
        self.session = session

    async def get_or_create(self, guild_id: int) -> Guild:
        """Fetch or create a guild entry in the database.

        Args:
            guild_id: The id of the guild to fetch or create.

        Returns:
            The existing or newly created Guild object.
        """
        row = await self.session.get(Guild, {"id": guild_id})
        if row is None:
            row = Guild(id=guild_id)
            self.session.add(row)
        return row

    async def get(self, guild_id: int) -> Guild | None:
        """Fetch a guild entry from the database.

        Args:
            guild_id: ID of the guild to fetch.

        Returns:
            The guild db object or None if not found.
        """
        return await self.session.get(Guild, {"id": guild_id})

    async def check_exists(self, guild_id: int, check_active: bool = True) -> bool:
        """Check if a guild exists in the database.

        Args:
            guild_id: The ID of the guild to check.
            check_active: Whether to check if the guild is active.
                Defaults to True.

        Returns:
            True if the guild exists (and is active if check_active is True),
                False otherwise.
        """
        guild = await self.get(guild_id)
        if guild is None:
            return False
        if check_active and not guild.active:
            return False
        return True

    async def create_guild(self, guild: Guild) -> None:
        """Create a new guild in the database.

        Args:
            guild: The Guild object to create.
        """
        self.session.add(guild)

    async def get_all(self, active_only: bool = False) -> list[Guild]:
        """Fetch all guilds in the database.

        Args:
            active_only: If True, only active guilds are returned.

        Returns:
            A list of Guild objects.
        """
        stmt = select(Guild)
        if active_only:
            stmt = stmt.where(Guild.active)
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def get_log_channel(self, guild_id: int) -> int | None:
        """Fetch the log channel id for a guild.

        Args:
            guild_id: The id of the guild to fetch the log channel for.

        Returns:
            The log channel id if set, None otherwise.
        """
        guild = await self.get(guild_id)
        if guild is None:
            return None
        return guild.log_channel

    async def get_admin_channel(self, guild_id: int) -> int | None:
        """Fetch the admin channel id for a guild.

        Args:
            guild_id: The id of the guild to fetch the admin channel for.

        Returns:
            The admin channel id if set, None otherwise.
        """
        guild = await self.get(guild_id)
        if guild is None:
            return None
        return guild.admin_channel


class GuildScheduleSettingsRepository:
    """Repository for accessing guild schedule settings in the database."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialise the repository with a database session."""
        self.session = session

    async def get_or_create(self, guild_id: int) -> GuildScheduleSettings:
        """Fetch or create the Guild Schedule Settings object.

        Args:
            guild_id: The ID to fetch or created.

        Returns:
            The database object.
        """
        row = await self.session.get(GuildScheduleSettings, {"guild": guild_id})
        if row is None:
            row = GuildScheduleSettings(guild=guild_id)
            self.session.add(row)
        return row

    async def get(self, guild_id: int) -> GuildScheduleSettings | None:
        """Fetch the guild schduled settings matching the id.

        Args:
            guild_id: The ID of the guild to fetch.

        Returns:
            The database object of None if not found.
        """
        return await self.session.get(GuildScheduleSettings, {"guild": guild_id})

    async def check_exists(self, guild_id: int) -> bool:
        """Check if the settings exist for a guild.

        Args:
            guild_id: The guild to search for.

        Returns:
            True if exists, False otherwise.
        """
        settings = await self.get(guild_id)
        return settings is not None

    async def create(self, guild_schedule_settings: GuildScheduleSettings) -> None:
        """Create teh provided guild settings object in the database.

        Args:
            guild_schedule_settings: The guild settings object to create.
        """
        self.session.add(guild_schedule_settings)


class ScheduleRepository:
    """Repository for accessing channel schedules in the database."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialise the repository with a database session."""
        self.session = session

    async def get(self, schedule_id: int) -> Schedule | None:
        """Get the scheduled matching the provided id.

        Args:
            schedule_id: The id (rowid) of the schedule to fetch.

        Returns:
            The database scheduled object or None if not found.
        """
        return await self.session.get(Schedule, {"rowid": schedule_id})

    async def check_exists(self, schedule_id: int) -> bool:
        """Check if a schedule exists in the database.

        Args:
            schedule_id: The rowid of the schedule to check.

        Returns:
            True if the schedule exists, False otherwise.
        """
        return await self.get(schedule_id) is not None

    async def check_exists_with_times(
        self, channel_id: int, open_time: str, close_time: str
    ) -> bool:
        """Check if a schedule exists for a channel with the given open/close times.

        Args:
            channel_id: The channel id to check.
            open_time: The open time to check.
            close_time: The close time to check.

        Returns:
            True if a matching schedule exists, False otherwise.
        """
        stmt = select(Schedule).where(
            Schedule.channel == channel_id,
            Schedule.open == open_time,
            Schedule.close == close_time,
        )
        result = await self.session.scalars(stmt)
        return result.first() is not None

    async def get_all(
        self, guild_id: int | None = None, active: bool | None = None
    ) -> list[Schedule]:
        """Fetch schedules, optionally filtered by guild and/or active status.

        Args:
            guild_id: If provided, only schedules for this guild are returned.
            active: If provided, only schedules matching this active status
                are returned.

        Returns:
            A list of Schedule objects.
        """
        stmt = select(Schedule)
        if guild_id is not None:
            stmt = stmt.where(Schedule.guild == guild_id)
        if active is not None:
            stmt = stmt.where(Schedule.active == active)
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def get_by_channel(self, channel_id: int) -> list[Schedule]:
        """Fetch all schedules for the given channel id.

        Args:
            channel_id: The channel id to fetch schedules for.

        Returns:
            A list of Schedule objects.
        """
        stmt = select(Schedule).where(Schedule.channel == channel_id)
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def create(self, schedule: Schedule) -> None:
        """Create a new schedule in the database.

        Args:
            schedule: The Schedule object to create.
        """
        self.session.add(schedule)

    async def delete(self, schedule: Schedule | None) -> None:
        """Delete a schedule from the database.

        Args:
            schedule: The Schedule object to delete.
        """
        if schedule is not None:
            await self.session.delete(schedule)


class FriendCodeChannelRepository:
    """Repository for accessing allowed friend code channels in the database."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialise the repository with a database session."""
        self.session = session

    async def get(self, guild_id: int, channel_id: int) -> FriendCodeChannel | None:
        """Fetch the friend code channel object for the guild and channel.

        Args:
            guild_id: The id of the guild to fetch.
            channel_id: The id of the channel to fetch.

        Returns:
            The database object of None if not found.
        """
        return await self.session.get(
            FriendCodeChannel, {"guild": guild_id, "channel": channel_id}
        )

    async def check_exists(self, channel_id: int) -> bool:
        """Check if a channel is present in the friend code whitelist.

        Args:
            channel_id: The id of the channel to check.

        Returns:
            True if present, False otherwise.
        """
        stmt = select(FriendCodeChannel).where(FriendCodeChannel.channel == channel_id)
        result = await self.session.scalars(stmt)
        return result.first() is not None

    async def get_all(self, guild_id: int | None = None) -> list[FriendCodeChannel]:
        """Fetch allowed friend code channels, optionally filtered by guild.

        Args:
            guild_id: If provided, only channels for this guild are returned.

        Returns:
            A list of FriendCodeChannel objects.
        """
        stmt = select(FriendCodeChannel)
        if guild_id is not None:
            stmt = stmt.where(FriendCodeChannel.guild == guild_id)
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def get_or_create(
        self,
        guild_id: int,
        channel_id: int,
        channel_name: str,
        secret: bool = False,
    ) -> FriendCodeChannel:
        """Fetch or create an allowed friend code channel entry.

        Args:
            guild_id: The id of the guild the channel belongs to.
            channel_id: The id of the channel.
            channel_name: The name of the channel.
            secret: Whether the channel should be marked as secret.

        Returns:
            The existing or newly created FriendCodeChannel object.
        """
        row = await self.get(guild_id, channel_id)
        if row is None:
            row = FriendCodeChannel(
                guild=guild_id,
                channel=channel_id,
                channel_name=channel_name,
                secret=secret,
            )
            self.session.add(row)
        return row

    async def delete(self, friend_channel: FriendCodeChannel | None) -> None:
        """Remove a channel from the friend code whitelist.

        Args:
            friend_channel: The FriendCodeChannel object to remove.
        """
        if friend_channel is not None:
            await self.session.delete(friend_channel)
