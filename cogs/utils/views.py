"""Contains the views used throughout the bot
"""
import discord
from typing import List


class ScheduleDropdown(discord.ui.Select):
    def __init__(self, options: List[discord.SelectOption], context: str):

        self.context_verbs = {
            'activate': 'activated',
            'deactivate': 'deactivated',
            'update': 'updated',
            'list': 'listed'
        }
        if context not in self.context_verbs:
            raise ValueError(f'context {context} is not valid!')

        self.context = context

        if context in ['activate', 'deactivate']:
            max_values = len(options)

        # The placeholder is what will be shown when no option is chosen
        # The min and max values indicate we can only pick one of the three options
        # The options parameter defines the dropdown options. We defined this above
        super().__init__(
            placeholder='Select the schedule(s)...',
            min_values=1,
            max_values=max_values,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        # Use the interaction object to send a response message containing
        # the user's favourite colour or choice. The self object refers to the
        # Select object, and the values attribute gets a list of the user's
        # selected options. We only want the first one.
        self.view.values = self.values
        msg = f"The {len(self.values)} selected schedule(s) will be {self.context_verbs[self.context]}."
        await interaction.response.send_message(msg, ephemeral=True)
        await self.view.disable_children()
        self.view.stop()


class ScheduleDropdownView(discord.ui.View):
    def __init__(
        self,
        user: discord.User,
        options: List[discord.SelectOption],
        context: str,
        timeout: int = 60
    ):
        super().__init__(timeout=timeout)
        self.values = None
        self.user = user

        self.add_item(ScheduleDropdown(options=options, context=context))

    async def disable_children(self) -> None:
        """Loops through the view children and disables the components.

        The response must have been attached to the view!

        Args:
            timeout_label: If True, the label of button components will be replaced with 'Timeout!'.
        """
        for child in self.children:
            child.disabled = True

        await self.response.edit(view=self)

    async def on_timeout(self) -> None:
        """Disable the buttons of the view in the event of a timeout.
        """
        await self.disable_children()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """The interaction check for the view.

        Checks whether the interaction user is the initial command user. A response is sent if this is not the case.

        Args:
            interaction: The interaction instance.

        Returns:
            Whether the check has passed (True) or not (False).
        """
        check_pass = self.user.id == interaction.user.id

        if not check_pass:
            await interaction.response.send_message("You do not have permission to do that!", ephemeral=True)

        return check_pass


# Define a simple View that gives us a confirmation menu
class RemoveAllConfirm(discord.ui.View):
    """This View is used for the confirmation of the removeAllSchedules command.

    Users will confirm or cancel the command. Only responds to the original author.
    Note that the initial response message should be attached to the class when used!

    Attributes:
        value (Optional[bool]): Whether the interaction is complete (True) or not (False).
            None indicates a timeout.
        user (Discord.User): The original author of the command who the view will only respond to.
    """
    def __init__(self, user: discord.User, timeout: int = 60) -> None:
        """Init function of the view.

        Args:
            user: The original author of the command who the view will only respond to.
            timeout: How long, in seconds, the view will remain active for.
        """
        super().__init__(timeout=timeout)
        self.value = None
        self.user = user

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(label='Confirm', style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        """The confirm button of the view.

        The value attribute is set to True when used and the view is stopped.

        Args:
            interaction: The interaction instance.
            button: The button instance.
        """
        await interaction.response.send_message('Confirmed!', ephemeral=True)
        self.value = True
        await self.disable_children()
        self.stop()

    # This one is similar to the confirmation button except sets the inner value to `False`
    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.grey)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        """The cancel button of the view.

        The value attribute is set to False when used and the view is stopped.

        Args:
            interaction: The interaction instance.
            button: The button instance.
        """
        await interaction.response.send_message('Cancelled!', ephemeral=True)
        self.value = False
        await self.disable_children()
        self.stop()

    async def disable_children(self, timeout_label: bool = False) -> None:
        """Loops through the view children and disables the components.

        The response must have been attached to the view!

        Args:
            timeout_label: If True, the label of button components will be replaced with 'Timeout!'.
        """
        for child in self.children:
            child.disabled = True
            if timeout_label:
                child.label = "Timeout!"

        await self.response.edit(view=self)

    async def on_timeout(self) -> None:
        """Disable the buttons of the view in the event of a timeout.
        """
        await self.disable_children(timeout_label=True)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """The interaction check for the view.

        Checks whether the interaction user is the initial command user. A response is sent if this is not the case.

        Args:
            interaction: The interaction instance.

        Returns:
            Whether the check has passed (True) or not (False).
        """
        check_pass = self.user.id == interaction.user.id

        if not check_pass:
            await interaction.response.send_message("You do not have permission to do that!", ephemeral=True)

        return check_pass
