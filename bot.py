#!/usr/bin/env python
"""Main bot file."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import discord

from discord.ext import commands
from sqlalchemy.ext.asyncio import AsyncSession

from bot_logger import get_logger, setup_logging
from cogs.utils.checks import check_admin
from cogs.utils.utils import get_prefix
from db import make_engine, make_session_factory
from settings import bot_settings

__version__ = "2.0.0-dev"
DOCS_URL = "placeholder"
setup_logging()
logger = get_logger(__name__)


class MyBot(commands.Bot):
    """Bot class."""

    def __init__(
        self, command_prefix, intents, version, database: str, test_guild=None
    ) -> None:
        """Initialise the bot."""
        super().__init__(command_prefix=command_prefix, intents=intents)
        self.initial_extensions = [
            "cogs.initial",
            "cogs.admin",
            "cogs.any_raids_filter",
            "cogs.fc_filter",
            "cogs.misc",
            "cogs.time_channel",
            "cogs.schedules",
        ]
        self.help_command.add_check(check_admin)
        self.my_version = version
        self.test_guild = test_guild
        self.docs = DOCS_URL
        self.database = database

    @asynccontextmanager
    async def db_session(self) -> AsyncGenerator[AsyncSession]:
        """Create a new database session context.

        Yields:
            An asynchronous database session.
        """
        async with self.session_factory() as session:
            async with session.begin():
                yield session

    async def setup_hook(self) -> None:
        """Load the initial extensions."""
        self.engine = make_engine(self.database)
        self.session_factory = make_session_factory(self.engine)

        for ext in self.initial_extensions:
            await self.load_extension(ext)

    async def close(self):
        await self.engine.dispose()
        await super().close()

    async def on_ready(self):
        """Print a message to the console when the bot is ready."""
        logger.info("Bot is ready!")


intents = discord.Intents.default()
intents.members = True
intents.message_content = True

logger.info("Starting bot...")
logger.info(f"Settings: {bot_settings.model_dump()}")

bot = MyBot(
    (get_prefix),
    intents,
    __version__,
    database=bot_settings.database,
    test_guild=bot_settings.test_guild,
)
bot.run(bot_settings.token.get_secret_value(), log_handler=None)
