import discord

from discord import Message
from discord.ext import commands
from discord.utils import get

from .utils import checks as snorlax_checks
from .utils import db as snorlax_db
from .utils.log_msgs import filter_delete_log_embed
from .utils.utils import strip_mentions


class AnyRaidsFilter(commands.Cog):
    """Cog for the Any raids filter feature."""
    def __init__(self, bot: commands.bot) -> None:
        """
        Init method for the any raids filter.

        Args:
            bot: The discord.py bot representation.

        Returns:
            None.
        """
        super(AnyRaidsFilter, self).__init__()
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: Message) -> None:
        """
        Method run for each message received which checks for any raid
        content and takes the appropriate action.

        Args:
            message: The message object.

        Returns:
            None
        """
        if snorlax_checks.check_bot(message):
            if not snorlax_checks.check_admin(message):
                if await snorlax_db.get_guild_any_raids_active(message.guild.id):
                    content = strip_mentions(message.content.strip().lower())

                    if snorlax_checks.check_for_any_raids(content):
                        msg = (
                            "{}, please don't spam this channel with"
                            " 'any raids?'. Check to see if there is a raid"
                            " being hosted or post your raid if you'd like to"
                            " host one yourself. See the relevant rules"
                            " channel for rules and instructions."
                        ).format(message.author.mention)
                        await message.channel.send(
                            msg,
                            delete_after=30
                        )
                        await message.delete()
                        log_channel_id = await snorlax_db.get_guild_log_channel(message.guild.id)

                        if log_channel_id != -1:

                            log_channel = get(
                                message.guild.channels, id=int(log_channel_id)
                            )
                            embed = filter_delete_log_embed(
                                message, "Any raids filter."
                            )
                            await log_channel.send(embed=embed)
                        return


async def setup(bot: commands.bot) -> None:
    """The setup function to initiate the cog.

    Args:
        bot: The bot for which the cog is to be added.
    """
    if bot.test_guild is not None:
        await bot.add_cog(
            AnyRaidsFilter(bot),
            guild=discord.Object(id=bot.test_guild)
        )
    else:
        await bot.add_cog(AnyRaidsFilter(bot))
