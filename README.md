
# pypresence
A Discord rich presence library in python! Wow!

## So you want docs? Fine.


### The Client

`pypresence.client(client_id)`

Construct the client.

* `client_id`: OAuth2 application id `[string]`

----------

`client.start()`

Start up the client so it is ready to perform commands.

----------

`client.close()`

Stop the client.

----------

`client.authorize(client_id, scopes)`

Used to authenticate a new client with your app. By default this pops up a modal in-app that asks the user to authorize access to your app.

* `client_id`: OAuth2 application id `[string]`
* `scopes`: a list of OAuth scopes as strings `[list]`

----------

`client.authenticate(token)`

Used to authenticate an existing client with your app.

* `token`: OAuth2 access token `[string]`

----------

`client.get_guilds()`

Used to get a list of guilds the client is in.

----------

`client.get_guild(guild_id)`

Used to get a guild the client is in.

* `guild_id`: id of the guild to get `[string]`

----------

`client.get_channels(guild_id)`

Used to get a guild's channels the client is in.

* `guild_id`: id of the guild to get channels for `[string]`

----------

`client.get_channel(channel_id)`

Used to get a channel the client is in.

* `channel_id`: id of the channel to get `[string]`

----------

`client.set_user_voice_settings(user_id, pan_left=None, pan_right=None, volume=None, mute=None)`

Used to change voice settings of users in voice channels.

* `user_id`: user id `[string]`
* `pan_left`: left pan of the user `[float]`
* `pan_right`: right pan of the user `[float]`
* `volume`: the volume of user (defaults to 100, min 0, max 200) `[int]`
* `mute`: the mute state of the user `[bool]`

----------

`client.select_voice_channel(channel_id)`

Used to join and leave voice channels, group dms, or dms.

* `channel_id`: channel id to join (or `None` to leave) `[string]`

----------

`client.get_selected_voice_channel()`

Used to get the client's current voice channel.

----------

`client.select_text_channel(channel_id)`

Used to join and leave text channels, group dms, or dms.

* `channel_id`: channel id to join (or `None` to leave) `[string]`

----------

`client.set_activity(pid=os.getpid(), state=None, details=None, start=None, end=None, large_image=None, large_text=None, small_image=None, small_text=None, party_id=None, party_size=None, join=None, spectate=None, match=None, instance=True)`

Used to set the activity shown on Discord profiles and status of users.

* `pid`: the process id of your game `[int]`
* `state`: the user's current status `[string]`
* `details`: what the player is currently doing`[string]`
* `start`: seconds for game start `[int]` 
* `end`: seconds for game end `[int]` 
* `large_image`: name of the uploaded image for the large profile artwork `[string]` 
* `large_text`: tooltip for the large image `[string]` 
* `small_image`: name of the uploaded image for the small profile artwork `[string]`
* `small_text`: tootltip for the small image `[string]` 
* `party_id`: id of the player's party, lobby, or group `[string]`
* `party_size`: current size of the player's party, lobby, or group, and the max `[list]`
* `join`: unique hashed string for chat invitations and ask to join `[string]`
* `spectate`: unique hashed string for spectate button `[string]`
* `match`: unique hashed string for spectate and join `[string]`
* `instance`: marks the match as a game session with a specific beginning and end `[bool]`
----------

`client.subscribe(event,args={})`

Used to subscribe to events.

* `event`: event name to subscribe to `[string]`
* `args`: any args to go along with the event `[dict]`

----------

`client.unsubscribe(event,args={})`

Used to unsubscribe from events.

* `event`: event name to unsubscribe from `[string]`
* `args`: any args to go along with the event `[dict]`

----------

`client.get_voice_settings()`

Get the user's voice settings.

----------
