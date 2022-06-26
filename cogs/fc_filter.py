import discord
import logging

from discord import TextChannel, Message, Thread, app_commands, Interaction
from discord.abc import GuildChannel
from discord.ext import commands
from discord.utils import get
from typing import Optional

from sqlalchemy import desc

from .utils import checks as snorlax_checks
from .utils import db as snorlax_db
from .utils.embeds import get_friend_channels_embed
from .utils import log_msgs as snorlax_log


logger = logging.getLogger()


class FriendCodeFilter(commands.Cog):
    """Cog for the FriendCode Filter feature."""
    def __init__(self, bot: commands.bot) -> None:
        """
        Init method for the friend code filter.

        Args:
            bot: The discord.py bot representation.

        Returns:
            None.
        """
        super(FriendCodeFilter, self).__init__()
        self.bot = bot

    @app_commands.command(
        name='add-friend-code-channel',
        description="Add a channel to the friend code whitelist."
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.checks.has_permissions(administrator=True)
    async def addFriendChannel(
        self,
        interaction: Interaction,
        channel: TextChannel,
        secret: Optional[bool] = False
    ) -> None:
        """
        Method for the command to add a channel where friend codes are allowed.

        Args:
            interaction: The interaction that triggered the request.
            channel: The channel to be added to the friend code whitelist.
            secret: Whether the channel should be publicly stated to allow
                friend codes (defaults to False, i.e. will be shown on the list).

        Returns:
            None
        """
        guild = interaction.guild
        present = await snorlax_db.check_friend_code_channel(channel.id)

        if present:
            msg = (
                "Channel is already in the whitelist."
            )
        else:
            ok = await snorlax_db.add_allowed_friend_code_channel(guild, channel, secret)
            if ok:
                msg = (
                    "{} added to the friend code whitelist successfully.".format(
                        channel.mention
                    )
                )
            else:
                msg = (
                    "Error when adding the channel to the friend code whitelist."
                )

        await interaction.response.send_message(msg, ephemeral=True)

    @app_commands.command(
        name='list-friend-channels',
        description="Shows the list of channels where friend codes are allowed."
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.checks.has_permissions(administrator=True)
    async def listFriendChannels(self, interaction: Interaction) -> None:
        """
        Method to send an embed to the request channel listing all the
        friend code channels for that server.

        Args:
            interaction: The interaction that triggered the request.

        Returns:
            None
        """
        friend_db = await snorlax_db.load_friend_code_channels_db()
        if interaction.guild.id not in friend_db['guild'].values:
            await interaction.response.send_message(
                "No channels have been set, the filter is not active.",
                ephemeral=True
            )
        else:
            guild_friend_channels = friend_db.loc[
                friend_db['guild'] == interaction.guild.id
            ]
            embed = get_friend_channels_embed(guild_friend_channels)

            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name='remove-friend-code-channel',
        description="Remove a channel from the friend code whitelist."
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.checks.has_permissions(administrator=True)
    async def removeFriendChannel(
        self,
        interaction: Interaction,
        channel: TextChannel
    ) -> None:
        """
        Method for the command to remove a channel from the allowed friend
        codes list.

        Args:
            interaction: The interaction that triggered the request.
            channel: The channel to be removed.

        Returns:
            None
        """
        guild = interaction.guild
        present = await snorlax_db.check_friend_code_channel(channel.id)

        if not present:
            msg = (
                "Channel is not in the whitelist."
            )
        else:
            ok = await snorlax_db.drop_allowed_friend_code_channel(guild, channel)
            if ok:
                msg = (
                    f"{channel.mention} removed from the friend code"
                    " whitelist successfully."
                )
            else:
                msg = (
                    f"Error when removing {channel.mention} from the friend code"
                    " whitelist."
                )

        await interaction.response.send_message(msg, ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: Message) -> None:
        """
        Method run for each message received which checks for friend code
        content and takes the appropriate action.

        Args:
            message: The message object.

        Returns:
            None
        """
        if snorlax_checks.check_bot(message):
            if not snorlax_checks.check_admin(message):
                content = message.content.strip().lower()
                guild_db = await snorlax_db.load_guild_db()

                if snorlax_checks.check_for_friend_code(content):
                    allowed_channels = await snorlax_db.load_friend_code_channels_db()
                    allowed_channels = allowed_channels.loc[
                        allowed_channels['guild'] == message.guild.id
                    ]
                    if allowed_channels.empty:
                        return
                    else:
                        if isinstance(message.channel, Thread):
                            origin_channel_id = message.channel.parent_id
                        else:
                            origin_channel_id = message.channel.id
                        if origin_channel_id not in allowed_channels['channel'].values:
                            msg = (
                                "{}, that looks like a friend code so"
                                " Snorlax ate it!\n\n"
                                "Friend codes are allowed in:"
                            ).format(message.author.mention)
                            for c in allowed_channels[~allowed_channels['secret']]['channel']:
                                msg += ' <#{}>'.format(c)
                            if guild_db.loc[message.guild.id]['meowth_raid_category'] != -1:
                                msg += (
                                    ' or any raid channel generated using'
                                    ' the Pokenav bot.'
                                )
                            await message.channel.send(
                                msg,
                                delete_after=30
                            )
                            await message.delete()
                            log_channel_id = (
                                guild_db.loc[message.guild.id]['log_channel']
                            )
                            if log_channel_id != -1:
                                log_channel = get(
                                    message.guild.channels, id=int(
                                        log_channel_id
                                    )
                                )
                                embed = snorlax_log.filter_delete_log_embed(
                                    message, "Friend code filter."
                                )
                                await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: GuildChannel) -> None:
        """
        Checks on a channel creation whether the channel has been created
        under the category assigned as the meowth raid category.

        If the channel is created under the category then the channel is
        quietly added to the allowed list.

        Args:
            channel: The created channel object.

        Returns:
            None
        """
        guild_db = await snorlax_db.load_guild_db()
        guild_meowth_cat = (
            guild_db.loc[channel.guild.id]['meowth_raid_category']
        )
        if guild_meowth_cat == -1:
            pass
        elif channel.category is not None:
            if channel.category.id == guild_meowth_cat:
                # Add the newly created channel to allow fc
                ok = await snorlax_db.add_allowed_friend_code_channel(
                    channel.guild, channel, "True"
                )
                # TODO Add logging here.
            else:
                pass

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: GuildChannel) -> None:
        """
        Checks on a channel deletion whether the channel was under the category
        assigned as the meowth raid category.

        If the channel was under the category then the channel is removed from
        the allowed list.

        Args:
            channel: The deleted channel object.

        Returns:
            None
        """
        fc_channels = await snorlax_db.load_friend_code_channels_db()

        if channel.id in fc_channels['channel'].tolist():
            ok = await snorlax_db.drop_allowed_friend_code_channel(channel.guild, channel)
            if ok:
                log_channel = await snorlax_db.get_guild_log_channel(channel.guild.id)
                if log_channel != -1:
                    log_channel = get(channel.guild.channels, id=int(log_channel))
                    log_embed = snorlax_log.fc_channel_removed_log_embed(channel)
                    await log_channel.send(embed=log_embed)
                logger.info(f'Channel {channel.name} removed from {channel.guild.name} allowed friend code list.')


async def setup(bot: commands.bot) -> None:
    """The setup function to initiate the cog.

    Args:
        bot: The bot for which the cog is to be added.
    """
    if bot.test_guild is not None:
        await bot.add_cog(
            FriendCodeFilter(bot),
            guild=discord.Object(id=bot.test_guild)
        )
    else:
        await bot.add_cog(FriendCodeFilter(bot))
