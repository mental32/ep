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

First we have to generate a configuration file. We can do this easily with:
 - `ep -C > foo.ep.toml`

Now lets write our cog, here we're creating the file `./cogs/ping.py`:

```py
# ./cogs/ping.py
from ep import Cog

@Cog.export(expose=True)
class Ping(Cog):
    def action(self) -> str:
        return 'Pong!'
```

The bot can now be run with:
 - `ep -c foo.ep.toml`

Ep uses the [episcript execution engine](https://github.com/mental32/episcript)
as a front facing user interface, this means that you interact with the bot
mainly through writing regular Python code

 - `cogs["Ping"].action()`

## Installing

 - `pip3 install git+https://github.com/mental32/ep#egg=ep`
