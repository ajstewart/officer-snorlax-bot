# Officer Snorlax Discord Bot
A simple bot for Discord that can close and open channels on a defined schedule. 

Also includes:

  * Display a time channel for the server.
  * Pokemon Go friend code filter option.
  * 'any raids? filter option.

**Disclaimer** This is the first Discord bot I have attempted and not spent too much time on it. 
It seems to do the job but undoubtedly could be done much better!
It is for this reason that I am not yet generally using an invite link for a hosted instance, and rather made the code public for people to self-host if they wish.
But if you are interested in using a hosted instance please find me on the Sydney Pokemon Go server.

This version supports `discord.py` v2.0 including features such as slash commands.

## Requirements

The project uses poetry to manage the dependencies and they can be installed with:
```
poetry install
```

## Self-Hosting Setup

1. Create a Discord bot, take note of the token and invite the bot to your server (see this guide https://realpython.com/how-to-make-a-discord-bot-python/).

2. Clone this repo and `cd` into it.

3. Checkout the `main` branch.

    ```
    git checkout main
    ```

4. Copy the `alembic.ini.template` file to `alembic.ini` and edit line `58` by replacing "ENTER DATABASE HERE!" with your intended database name, e.g.

    ```
    sqlalchemy.url = sqlite:///database.db
    ```

    and then run:

    ```
    alembic upgrade head
    ```

    which will create the database.

5. Copy the `.env_template` to `.env` and proceed to enter your settings.

6. Run the bot with:
    ```
    python bot.py
    ```

## Permissions Required

For all features to work the following permissions are needed:

  * View channels
  * Manage channels
  * Manage roles
  * Ban members
  * Send messages
  * Add reactions
  * Manage messages
  * Read message history

If channel permissions are present which override the server permissions makes sure to add the bot role to the relevant channels.
The scheduling works by toggling the `@everyone` role on the channel to `deny` for closure and `neutral` for open.
So make sure the channel permissions for the bot and users are set such that this toggle will be effective.
For channels that are part of a schedule it's important to have the following permissions:

  * View channel
  * Manage channel
  * Manage permissions
  * Send messages
  * Add reactions
  * Manage messages
  * Read message history

### Permissions Code

Below is a permissions code that can be used when creating a url invite:

```permissions=1393986497620```

## Bot Setup

**All the commands below are done on the Discord server.**

Once added to your server the bot will automatically create a `snorlax-admin` channel that only admins can see with the following welcome message:

![Welcome message](/screenshots/welcome.png)

All admin commands should be issued in this channel.

The settings summary can be viewed at any time by using the `/admin show-settings` command.

![Show settings](/screenshots/show-settings.png)

### Log Channel

Snorlax will notify of automated events, such as channel opening, closing and message filters, in a designated log channel. 
To enable logging firstly create or identify the text channel where you wish logs to be written to. 
Then in the admin channel use the command:

```
/admin set-log-channel
```

![set-log-channel](/screenshots/set-log-channel.png)
![log channel success](/screenshots/log-channel-success.png)

Log messages will now be sent to your chosen channel.

![Log Example](/screenshots/log_example.png)

### Guild Timezone

You can set the timezone for your Guild (if different from the default option set in the `.env` file) using the command:

```
/admin set-timezone
```

![Set timezone](/screenshots/set-timezone.png)

The command contains a list of standard timezones (https://en.wikipedia.org/wiki/List_of_tz_database_time_zones) where you can type the name of your nearest major city to find the correct timezone.

In the example above `London` is searched for, obtaining the `Europe/London` timezone.

![Timezone success](/screenshots/set-timezone-success.png)

## Local Time Display Channel

The local time and timezone of the server can be displayed to server members by using a voice channel. 
The name of the voice channel is updated periodically to represent the time.
**Note**: Because of Discord rate limiting the amount of times a bot can change a channel name, the time is only updated every 10 mins.
On first launch the bot will wait for a even 10 minute time to start displaying the time. E.g. if you launch the bot at 1:36 the first update will be done at 1:40.

### Create a Time Channel

A time channel can be created by using the command:

```
/create-time-channel
```

The command has one optional argument of what category to place the channel under.

The voice channel name will now be updated every 10 minutes and will look like the example below.

![create-time-channel](/screenshots/create-time-channel.png)
![setTimeChannel](/screenshots/time-channel-success.png)

Note that Snorlax should take care of the permissions of the voice channel.

When the channel is updated it will appear as so:

![Time Example](/screenshots/time_display_example.png)

## Schedules

### Creating a Schedule

To add an open and close schedule you can use the command:

```
/schedules create-schedule
```

![create schedule](/screenshots/create-schedule.png)
![create schedule success](/screenshots/create-schedule-success.png)

The Discord slash command interface will make sure the arguments are entered as required though note that **the time entries must be in the format of `HH:MM` in 24-hour format**

See the explanations further on in this README for information on `dynamic`, `max_num_delays` and `silent` options.

Note that by default the selected channel is the channel where the command is being issued.

A summary of all created schedules can be viewed by using the command:

```
/schedules view-schedules
```

### How does it work?

It works by toggling the `@everyone` role on the channel to `deny` for closure and `neutral` for open. 
The bot will check if the channel is already closed or opening before applying the change, so it won't attempt to close a channel already closed for example.

When creating the schedule Snorlax will check that it has the correct permissions on the respective channel to implement the schedule.

![CloseAndOpen](/screenshots/CloseAndOpen.png)

**Note**: If there is no activity in the channel since the last opening then the bot will self-tidy the opening and close messages in the channel to avoid clutter.

### Roles Not Affected By Schedule

When creating the schedule, Snorlax will check if any roles have an explicit send message permission. This would mean that the schedule will have no effect for these roles. These will be communicated via a warning message upon creation like that shown below.

![ScheduleRolesWarning](/screenshots/SchedulesRolesWarning.png)

### Warning Option

If selected, then if the channel has seen activity in the past `X` minutes, where `X` is determined by the global schedules setting `Inactive Time`, then `Y` minutes before the scheduled closure, where `Y` is determined by the global schedules setting `Warning Time`, the bot will post a warning that the channel is scheduled to close soon.

See the [Schedule Global Settings](#schedule-global-settings) section for details on how to set the inactive and warning time settings.

![warning-example](/screenshots/warning-example.png)

### Dynamic Closure Option

If the channel has been active for `Inactive Time` minutes before the closure then the closure is pushed back by the global schedules setting `Delay Time` minutes. 
This happens silently from the users point of view.
There is a `max_num_delays` setting available when adding the schedule to force closure after a chosen amount of delays (defaults to 1).

See the [Schedule Global Settings](#schedule-global-settings) section for details on how to set the inactive and delay time settings.

### Silent Mode

When set to `True`, silent mode means that Snorlax will open and close the channel without posting the accompanying messages.

### Current Behaviour Warning

At the moment it's possible to add multiple schedules to one channel - BUT - these won't have knowledge of each other. So keep that in mind if you do this.

### Updating a Schedule

A schedule can be updated by using the command:

```
/schedules update-schedule
```

A selection menu will appear for the first option to select the schedule to update.

![update schedule](/screenshots/update-schedule.png)

Then all other options can be entered like that done in the command creation.

![update schedule options](/screenshots/update-schedule-options.png)

![update schedule success](/screenshots/update-schedule-success.png)

### Deactivating & Activating a Schedule

Schedules have an 'active' status which can be on or off.
Upon creation a schedule is activated by default.
When set to off a schedule will not be processed when the time comes.

Deactivating a schedule can be done using the command:

```
/schedules deactivate-schedule
```

![deactivate-schedule](/screenshots/deactivate-schedule.png)

Multiple schedules can be deactivated with:

```
/schedules deactivate-schedules
```

And all schedules can be deactivated with:

```
/schedules deactivate-all
```

The same commands exists for activating a schedule.

### Removing a Schedule

A schedule can be deleted with the command:

```
/schedules delete-schedule
```

![delete-schedule](/screenshots/delete-schedule.png)

A confirmation will be requested before any deletion.

![delete-schedule-confirm](/screenshots/delete-schedule-confirm.png)

![delete-schedule-success](/screenshots/delete-schedule-success.png)

Note that like activating and deactivating, there are commands available to delete more than one schedule at a time.

```
/schedules delete-schedules
/schedules delete-all
```

### Manual Open and Closing

Channels with active schedules can have the opening or closing triggered manually.
This can be done with the commands:

```
/schedules manual-open
/schedules manual-close
```

![manual-close](/screenshots/manual-close.png)
![manual-close-success](/screenshots/manual-close-success.png)

**Manual opening and closing only works on channels with an active schedule!**

### Schedule Global Settings

The following schedules settings apply to all schedules created on the server:

![schedule-settings](/screenshots/schedules-settings.png)

The open and close messages are the base messages that are included with every command. The warning time governs how long before a closure a warning is issued. The inactive and delay times related to the dynamic scheduling behaviour.

These settings can be set using the commands under the command group:

```
/schedules-settings
```

![schedules-settings-commands](/screenshots/schedule-settings-commands.png)

## Friend Code Filtering

By default this feature is turned off.

The bot can monitor all messages on the server and remove those that contain friend codes. The bot will send a message, mentioning the user, telling them the message has been removed and where friend codes are allowed. The message from Snorlax will auto-delete after one minute.

The feature is activated when a channel is added to the whitelist. This is done with the command:

```
/friend-code-filter add-channel
```

![friend-code-commands](/screenshots/friend-code-commands.png)
![friend-code-add](/screenshots/friend-code-add.png)
![friend-code-add](/screenshots/friend-code-add-success.png)

The `secret` option (accepting the true and false like above) if true means that while friend codes will be allowed in the added channel, it won't be communicated to the user in the removal notice message.

Channels in the whitelist can be view with the command

```
/friend-code-filter list
```

![friend-code-add](/screenshots/friend-code-list.png)

A user will see the following message when they attempt to post a friend code in a non-whitelisted channel:

![FriendCodeRemoval](/screenshots/friend-code-filter-message.png)

### Friend Code Filtering & Meowth/PokeNav

Some raid bots create individual channels for raids, where of course friend codes need to be shared.
You can use the command: 

```
/admin set-pokenav-raid-category
```

to add a category where any channels created within the category will be added to the friend code whitelist automatically.
Only set this if the friend code filter is being used.
To get the category id, make sure you developer mode activated on Discord and then proceed to right click on the category, and select `Copy ID`.

The `PokenavRaidCategory` can be reset with:

```
/admin reset-pokenav-raid-category
```

Currently only one category can be set.

## Any Raids Filter

By default this feature is turned off.

The bot can monitor all messages on the server and remove those that contain the expression `any raids?` or `any X raids?`.
Snorlax will let the user know to please not spam this message in raid channels.

The feature is activated by issuing the command below in the admin channel:

```
/any-raids-filter activate
```

![any-raids-commands](/screenshots/any-raids-commands.png)

It is deactivated with:

```
/any-raids-filter deactivate
```

When a user triggers the filter they will see:

![any-raids-filter-message](/screenshots/any-raids-filter-message.png)

## Join Name Filtering

**Note this feature is not fully supported yet as it only supports a global list of banned names**.

By default this feature is turned off.

The bot can ban new members to a server who's name matches a user defined pattern list.

The feature is activated by issuing the command below in the admin channel:

```
/join-name-filter activate
```

It is deactivated with:

```
/join-name-filter deactivate
```

![join-name-filter](/screenshots/join-name-filter-commands.png)

The ban list is defined in the `.env` file using a comma separated list. For example:

```
BAN_NAMES=firstname,secondname
```

The patterns will be matched by converting names to lower case.
