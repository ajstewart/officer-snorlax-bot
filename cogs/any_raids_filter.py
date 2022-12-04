import discord

from discord import app_commands, Message
from discord.ext import commands
from discord.utils import get

from .utils import checks as snorlax_checks
from .utils import db as snorlax_db
from .utils.embeds import get_message_embed
from .utils.log_msgs import filter_delete_log_embed
from .utils.utils import strip_mentions


@app_commands.default_permissions(administrator=True)
class AnyRaidsFilter(commands.GroupCog, name="any-raids-filter"):
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

    @app_commands.command(
        name='activate',
        description=(
            "Turn on the 'any raids' filter. Filters messages containing 'any raids?'."
        ),
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.check(snorlax_checks.check_admin_channel)
    @app_commands.checks.has_permissions(administrator=True)
    async def activateAnyRaidsFilter(self, interaction: discord.Interaction) -> None:
        """
        Method to activate the any raids filter on the guild.

        Args:
            interaction: The interaction triggering the request.

        Returns:
            None
        """
        any_filter = await snorlax_db.get_guild_any_raids_active(interaction.guild.id)
        if any_filter:
            msg = "The 'any raids' filter is already activated."
            embed = get_message_embed(msg, msg_type='warning')
        else:
            ok = await snorlax_db.toggle_any_raids_filter(interaction.guild, True)
            if ok:
                msg = "'Any raids' filter activated."
                embed = get_message_embed(msg, msg_type='success')
            else:
                msg = "Error when attempting to activate the 'Any raids' filter"
                embed = get_message_embed(msg, msg_type='error')

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="deactivate",
        description="Turns off the 'any raids' filter."
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.check(snorlax_checks.check_admin_channel)
    @app_commands.checks.has_permissions(administrator=True)
    async def deactivateAnyRaidsFilter(self, interaction: discord.Interaction):
        """
        Command to deactivate the any raids filter.

        Args:
            interaction: The interaction that triggered the request.

        Returns:
            None
        """
        any_filter = await snorlax_db.get_guild_any_raids_active(interaction.guild.id)
        if not any_filter:
            msg = "The 'any raids' filter is already deactivated."
            embed = get_message_embed(msg, msg_type='warning')
        else:
            ok = await snorlax_db.toggle_any_raids_filter(interaction.guild, False)
            if ok:
                msg = "'Any raids' filter deactivated."
                embed = get_message_embed(msg, msg_type='success')
            else:
                msg = "Error when attempting to deactivate the 'Any raids' filter."
                embed = get_message_embed(msg, msg_type='error')

        await interaction.response.send_message(embed=embed)

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

                        embed = get_message_embed(msg, msg_type='warning')

                        await message.channel.send(
                            embed=embed,
                            delete_after=20
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
