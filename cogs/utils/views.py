"""Contains the views used throughout the bot
"""
import discord


class ScheduleDropdown(discord.ui.Select):
    """A schedule dropdown class that displays the passed in options.

    Sets the context relative to the command type.

    Attributes:
        context: The context of the command, either 'activate', 'deactivate',
            'update', 'list' or 'delete'.
    """
    def __init__(self, options: list[discord.SelectOption], context: str) -> None:
        """A schedule dropdown class that displays the passed in options.

        Sets the context relative to the command type.

        Args:
            options: The list of pre-prepared discord SelectOptions containing
                the schedules.
            context: The context of the command, either 'activate', 'deactivate',
                'update', 'list' or 'delete'.

        Raises:
            ValueError: If the context is not a valid choice.
        """
        self.context_verbs = {
            'activate': 'activated',
            'deactivate': 'deactivated',
            'update': 'updated',
            'list': 'listed',
            'delete': 'deleted'
        }

        if context not in self.context_verbs:
            raise ValueError(f'context {context} is not valid!')

        self.context = context

        if context in ['activate', 'deactivate', 'delete']:
            max_values = len(options)

        super().__init__(
            placeholder='Select the schedule(s)...',
            min_values=1,
            max_values=max_values,
            options=options
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        """The callback function upon interaction.

        The selected values are passed to the parent view and a confirmation
        message is sent through the interaction. The children (i.e. the selector)
        are then disabled and the view stopped.
        """
        # Use the interaction object to send a response message containing
        # the user's selected schedules.
        self.view.values = self.values
        msg = f"The {len(self.values)} selected schedule(s) will be {self.context_verbs[self.context]}."
        await interaction.response.send_message(msg)
        await self.view.disable_children()
        self.view.stop()


class ScheduleDropdownView(discord.ui.View):
    """The view for the schedule dropdown options.

    Creates the view and attaches the ScheduleDropdown object
    from the provided options.

    Attributes:
        values: The final view values.
        user: The interaction user.
    """
    def __init__(
        self,
        user: discord.User,
        options: list[discord.SelectOption],
        context: str,
        timeout: int = 60
    ) -> None:
        """The initialisation function of the view.

        Args:
            user: The discord user who triggered the interaction for which the view
                will be sent - and only they can reply.
            options: The schedule options to be passed to the Schedule dropdown.
            context: The context of the schedule command either 'activate', 'deactivate',
                'update', 'list' or 'delete'.
            timeout: The value, in seconds, to set as the timeout.
        """
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
class Confirm(discord.ui.View):
    """This View is used for supplying a confirmation choice.

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
        await interaction.response.send_message('Confirmed!')
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

    async def disable_children(self) -> None:
        """Loops through the view children and disables the components.

        The response must have been attached to the view!
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
