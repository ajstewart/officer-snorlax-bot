from discord.ext import commands
from discord import TextChannel
from typing import Optional
import discord
from .utils.checks import (
    check_admin,
    check_admin_channel,
    check_time_format,
    check_for_friend_code,
    check_bot
)
from .utils.db import (
    load_friend_code_channels_db,
    add_allowed_friend_code_channel,
    drop_allowed_friend_code_channel
)
from .utils.utils import get_friend_channels_embed


class FriendCodeFilter(commands.Cog):
    """docstring for Initial"""
    def __init__(self, bot):
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
        self, ctx, channel: TextChannel, secret: Optional[str] = "False"
    ):
        """
        Docstring goes here.
        """
        guild = ctx.guild
        ok = add_allowed_friend_code_channel(guild, channel, secret)
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

    # EVENT LISTENER FOR WHEN THE BOT HAS SWITCHED FROM OFFLINE TO ONLINE.
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
    async def listFriendChannels(self, ctx):
        """
        Docstring goes here.
        """
        friend_db = load_friend_code_channels_db()
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
    async def removeFriendChannel(self, ctx, channel: TextChannel):
        """
        Docstring goes here.
        """
        guild = ctx.guild
        ok = drop_allowed_friend_code_channel(guild, channel)
        if ok:
            msg = (
                "{} removed from the friend code whitelist successfully.".format(
                    channel.mention
                )
            )
        else:
            msg = (
                "Error when removing {} from the friend code whitelist.".format(
                    channel.mention
                )
            )
        await ctx.channel.send(msg)

    @commands.Cog.listener()
    async def on_message(self, message):
        if check_bot(message):
            if not check_admin(message):
                content = message.content.strip().lower()
                if check_for_friend_code(content):
                    allowed_channels = load_friend_code_channels_db()
                    allowed_channels = allowed_channels.loc[
                        allowed_channels['guild'] == message.guild.id
                    ]
                    if allowed_channels.empty:
                        return
                    else:
                        if message.channel.id not in allowed_channels['channel'].values:
                            msg = (
                                "{}, that looks like a friend code so"
                                " Snorlax ate it!\n\n"
                                "Friend codes are allowed in:"
                            ).format(message.author.mention)
                            for c in allowed_channels[
                                allowed_channels['secret'] == False
                            ]['channel']:
                                msg += ' <#{}>'.format(c)
                            await message.channel.send(
                                msg,
                                delete_after=60
                            )
                            await message.delete()
