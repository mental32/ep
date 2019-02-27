import inspect
import random
import string
import enum

import discord
from discord.ext import commands
from discord.ext.commands import Context
from discord.ext.commands.view import StringView

import src
from src.utils import GuildCog

ascii_letters = string.ascii_letters + '_'

allowed = {
    discord.Guild: {
        'name': None,
        'emojis': None,
        'region': None,
        'afk_timeout': None,
        'afk_channel': None,
        'icon': None,
        'id': None,
        'owner_id': None,
        'unavailable': None,
        'mfa_level': None,
        'verification_level': None,
        'explicit_content_filter': None,
        'default_notifications': None,
        'features': None,
        'splash': None,
        'channels': None,
        'large': None,
        'voice_channels': None,
        'me': None,
        'voice_client': None,
        'text_channels': None,
        'categories': None,
        'get_channel': None,
        'members': None,
        'get_member': None,
        'get_role': None,
        'default_role': None,
        'owner': None,
        'icon_url': None,
        'splash_url': None,
        'member_count': None,
        'created_at': None,
        'system_channel': None,
        'vanity_invite': None,
        'roles': None,
    },

    src.Bot: {
        'guilds': None,
        'emojis': None,
        'is_ready': None,
        'activity': None,
        'users': None,
    },

    discord.Member: {
        'joined_at': None,
        'activities': None,
        'guild': None,
        'nick': None,
        'status': None,
        'mobile_status': None,
        'desktop_status': None,
        'web_status': None,
        'is_on_mobile': None,
        'colour': None,
        'color': None,
        'display_name': None,
        'activity': None,
        'mentioned_in': None,
        'permissions_in': None,
        'top_role': None,
        'guild_permissions': None,
        'voice': None,
        'avatar_url': None,
        'bot': None,
        'created_at': None,
        'default_avatar_url': None,
        'discriminator': None,
        'id': None,
        'is_avatar_animated': None,
        'roles': None,
    },

    discord.ClientUser: {
        'name': None,
        'id': None,
        'discriminator': None,
        'avatar': None,
        'bot': None,
        'created_at': None,
        'default_avatar_url': None,
        'display_name': None,
        'is_avatar_animated': None,
    },

    discord.User: {
        'name': None,
        'id': None,
        'discriminator': None,
        'avatar_url': None,
        'bot': None,
        'created_at': None,
        'default_avatar_url': None,
        'display_name': None,
        'is_avatar_animated': None,
    },

    discord.Attachment: {
        'id': None,
        'size': None,
        'height': None,
        'width': None,
        'filename': None,
        'url': None,
        'proxy_url': None,
        'is_spoiler': None,
    },

    discord.Message: {
        'tts': None,
        'type': None,
        'author': None,
        'content': None,
        'nonce': None,
        'embeds': None,
        'channel': None,
        'call': None,
        'mention_everyone': None,
        'mentions': None,
        'channel_mentions': None,
        'role_mentions': None,
        'id': None,
        'webhook_id': None,
        'attachments': None,
        'pinned': None,
        'reactions': None,
        'activity': None,
        'application': None,
        'guild': None,
        'created_at': None,
        'edited_at': None,
        'jump_url': None,
    },

    discord.Reaction: {
        'emoji': None,
        'count': None,
        'me': None,
        'message': None,
        'custom_emoji': None
    },

    discord.Spotify: {
        'colour': None,
        'color': None,
        'name': None,
        'title': None,
        'artists': None,
        'artist': None,
        'album': None,
        'album_cover_url': None,
        'track_id': None,
        'start': None,
        'end': None,
        'duration': None,
        'party_id': None,
    },

    discord.VoiceState: {
        'deaf': None,
        'mute': None,
        'self_mute': None,
        'self_deaf': None,
        'self_video': None,
        'afk': None,
        'channel': None,
    },

    discord.Emoji: {
        'name': None,
        'id': None,
        'require_colons': None,
        'animated': None,
        'managed': None,
        'guild_id': None,
        'created_at': None,
        'url': None,
        'guild': None,
        'roles': None,
    },

    discord.PartialEmoji: {
        'name': None,
        'id': None,
        'animated': None,
        'url': None,
    },

    discord.Role: {
        'id': None,
        'name': None,
        'permissions': None,
        'guild': None,
        'colour': None,
        'color': None,
        'hoist': None,
        'position': None,
        'managed': None,
        'mentionable': None,
        'is_default': None,
        'created_at': None,
        'members': None,
    },

    discord.TextChannel: {
        'id': None,
        'name': None,
        'guild': None,
        'category_id': None,
        'topic': None,
        'position': None,
        'slowmode_delay': None,
        'members': None,
        'category': None,
        'created_at': None,
        'mention': None,
    },

    discord.VoiceChannel: {
        'id': None,
        'name': None,
        'guild': None,
        'category_id': None,
        'position': None,
    },

    discord.CategoryChannel: {
        'id': None,
        'name': None,
        'guild': None,
    },

    discord.DMChannel: {},
    discord.Invite: {},

    Context: {
        'message': None,
        'bot': None,
        'guild': None,
        'author': None,
    }
}

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

        elif len(message.content) >= 2 and message.content.count('`') == 1 and message.content[0] == '`' and message.content[1] in ascii_letters:
            if message.channel.id != 534364800679936000:
                return

            try:
                output = await self._eval(Context(prefix='`', view=StringView(message.content), bot=self.bot, message=message), message.content[1:])
            except BaseException as error:
                output = str(error)

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

def setup(bot):
    bot.add_cog(Pseudo(bot))
