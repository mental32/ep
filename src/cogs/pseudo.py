import inspect
import random
import string
import enum

import discord
from discord.ext import commands
from discord.ext.commands import Context
from discord.ext.commands.view import StringView

from src.utils import GuildCog

def NOP(ctx, value):
    return value

allowed = {
    discord.Guild: {
        'name': NOP,
        'emojis': NOP,
        'region': NOP,
        'afk_timeout': NOP,
        'afk_channel': NOP,
        'icon': NOP,
        'id': NOP,
        'owner_id': NOP,
        'unavailable': NOP,
        'mfa_level': NOP,
        'verification_level': NOP,
        'explicit_content_filter': NOP,
        'default_notifications': NOP,
        'features': NOP,
        'splash': NOP,
        'channels': NOP,
        'large': NOP,
        'voice_channels': NOP,
        'me': NOP,
        'voice_client': NOP,
        'text_channels': NOP,
        'categories': NOP,
        'get_channel': NOP,
        'members': NOP,
        'get_member': NOP,
        'get_role': NOP,
        'default_role': NOP,
        'owner': NOP,
        'icon_url': NOP,
        'splash_url': NOP,
        'member_count': NOP,
        'created_at': NOP,
        'system_channel': NOP,
        'vanity_invite': NOP,
        'roles': NOP,
    },

    discord.Member: {},
    discord.ClientUser: {},
    discord.User: {},
    discord.Attachment: {},
    discord.Message: {},
    discord.Reaction: {},
    discord.Spotify: {},
    discord.VoiceState: {},
    discord.Emoji: {},
    discord.PartialEmoji: {},
    discord.Role: {},
    discord.TextChannel: {},
    discord.VoiceChannel: {},
    discord.CategoryChannel: {},
    discord.DMChannel: {},
    discord.Invite: {},

    Context: {
        'message': NOP,
        'bot': NOP,
        'guild': NOP,
        'author': NOP,
    }
}

class TokenTypes(enum.IntEnum):
    OTHER = 0
    NAME = 1


class Pseudo:
    def __init__(self, bot):
        self.bot = bot

    async def on_message(self, message):
        if message.author.bot:
            return

        elif len(message.content) >= 2 and message.content[0] == '`' and message.content[1] in string.ascii_letters:
            if message.channel.id != 534364800679936000:
                return

            try:
                output = await self._eval(Context(prefix='`', view=StringView(message.content), bot=self.bot, message=message), message.content[1:])
            except BaseException as error:
                output = repr(error)

            await message.channel.send(f'```\n{output}```')

    async def pseudo_eval(self, ctx, *message):
        try:
            output = await self._eval(ctx, message[1:])
        except BaseException as error:
            output = repr(error)

        await ctx.send(f'```\n{output}```')

    def _parse(self, source):
        token = []

        last_bracket = [None]
        brackets = {
            ')': '(',
            ']': '[',
            '}': '{'
        }

        for char in source:
            if char in brackets:
                if brackets[char] != last_bracket[-1]:
                    raise SyntaxError(f'Unmatched bracket: "{char}"')
                else:
                    last_bracket.pop()

            elif char in '([{':
                last_bracket.append(char)

            if char not in string.ascii_letters:
                if token:
                    yield ''.join([*token]), TokenTypes.NAME
                    token = []

                yield char, TokenTypes.OTHER
            else:
                token += [char]

        else:
            if last_bracket[-1] is not None:
                raise SyntaxError(f'Unmatched bracket: "{last_bracket[-1]}"')

            elif token:
                yield ''.join([*token]), TokenTypes.NAME

    async def _eval(self, ctx, source):
        stacks = [[]]
        stack = stacks[-1]

        scope = {
            'ctx': ctx,
            'guild': ctx.guild,
            'author': ctx.author,

            'choice': lambda seq: random.choice(seq),

            'len': len,
            'str': str,
            'repr': repr,
        }

        tokens = self._parse(source)

        check = True # not (await ctx.bot.is_owner(ctx.author))

        for token, type_ in tokens:
            if type_:
                if token not in scope:
                    raise LookupError(f'{token!r} is not in scope!')
                else:
                    stack.append(scope[token])

                continue

            elif token == '.':
                obj, attr = stack[-1], next(tokens)[0]

                obj_t = type(obj)

                if check and obj_t not in allowed or attr not in allowed[obj_t]:
                    raise AttributeError(f'\'{obj_t}\' object has no attribute \'{attr}\'')

                if check:
                    value = allowed[obj_t][attr](ctx, getattr(obj, attr))

                    if inspect.iscoroutine(value):
                        value = await value

                    stack[-1] = value
                else:
                    stack[-1] = getattr(obj, attr)         

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

        return stack[-1]

def setup(bot):
    bot.add_cog(Pseudo(bot))
