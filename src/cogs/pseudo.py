import random
import string
import enum

from discord.ext import commands

from src.utils import GuildCog

class TokenTypes(enum.IntEnum):
    OTHER = 0
    NAME = 1

class Pseudo:
    async def on_message(self, message):
        if message.author.bot:
            return

        elif len(message) >= 2 and message[0] == '`' and message[1] in string.ascii_letters:
            try:
                output = await self._eval(message[1:])
            except BaseException as error:
                output = str(error)

            await message.channel.send(f'```\n{output}```')

    @commands.Command(name='eval')
    @commands.is_owner()
    async def pseudo_eval(self, ctx, *message):
        try:
            output = await self._eval(ctx, message[1:])
        except BaseException as error:
            output = str(error)

        await message.channel.send(f'```\n{output}```')

    def _parse(self, source):
        token = []

        for char in source:
            if char not in string.ascii_letters:
                if token:
                    yield ''.join([*token]), TokenTypes.NAME
                    token = []

                yield char, TokenTypes.OTHER
            else:
                token += [char]
        else:
            if token:
                yield ''.join([*token]), TokenTypes.NAME

    async def _eval(self, ctx, source):
        stacks = [[]]
        stack = stacks[-1]

        scope = {
            'ctx': ctx,
            'guild': ctx.guild,
            'author': ctx.author,
            'choice': lambda seq: random.choice(seq)
        }

        tokens = self._parse(stmt)

        for token, type_ in tokens:
            if type_:
                if token not in scope:
                    raise LookupError(f'{token!r} is not in scope! ({scope!r})')
                else:
                    stack.append(scope[token])
                continue

            elif token == '.':
                stack[-1] = getattr(stack[-1], next(tokens)[0])

            elif token == '(':
                stacks.append([])
                stack = stacks[-1]

            elif token == ')':
                value = stacks[-2][-1](*stack)

                if inspect.iscoroutine(value):
                    value = await value

                stacks.pop()
                stack = stacks[-1]

                stack[-1] = value

        return stack
