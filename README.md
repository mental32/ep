# Ep
## A different kind of discord bot framework

## Index

 - [Abstract](#Abstract)
 - [Examples](#Examples)
 - [Installing](#Installing)

## Abstract

Ep started out as a wholesome discord bot for the efficient python
[discord guild](https://discord.gg/rmK6jWM) but as time passed it
grew into a large, wild, not very well maintained code base.

Ep is to the commands extension what django is to flask, just a
batteries included approach to making discord bots. It's separated
as a library and discord bot because I found some of the core logic
usefull for some other projects.

## Examples

### Ping!

First lets write our cog, here we're creating the file `./cogs/ping.py` (create the `cogs` directory if you haven't already):

```py
# ./cogs/ping.py

from discord import Message
from ep import Cog

@Cog.export
class Ping(Cog):

    @Cog.regex(r"!ping", message_author_bot=False)
    def action(self, message: Message) -> str:
        await message.channel.send('Pong!')
```

Now we have to generate a configuration file. We can do this easily with:

 - `ep -C > ./cogs/foo.ep.toml`


Then set the discord token, this is done as an environment variable:

 - `export DISCORD_TOKEN="YOUR_TOKEN_HERE"`

The bot can now be run with:
 - `ep -c ./cogs/foo.ep.toml`

### Events

```py
class RegularStyle(Cog):
    @Cog.event
    async def on_message(self, message: Message) -> None:  # Plain ol' boring events, ugh
        pass
```

```py
class NewStyle(Cog):
    @Cog.event(tp="on_message", message_channel_id=SPECIAL_CHANNEL)  # Alright! now we can apply predicates over event dispatch.
    async def filtered_message(self, message: Message) -> None:
        pass
```

```py
class DoCommandsWork(Cog):
    @Cog.regex(r'[\.!$]check')
    async def check_trigger(self, message: Message) -> None:
        await message.channel.send("Yes, it's just a regular expression :)")
```

## Installing

 - `pip3 install git+https://github.com/mental32/ep#egg=ep`
