# Officer Snorlax Discord Bot
A simple bot for Discord that can close and open channels on a defined schedule. Also includes a Pokemon Go friend code filter option.

**Disclaimer** This is the first Discord bot I have attempted and not spent too much time on it. It seems to do the job but undoubtedly could be done much better!

## Requirements

* Python 3.5.3+ (tested on 3.8.5)
* discord.py 1.4.1
* pandas 1.1.1

There is a requirements.txt file to install the dependancies from:
```
pip install -r requirements.txt
```

## Setup

1. Create a Discord bot, take note of the token and invite the bot to your server (see this guide https://realpython.com/how-to-make-a-discord-bot-python/).

2. Clone this repo and `cd` into it.

3. Initialise the sqlite3 database using the initdb.py script:
```
python initdb.py
```
this will create `database.db`.

4. Copy the `.env_template` to `.env` and proceed to enter your settings.

5. Run the bot with:
```
python bot.py
```

## Bot Setup

**All the commands below are done on the Discord server.**

Once added to your server the bot will need to be set up with an admin channel before all the other commands can be used, this can be done by any admin in any channel:

```
@Officer Snorlax setAdminChannel <#channel-mention>
```

![setAdminChannel](/screenshots/setadmin.png)

Once this is set use the designated `admin channel` to issue all other commands. Use the help function to see a list of commands.

### Guild Timezone

You can set the timezone for your Guild (if different from the default option set in the `.env` file) using the command:

```
@Officer Snorlax setTimezone <tz>
```

where `tz` is one of the standard timezones: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones.

## Schedule Behaviour

To add a open and close schedule you mention the bot and use the `addSchedule` command in the following format:

```
@Officer Snorlax addSchedule <#channel-mention> <open-time> <close-time> "<custom-open-message>" "<custom-close-message>" <warning> <dynamic>
```

![setSchedule](/screenshots/setSchedule.png)

The time entries must be in the format of `HH:MM` in 24-hour format and the warning and dynamic are boolean entries which will accept `true,  yes, y, 1` as true. By default warning is `False` and dynamic is `True`. The custom messages are added to the base message provided in the `.env`.

It works by toggling the `@everyone` role on the channel to `deny` for closure and `neutral` for open. The bot will check if the channel is already closed or opening before applying the change, so it won't attempt to close a channel already closed for example.

![CloseAndOpen](/screenshots/CloseAndOpen.png)

### Warning Option

If selected, then if the channel has seen activity in the past `X` minutes, where `X` is determined by the setting `INACTIVE_TIME`, then `Y` minutes before the scheduled closeure, where `Y` is determined by the setting `WARNING_TIME`, the bot will post a warning that the channel is scheduled to close soon.

### Dynamic Closure Option

If the channel has been active for `INACTIVE_TIME` minutes before the closure then the closure is pushed back by `DELAY_TIME` minutes. This happens silently from the users point of view.

### Current Behaviour Warning

At the moment it's possible to add multiple schedules to one channel - BUT - these won't have knowledge of each other. So keep that in mind if you do this.

## Friend Code Filtering

By default this feature is turned off.

The bot can monitor all messages on the server and remove those that contain friend codes. The bot will send a message, mentioning the user, telling them the message has been removed and where friend codes are allowed.

The feautre is activated when a channel is added to the whitelist. This is done with the command:

```
@Officer Snorlax addFriendChannel <#channel-mention> <secret>
```

The `secret` option (accepting the true and false like above) if true means that while friend codes will be allowed in the added channel, it won't be communicated to the user in the removal notice message.

![FriendCodeRemoval](/screenshots/FriendCodeRemoval.png)



