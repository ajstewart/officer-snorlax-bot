"""The friend code filter cog for Snorlax."""
import logging

import discord

from discord import app_commands
from discord.abc import GuildChannel
from discord.ext import commands
from discord.utils import get

from .utils import checks as snorlax_checks
from .utils import db as snorlax_db
from .utils import log_msgs as snorlax_log
from .utils.autocompletes import friend_code_channel_autocomplete
from .utils.embeds import get_friend_channels_embed, get_message_embed

logger = logging.getLogger()


@app_commands.default_permissions(administrator=True)
class FriendCodeFilter(commands.GroupCog, name="friend-code-filter"):
    """Cog for the FriendCode Filter feature."""

    def __init__(self, bot: commands.bot) -> None:
        """Init method for the friend code filter.

        Args:
            bot: The discord.py bot representation.

        Returns:
            None.
        """
        super(FriendCodeFilter, self).__init__()
        self.bot = bot

    @app_commands.command(
        name="add-channel", description="Add a channel to the friend code whitelist."
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.check(snorlax_checks.check_admin_channel)
    @app_commands.checks.has_permissions(administrator=True)
    async def addFriendChannel(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        secret: bool = False,
    ) -> None:
        """Method for the command to add a channel where friend codes are allowed.

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
            msg = "Channel is already in the whitelist."
            embed = get_message_embed(msg, msg_type="warning")
            ephemeral = True
        else:
            ok = await snorlax_db.add_allowed_friend_code_channel(
                guild, channel, secret
            )
            if ok:
                msg = "{} added to the friend code whitelist successfully.".format(
                    channel.mention
                )
                embed = get_message_embed(msg, msg_type="success")
                ephemeral = False
            else:
                msg = "Error when adding the channel to the friend code whitelist."
                embed = get_message_embed(msg, msg_type="error")
                ephemeral = True

        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)

    @app_commands.command(
        name="list",
        description="Shows the list of channels where friend codes are allowed.",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.check(snorlax_checks.check_admin_channel)
    @app_commands.checks.has_permissions(administrator=True)
    async def listFriendChannels(self, interaction: discord.Interaction) -> None:
        """List all the friend code channels for the server.

        Returns as an embed.

        Args:
            interaction: The interaction that triggered the request.

        Returns:
            None
        """
        guild_id = interaction.guild_id
        friend_db = await snorlax_db.load_friend_code_channels_db(guild_id=guild_id)
        if friend_db.empty:
            embed = get_message_embed(
                "No channels have been set, the filter is not active.",
                msg_type="warning",
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            embed = get_friend_channels_embed(friend_db)

            await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="remove-channel",
        description="Remove a channel from the friend code whitelist.",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.check(snorlax_checks.check_admin_channel)
    @app_commands.checks.has_permissions(administrator=True)
    async def removeFriendChannel(
        self, interaction: discord.Interaction, channel: discord.TextChannel
    ) -> None:
        """Method to remove a channel from the allowed friend codes list.

        Args:
            interaction: The interaction that triggered the request.
            channel: The channel to be removed.

        Returns:
            None
        """
        guild = interaction.guild
        present = await snorlax_db.check_friend_code_channel(channel.id)

        if not present:
            msg = "Channel is not in the whitelist."
            embed = get_message_embed(msg, msg_type="warning")
            ephemeral = True
        else:
            ok = await snorlax_db.drop_allowed_friend_code_channel(guild.id, channel.id)
            if ok:
                msg = (
                    f"{channel.mention} removed from the friend code"
                    " whitelist successfully."
                )
                embed = get_message_embed(msg, msg_type="success")
                ephemeral = False
            else:
                msg = (
                    f"Error when removing {channel.mention} from the friend code"
                    " whitelist."
                )
                embed = get_message_embed(msg, msg_type="error")
                ephemeral = True

        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)

    @app_commands.command(
        name="toggle-secret",
        description=(
            "Toggle the secret value of a channel on the friend code whitelist."
        ),
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(snorlax_checks.interaction_check_bot)
    @app_commands.check(snorlax_checks.check_admin_channel)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.autocomplete(channel=friend_code_channel_autocomplete)
    async def friend_code_toggle_secret(
        self, interaction: discord.Interaction, channel: str
    ):
        """Toggle the secret value of a channel on the friend code whitelist.

        Args:
            interaction: The interaction that triggered the request.
            channel: The channel to be toggled.
        """
        try:
            channel, secret_val = channel.split("-")
            # A bit assuming here but it should be ok.
            secret_val = True if secret_val == "True" else False
            channel = int(channel)
            self.bot.get_channel(channel)
        except Exception as e:
            msg = (
                "That doesn't seem to be a valid channel. Please select a channel from"
                " the options provided."
            )
            embed = get_message_embed(msg, msg_type="warning")
            await interaction.response.send_message(embed=embed, ephemeral=True)

            logger.error(
                f"Failed toggle friend code channel secret in {interaction.guild.name}:"
                f" {e}."
            )
            return
        else:
            ok = await snorlax_db.set_friend_code_channel_secret(
                guild_id=interaction.guild_id, channel_id=channel, secret=secret_val
            )
            if ok:
                msg = "Friend code channel updated successfully."
                embed = get_message_embed(msg, msg_type="success")
                friend_db = await snorlax_db.load_friend_code_channels_db(
                    guild_id=interaction.guild_id
                )
                channels_embed = get_friend_channels_embed(friend_db)
                embeds = [embed, channels_embed]
            else:
                msg = "Error when attempting to update the friend code channel."
                embeds = [get_message_embed(msg, msg_type="error")]

        await interaction.response.send_message(embeds=embeds)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Method run for each message received.

        Checks for friend code content and takes the appropriate action.

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
                        allowed_channels["guild"] == message.guild.id
                    ]
                    if allowed_channels.empty:
                        return
                    else:
                        if isinstance(message.channel, discord.Thread):
                            origin_channel_id = message.channel.parent_id
                        else:
                            origin_channel_id = message.channel.id

                        if origin_channel_id not in allowed_channels["channel"].values:
                            msg = (
                                f"{message.author.mention}, that looks like a friend"
                                " code so Snorlax ate it!\n\nFriend codes are allowed"
                                " in:\n\n"
                            )

                            for c in allowed_channels[~allowed_channels["secret"]][
                                "channel"
                            ]:
                                msg += f":small_blue_diamond: <#{c}>\n"

                            if (
                                guild_db.loc[message.guild.id]["meowth_raid_category"]
                                != -1
                            ):
                                msg += (
                                    "\n or any raid channel generated using"
                                    " the Pokenav bot."
                                )

                            embed = get_message_embed(msg, msg_type="warning")
                            await message.channel.send(embed=embed, delete_after=15)

                            await message.delete()
                            log_channel_id = guild_db.loc[message.guild.id][
                                "log_channel"
                            ]

                            if log_channel_id != -1:
                                log_channel = get(
                                    message.guild.channels, id=int(log_channel_id)
                                )
                                embed = snorlax_log.filter_delete_log_embed(
                                    message, "Friend code filter."
                                )
                                await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: GuildChannel) -> None:
        """Performs checks on a channel creation.

        In this case it checks whether the channel has been created
        under the category assigned as the meowth raid category.

        If the channel is created under the category then the channel is
        quietly added to the allowed list.

        Args:
            channel: The created channel object.

        Returns:
            None
        """
        guild_db = await snorlax_db.load_guild_db()
        guild_meowth_cat = guild_db.loc[channel.guild.id]["meowth_raid_category"]
        if guild_meowth_cat == -1:
            pass
        elif channel.category is not None:
            if channel.category.id == guild_meowth_cat:
                # Add the newly created channel to allow fc
                await snorlax_db.add_allowed_friend_code_channel(
                    channel.guild, channel, "True"
                )
                # TODO Add logging here.
            else:
                pass

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: GuildChannel) -> None:
        """Runs on a channel deletion.

        Checks whether the channel was under the category assigned
        as the meowth raid category.

        If the channel was under the category then the channel is removed from
        the allowed list.

        Args:
            channel: The deleted channel object.

        Returns:
            None
        """
        fc_channels = await snorlax_db.load_friend_code_channels_db()

        if channel.id in fc_channels["channel"].tolist():
            ok = await snorlax_db.drop_allowed_friend_code_channel(
                channel.guild.id, channel.id
            )
            if ok:
                log_channel = await snorlax_db.get_guild_log_channel(channel.guild.id)
                if log_channel != -1:
                    log_channel = get(channel.guild.channels, id=int(log_channel))
                    log_embed = snorlax_log.fc_channel_removed_log_embed(channel)
                    await log_channel.send(embed=log_embed)
                logger.info(
                    f"Channel {channel.name} removed from {channel.guild.name} allowed"
                    " friend code list."
                )


async def setup(bot: commands.bot) -> None:
    """The setup function to initiate the cog.

    Args:
        bot: The bot for which the cog is to be added.
    """
    if bot.test_guild is not None:
        await bot.add_cog(
            FriendCodeFilter(bot), guild=discord.Object(id=bot.test_guild)
        )
    else:
        await bot.add_cog(FriendCodeFilter(bot))
