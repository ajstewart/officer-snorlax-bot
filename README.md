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

This is yet to be updated to use discord.py >= 2.0, so threads and slash commands are not supported.

## Requirements

* Python 3.5.3+ (tested on 3.8.5)
* discord.py > 1.6.0, < 2.0
* pandas > 1.1.0

There is a requirements.txt file to install the dependancies from:
```
pip install -r requirements.txt
```

## Self-Hosting Setup

1. Create a Discord bot, take note of the token and invite the bot to your server (see this guide https://realpython.com/how-to-make-a-discord-bot-python/).

2. Clone this repo and `cd` into it.

3. Checkout the `main` branch.

```
git checkout main
```

4. Initialise the sqlite3 database using the initdb.py script:
```
python initdb.py
```
this will create `database.db`.

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

## Bot Setup

**All the commands below are done on the Discord server.**

Once added to your server the bot will need to be set up with an admin channel before all the other commands can be used, this can be done by any admin in any channel:

```
@Officer Snorlax setAdminChannel <#channel-mention>
```

![setAdminChannel](/screenshots/setadmin.png)

Once this is set use the designated `admin channel` to issue all other commands. Use the help function to see a list of commands.

A summary of all the settings can be shown with the command

```
@Officer Snorlax showSettings
```

### Log Channel

Snorlax will notify of automated events, such as channel opening, closing and message filters, in a designated log channel. 
To enable logging firstly create or identify the text channel where you wish logs to be written to. 
Then in the admin channel use the command:

```
@Officer Snorlax setLogChannel <#channel-mention>
```

Log messages will now be sent to your chosen channel.

![setLogChannel](/screenshots/setLogChannel.png)
![Log Example](/screenshots/log_example.png)

### Guild Timezone

You can set the timezone for your Guild (if different from the default option set in the `.env` file) using the command:

```
@Officer Snorlax setTimezone <tz>
```

where `<tz>` is one of the standard timezones: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones.

For example:

```
@Officer Snorlax setTimezone Europe/London
```

### Guild Prefix

By default the bot will respond to the `!` prefix or a direct mention.
The prefix can be changed by using the `setPrefix` option.

```
@Officer Snorlax setPrefix <prefix>
```

The prefix must be 3 characters or shorter.
For example:

```
@Officer Snorlax setPrefix $
```

## Local Time Display Channel

The local time and timezone of the server can be displayed to server members by using a voice channel. 
The name of the voice channel is updated periodically to represent the time.
**Note**: Because of Discord rate limiting the amount of times a bot can change a channel name, the time is only updated every 10 mins.
On first launch the bot will wait for a even 10 minute time to start displaying the time. E.g. if you launch the bot at 1:36 the first update will be done at 1:40.

To set this up:

  1. Create a voice channel and make sure the permissions are so that no one can connect to it.
  2. Copy the ID of the voice channel created.
  3. Enter the following command in Discord in the Snorlax admin channel, replacing ID with the channel ID copied (the `<#>` is needed in this case):
    ```
    @Officer Snorlax setTimeChannel <#ID>
    ```

The voice channel name will now be updated every 10 minutes and will look like the example below.

![setTimeChannel](/screenshots/setTimeChannel.png)
![Time Example](/screenshots/time_display_example.png)

## Schedule Behaviour

To add an open and close schedule you mention the bot and use the `createSchedule` command in the following format:

```
@Officer Snorlax createSchedule <#channel-mention> <open-time> <close-time> "<custom-open-message>" "<custom-close-message>" <warning> <dynamic> <max_num_delays> <silent>
```

![createSchedule](/screenshots/createSchedule.png)

The time entries must be in the format of `HH:MM` in 24-hour format and the warning and dynamic are boolean entries which will accept `true,  yes, y, 1, on` as true. 
By default warning is `False` and dynamic is `True`. 
The custom messages are added to the base message provided in the `.env`.
A custom message with spaces should be entered with quotation marks, e.g. `"Example open message."`.

Once created the bot will display a summary of the schedule which will include the assigned ID.
The ID is used to refer to the schedule when using other features such as updating or deleting the schedule.
A summary of all created schedules can be 

It works by toggling the `@everyone` role on the channel to `deny` for closure and `neutral` for open. 
The bot will check if the channel is already closed or opening before applying the change, so it won't attempt to close a channel already closed for example.

![CloseAndOpen](/screenshots/CloseAndOpen.png)

### Warning Option

If selected, then if the channel has seen activity in the past `X` minutes, where `X` is determined by the setting `INACTIVE_TIME`, then `Y` minutes before the scheduled closeure, where `Y` is determined by the setting `WARNING_TIME`, the bot will post a warning that the channel is scheduled to close soon.

### Dynamic Closure Option

If the channel has been active for `INACTIVE_TIME` minutes before the closure then the closure is pushed back by `DELAY_TIME` minutes. 
This happens silently from the users point of view.
There is a `max_num_delays` setting available when adding the schedule to force closure after a chosen amount of delays (defaults to 1).

### Silent Mode

When set to `True`, silent mode means that Snorlax will open and close the channel without posting the accompanying messages.

### Current Behaviour Warning

At the moment it's possible to add multiple schedules to one channel - BUT - these won't have knowledge of each other. So keep that in mind if you do this.

### Updating a Schedule

Once created the schedule can be updated using the following command:

```
@Officer Snorlax updateSchedule <id> <column> <value>
```

The `id` refers to the ID of the schedule, the `column` refers to the parameter to be changed, and `value` is the value you wish to apply.
The channel of a schedule cannot be changed using this method.
The available columns to use are:

  * `open` The open time.  
    ```@Officer Snorlax updateSchedule 1 open 06:30```
  * `close` The close time.  
    ```@Officer Snorlax updateSchedule 1 close 22:30```
  * `open_message` Custom open message to add to the channel open bot post.  
    ```@Officer Snorlax updateSchedule 1 open_message "Custom open message."```
  * `close_message` Custom close message to add to the channel closed bot post.  
    ```@Officer Snorlax updateSchedule 1 close_message "Custom close message."```
  * `warning` Turn on or off close warnings.  
    ```@Officer Snorlax updateSchedule 1 warning on```
  * `dynamic` Turn on or off the [dynamic closing behaviour](#dynamic-closure-option).  
    ```@Officer Snorlax updateSchedule 1 dynamic off```
  * `max_num_delays` The maximum number of delays to use with the dynamic option.  
    ```@Officer Snorlax updateSchedule 1 max_num_delays 4```
  * `silent` Turn on or off [silent mode](#silent-mode) when opening and closing channels.  
    ```@Officer Snorlax updateSchedule 1 silent on```

It is possible to update multiple values with one command.
To achieve this the format should be:

```
@Officer Snorlax updateSchedule <id> <column1> <value1> <column2> <value2> ... <columnN> <valueN>
```

for example:

```
@Officer Snorlax updateSchedule 1 open 06:30 close 22:30 silent on
```

### Deactivating & Activating a Schedule

Schedules have an 'active' status which can be on or off.
Upon creation a schedule is activated by default.
When set to off a schedule will not be processed when the time comes.

Deactivating a schedule can be done with the following commands, where the numbers used refer to the ID of the schedule to be processed.

Single schedule:
```
@Officer Snorlax deactivateSchedule 1
```

Multiple schedules:
```
@Officer Snorlax deactivateSchedules 1 2 3 10
```

All schedules:
```
@Officer Snorlax deactivateAllSchedules
```

Similarly a schedule can be set to active again using the following:

```
@Officer Snorlax activateSchedule 1
```

```
@Officer Snorlax activateSchedules 1 2 3 10
```

```
@Officer Snorlax activateAllSchedules
```

### Removing a Schedule

A schedule can be deleted by using the following commands.

Single schedule:
```
@Officer Snorlax removeSchedule 1
```

Multiple schedules:
```
@Officer Snorlax removeSchedules 1 2 3 10
```

All schedules:
```
@Officer Snorlax removeAllSchedules
```

The `removeAllSchedules` command will ask for confirmation before processing request:

![removeAllSchedules](/screenshots/remove_all_confirmation.png)

Click on the green tick emoji to confirm the deletion, or the red cross to cancel.

### Manual Open and Closing

Channels with active schedules can have the opening or closing triggered manually.
This can be done with the commands:
```
@Officer Snorlax manualOpen <#channel-mention>
```
and
```
@Officer Snorlax manualClose <#channel-mention>
```

There is also an option to perform the action silently by entering:
```
@Officer Snorlax manualOpen <#channel-mention> True
```

By default silent mode is turned off when using the manual commands regardless of the schedule setting.

**Manual opening and closing only works on channels with an active schedule!**

## Friend Code Filtering

By default this feature is turned off.

The bot can monitor all messages on the server and remove those that contain friend codes. The bot will send a message, mentioning the user, telling them the message has been removed and where friend codes are allowed. The message from Snorlax will auto-delete after one minute.

The feature is activated when a channel is added to the whitelist. This is done with the command:

```
@Officer Snorlax addFriendChannel <#channel-mention> <secret>
```

The `secret` option (accepting the true and false like above) if true means that while friend codes will be allowed in the added channel, it won't be communicated to the user in the removal notice message.

![FriendCodeRemoval](/screenshots/FriendCodeRemoval.png)


### Friend Code Filtering & Meowth/PokeNav

Some raid bots create individual channels for raids, where of course friend codes need to be shared.
You can use the command: 

```
@Officer Snorlax setMeowthRaidCategory <category id>
```

to add a category where any channels created within the category will be added to the friend code whitelist automatically.
Only set this if the friend code filter is being used.
To get the category id, make sure you developer mode activated on Discord and then proceed to right click on the category, and select `Copy ID`.

The `MeowthRaidCategory` can be reset with:

```
@Officer Snorlax resetMeowthRaidCategory
```

Currently only one category can be set, but this is planned to expanded in future to support defining multiple categories.

## Any Raids Filter

By default this feature is turned off.

The bot can monitor all messages on the server and remove those that contain the expression `any raids?` or `any X raids?`.
Snorlax will let the user know to please not spam this message in raid channels.

The feature is activated by issuing the command below in the admin channel:

```
@Officer Snorlax activateAnyRaidsFilter
```

It is deactivated with:

```
@Officer Snorlax deactivateAnyRaidsFilter
```

## Join Name Filtering

By default this feature is turned off.

The bot can ban new members to a server who's name matches a user defined pattern list.

The feature is activated by issuing the command below in the admin channel:

```
@Officer Snorlax activateJoinNameFilter
```

It is deactivated with:

```
@Officer Snorlax deactivateJoinNameFilter
```

The ban list is defined in the `.env` file using a comma separated list. For example:

```
BAN_NAMES=firstname,secondname
```

The patterns will be matched by converting names to lower case.