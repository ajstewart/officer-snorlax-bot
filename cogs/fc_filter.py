import discord

from discord import TextChannel, Message, Thread
from discord.abc import GuildChannel
from discord.ext import commands
from discord.utils import get
from typing import Optional

from .utils.checks import (
    check_admin,
    check_admin_channel,
    check_for_friend_code,
    check_bot,
    check_for_any_raids
)
from .utils.db import (
    load_guild_db,
    load_friend_code_channels_db,
    add_allowed_friend_code_channel,
    drop_allowed_friend_code_channel
)
from .utils.log_msgs import filter_delete_log_embed
from .utils.utils import get_friend_channels_embed


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

    @commands.command(
        help=(
            "Adds a channel to the whitelist of where friend codes are"
            " allowed to be posted. The secret flag means that this channel"
            " won't be listed to users when their message is deleted."
        ),
        brief="Add a channel to the friend code whitelist."
    )
    @commands.check(check_bot)
    @commands.check(check_admin)
    @commands.check(check_admin_channel)
    async def addFriendChannel(
        self,
        ctx: commands.context,
        channel: TextChannel,
        secret: Optional[str] = "False"
    ) -> None:
        """
        Method for the command to add a channel where friend codes are allowed.

        Args:
            ctx: The command context containing the message content and other
                metadata.
            channel: The channel to be added.
            secret: Whether the channel should be publicly stated to allow
                friend codes.

        Returns:
            None
        """
        guild = ctx.guild
        ok = await add_allowed_friend_code_channel(guild, channel, secret)
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
        await ctx.channel.send(msg)

    @commands.check(check_bot)
    @commands.check(check_admin_channel)
    @commands.check(check_admin)
    @commands.command(
        help=(
            "Will list all the channels where"
            " friend codes are allowed to be posted."
        ),
        brief="Show a list of active schedules."
    )
    async def listFriendChannels(self, ctx: commands.context) -> None:
        """
        Method to send an embed to the request channel listing all the
        friend code channels for that server.

        Args:
            ctx: The command context containing the message content and other
                metadata.

        Returns:
            None
        """
        friend_db = await load_friend_code_channels_db()
        if ctx.guild.id not in friend_db['guild'].values:
            await ctx.channel.send(
                "No channels have been set, the filter is not active."
            )
        else:
            guild_friend_channels = friend_db.loc[
                friend_db['guild'] == ctx.guild.id
            ]
            embed = get_friend_channels_embed(ctx, guild_friend_channels)

            await ctx.channel.send(embed=embed)

    @commands.command(
        help=(
            "Removes a channel from the friend code whitelist."
        ),
        brief="Remove a channel from the friend code whitelist."
    )
    @commands.check(check_bot)
    @commands.check(check_admin)
    @commands.check(check_admin_channel)
    async def removeFriendChannel(
        self,
        ctx: commands.context,
        channel: TextChannel
    ) -> None:
        """
        Method for the command to remove a channel from the allowed friend
        codes list.

        Args:
            ctx: The command context containing the message content and other
                metadata.
            channel: The channel to be added.

        Returns:
            None
        """
        guild = ctx.guild
        ok = await drop_allowed_friend_code_channel(guild, channel)
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
        await ctx.channel.send(msg)

    @commands.Cog.listener()
    async def on_message(self, message: Message) -> None:
        """
        Method run for each message received which checks for friend code
        content and takes the appropriate action.

        This is also where the any raids filter is performed.

        Args:
            message: The message object.

        Returns:
            None
        """
        if check_bot(message):
            if not check_admin(message):
                content = message.content.strip().lower()
                guild_db = await load_guild_db()
                if guild_db.loc[message.guild.id]['any_raids_filter']:
                    if check_for_any_raids(content):
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
                        log_channel_id = (
                            guild_db.loc[message.guild.id]['log_channel']
                        )
                        if log_channel_id != -1:
                            tz = guild_db.loc[message.guild.id]['tz']
                            log_channel = get(
                                message.guild.channels, id=int(log_channel_id)
                            )
                            embed = filter_delete_log_embed(
                                message, tz, "Any raids filter."
                            )
                            await log_channel.send(embed=embed)
                        return

                if check_for_friend_code(content):
                    allowed_channels = await load_friend_code_channels_db()
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
                            for c in allowed_channels[
                                ~allowed_channels['secret']
                            ]['channel']:
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
                                tz = guild_db.loc[message.guild.id]['tz']
                                log_channel = get(
                                    message.guild.channels, id=int(
                                        log_channel_id
                                    )
                                )
                                embed = filter_delete_log_embed(
                                    message, tz, "Friend code filter."
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
        guild_db = await load_guild_db()
        guild_meowth_cat = (
            guild_db.loc[channel.guild.id]['meowth_raid_category']
        )
        if guild_meowth_cat == -1:
            pass
        elif channel.category is not None:
            if channel.category.id == guild_meowth_cat:
                # Add the newly created channel to allow fc
                ok = await add_allowed_friend_code_channel(
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

        TODO: Need to support channel deletions of other channels otherwise
              the database will get messy.

        Args:
            channel: The created channel object.

        Returns:
            None
        """
        guild_db = await load_guild_db()
        guild_meowth_cat = (
            guild_db.loc[channel.guild.id]['meowth_raid_category']
        )
        if guild_meowth_cat == -1:
            pass
        elif channel.category is not None:
            if channel.category.id == guild_meowth_cat:
                # Add the newly created channel to allow fc
                ok = await drop_allowed_friend_code_channel(
                    channel.guild, channel
                )
                # TODO Add logging here.
            else:
                pass


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
