import inspect
import random
import string
import enum
from pprint import pformat

import discord
from discord.ext.commands import Context
from discord.ext.commands.view import StringView

from .attrs import allowed

ascii_letters = string.ascii_letters + '_'

pseudo_invoke = lambda content: len(content) >= 2 and content.count('`') == 1 and content[0] == '`' and content[1] in ascii_letters
pretty_invoke = lambda content: len(content) >= 3 and content[:2] == '``' and content[2] in ascii_letters

class TokenTypes(enum.IntEnum):
    OTHER = 0
    NAME = 1


class Pseudo:
    def __init__(self, bot):
        self.bot = bot
        self._users = {}

    async def on_message(self, message):
        if message.author.bot:
            return

        elif message.channel.id == 534364800679936000:
            if pseudo_invoke(message.content):
                await self._invoke(message)

            elif pretty_invoke(message.content):
                await self._invoke(message, pretty=True)

    async def _invoke(self, message, pretty=False):
        try:
            output = await self._eval(Context(prefix='`', view=StringView(message.content), bot=self.bot, message=message), message.content[1 + pretty:])
        except BaseException as error:
            output = error

        if pretty:
            output = pformat(output)

        try:
            await message.channel.send(f'```\n{output}```')
        except discord.HTTPException as error:
            await message.channel.send(f'```\n{error}```')


    def _parse(self, source):
        token = []

        last_bracket = [None]
        brackets = {
            ')': '(',
            ']': '[',
            '}': '{'
        }

        # Check for unbalanced brackets before tokenizing
        for char in source:
            if char in brackets:
                if brackets[char] != last_bracket[-1]:
                    raise SyntaxError(f'Unmatched bracket: "{char}"')
                else:
                    last_bracket.pop()

            elif char in '([{':
                last_bracket.append(char)

        if last_bracket[-1] is not None:
            raise SyntaxError(f'Unmatched bracket: "{last_bracket[-1]}"')

        # Begin tokenizing and yielding
        for char in source:
            if char not in ascii_letters:
                if token:
                    yield ''.join([*token]), TokenTypes.NAME
                    token = []

                yield char, TokenTypes.OTHER

            else:
                token += [char]

        if token:
            yield ''.join([*token]), TokenTypes.NAME

    async def _eval(self, ctx, source):
        stacks = [[]]
        stack = stacks[-1]

        scope = {
            'ctx': ctx,
            'guild': ctx.guild,
            'message': ctx.message,
            'author': ctx.author,

            'choice': lambda seq: random.choice(seq),

            'len': len,
            'str': str,
            'repr': repr,
            'type': type,
        }

        if ctx.author.id in self._users:
            scope['_'] = self._users[ctx.author.id]

        check = True

        tokens = self._parse(source)

        for token, type_ in tokens:
            if type_:
                if token not in scope:
                    raise NameError(f'name {token!r} is not defined')
                else:
                    stack.append(scope[token])

                continue

            elif token == '.':
                obj, attr = stack[-1], next(tokens)[0]

                obj_t = type(obj)

                if check and obj_t not in allowed or attr not in allowed[obj_t]:
                    raise AttributeError(f'\'{obj_t}\' object has no attribute \'{attr}\'')

                value = getattr(obj, attr)

                if check:
                    func = allowed[obj_t][attr]

                    if func is not None:
                        value = func(ctx, value)

                        if inspect.iscoroutine(value):
                            value = await value    

                stack[-1] = value

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

            else:
                raise SyntaxError(f'Unexpected token! {token!r} (type={type_!r})')

        self._users[ctx.author.id] = stack[-1]

        return stack[-1]
