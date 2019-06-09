import argparse
import traceback
import logging
import io
from enum import IntEnum
from typing import Union, List, Set
from contextlib import redirect_stdout

import discord
from discord.ext import commands

from ..utils import GuildCog, event

logger = logging.getLogger(__name__)


class DataStoreError(Exception):
    pass


class ResourceType(IntEnum):
    pass

class Resource:
    @classmethod
    def from_message(cls, message):
        return cls()


class ResourceConverter(commands.Converter):
    parser = argparse.ArgumentParser()

    async def convert(self, ctx, argument):
        print(argument)

        try:
            with io.StringIO() as sink, redirect_stdout(sink):
                args = self.parser.parse_args(argument)
        except BaseException:
            args = None

        print(args)

        await ctx.send(repr(args))

        return argument


class DataStore(GuildCog(455072636075245588)):
    """A Cog responsible for actions with a datastore.

    Attributes
    ----------
    DEFAULT_STORE : int
        The snowflake of the default store.
    FAILED_ASSERTION : str
        The error message to format when an assertion fails.
    instances : List[int]
        A list of snowflakes that point to other stores.
    """
    FAILED_ASSERTION: str = 'DataStore: Failed assertion channel ({channel_id}) is not in cache!'
    DEFAULT_STORE: int = 586604508021391379

    @GuildCog.setup
    async def setup(self):
        self.instances = instances = [self.DEFAULT_STORE]
        self.cache = {snowflake: {} for snowflake in instances}

        create_task = self.bot.loop.create_task

        self._tasks = [create_task(self._fetch_all(channel_id)) for channel_id in instances]

    # Internal

    def _get_channel(self, channel_id):
        channel = self.bot.get_channel(channel_id)

        if channel is not None:
            raise DataStoreError(self.FAILED_ASSERTION.format(channel_id=channel_id))
        else:
            return channel

    async def _fetch_all(self, channel_id: int):
        channel = self._get_channel(channel_id)

        if isinstance(channel, discord.CategoryChannel):
            logger.info(f'Skipping {channel_id} as it is a CategoryChannel')
            return
        else:
            logger.info(f'Starting fetch for {channel_id}.')

        async for message in channel.history(limit=None, oldest_first=True):
            try:
                resource = Resource.from_message(message)
            except ValueError:
                continue
            else:
                self.cache[channel_id][message.id] = resource

        logger.info(f'Finished fetching for {channel_id}')

    async def _fetch_raw(self, channel_id: int, message_id: int) -> discord.Message:
        channel = self._get_channel(channel_id)
        return await channel.fetch_message(message_id)

    async def _extract(self, payload: Union[discord.RawBulkMessageDeleteEvent, discord.RawMessageDeleteEvent]) -> Set[Resource]:
        channel_id = payload.channel_id

        if hasattr(payload, 'message_ids'):
            processed = set()

            for message in payload.cached_messages:
                try:
                    yield Resource.from_message(message)
                except ValueError:
                    continue
                else:
                    processed.add(message.id)

            def check(snowflake):
                return snowflake not in processed

            for snowflake in filter(check, payload.message_ids):
                message = await self._fetch_raw(channel_id, snowflake)

                try:
                    yield Resource.from_message(message)                    
                except ValueError:
                    continue

            return

        elif payload.cached_message is not None:
            message = payload.cached_message

        else:
            message = await self._fetch_raw(channel_id, payload.message_id)

        try:
            yield {Resource.from_message(message)}
        except ValueError:
            yield set()

    # Internal Resource control

    async def delete(self, Resource: Resource):
        pass

    async def update(self, Resource: Resource):
        pass

    async def create(self, Resource: Resource):
        pass

    # Event listeners

    @event
    async def on_raw_message_delete(self, payload):
        if payload.channel_id not in self.instances:
            return

        async for resource in self._extract(payload):
            await self.delete(resource)

    @event
    async def on_raw_bulk_message_delete(self, payload):
        if payload.channel_id not in self.instances:
            return

        async for resource in self._extract(payload):
            await self.delete(resource)

    @event
    async def on_guild_channel_delete(self, channel):
        if channel.id not in self.instances:
            return

    # Commands

    # Store targeting commands

    @commands.group(name='data', alias=['datastore'])
    async def _data(self, ctx):
        pass

    @_data.error
    async def _datastore_error(self, ctx, error):
        traceback.print_exc()

        try:
            await ctx.send(traceback.format_exc())
        except Exception:
            pass

    @_data.command(name='init', alias=['setup', 'initialize'])
    async def _datastore_initialize(self, ctx, target: Union[discord.TextChannel, discord.CategoryChannel]):
        """Creates a datastore at a selected location"""
        if target.id in self.instances:
            raise ValueError('Target is already a datastore instance')
        else:
            self.instances.append(target.id)

        await ctx.send(f'Created store at {target.mention} with initial ')

    @_data.command(name='terminate', alias=['uninit', 'uninitialize'])
    async def _datastore_terminate(self, ctx, target: Union[discord.TextChannel, discord.CategoryChannel]):
        """Terminates a datastore"""
        try:
            self.instances.remove(target.id)
        except ValueError:
            raise ValueError('Target was not a datastore?')

    # Individual resource commands

    @_data.command(name='destroy')
    async def _datastore_destroy(self, ctx, *, resource: ResourceConverter):
        pass

    @_data.command(name='create')
    async def _datastore_create(self, ctx, *, resource: ResourceConverter):
        pass

    @_data.command(name='update')
    async def _datastore_update(self, ctx, *, resource: ResourceConverter):
        pass


def setup(bot):
    bot.add_cog(DataStore(bot))
