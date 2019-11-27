"""Captcha based authentication for discord."""

from asyncio import wait, Future, TimeoutError  # pylint: disable=redefined-builtin
from dataclasses import dataclass, field
from functools import partial
from os import close
from pathlib import Path
from random import choice
from string import ascii_letters, digits
from tempfile import mkstemp
from typing import Tuple, ClassVar, Set

from captcha.image import ImageCaptcha
from discord import Member, Message, Role, File, Embed
from ep import Cog, Client

ASCII: str = ascii_letters + digits


@dataclass
class CaptchaFlow:
    """Represents the state of a captcha flow."""

    member: Member
    client: Client
    done: bool = field(default=False)

    __captcha: ClassVar[ImageCaptcha] = ImageCaptcha()

    def __post_init__(self):
        self.client.schedule_task(self.start())

    def generate(self) -> Tuple[Path, str]:
        """Generate a secret and an image captcha."""
        secret = "".join(choice(ASCII) for _ in range(8))

        desc, filepath = mkstemp()
        close(desc)

        self.__captcha.write(secret, filepath)

        return Path(filepath), secret

    async def start(self):
        """Begin the captcha flow for a given :class:`discord.Member`."""
        path, secret = await self.client.loop.run_in_executor(None, self.generate)

        file = File(str(path))
        embed = Embed(title="Captcha flow")
        embed.set_image(url=f"attachment://{path!s}")

        await self.member.send(file=file, embed=embed)

        def check(message: Message) -> bool:
            return message.author == self.member and message.guild is None

        while True:
            try:
                message = await wait(self.client.wait_for("message", check=check), timeout=300)
            except TimeoutError:
                path.unlink()
                return await self.start()

            if message.content == secret:
                self.done = True
                break


@Cog.export
class Captcha(Cog):
    """A :class:`ep.Cog` responsible for state tracking of all :class:`CaptchaFlow`s."""
    flows: Set[CaptchaFlow]

    _member_role_id: int
    _bot_role_id: int

    # Internals

    def __post_init__(self):
        self.flows = set()
        self._member_role_id = self.config["default"]["guild_member_role"]
        self._bot_role_id = self.config["default"]["guild_bot_role"]

    def __get_role(self, name: str) -> Role:
        snowflake: int = getattr(self, f"_{name}_id")
        role = self.client.get_role(snowflake)
        assert role is not None, f"{name} => {snowflake}"
        return role

    # Properties

    member_role = property(partial(__get_role, "member_role"))
    bot_role = property(partial(__get_role, "bot_role"))

    # Event handlers

    @Cog.event(tp="on_member_join", member_bot=False)
    @Cog.wait_until_ready
    async def start_user_captcha(self, member: Member) -> None:
        """Given a :class:`discord.Member` begin a captcha authentication flow."""
        flow = CaptchaFlow(member, self.client)

        task = self.client.schedule_task(flow.start())

        def remove_flow(future: Future) -> None:
            self.flows.remove(flow)
            future.result()  # Propagate exceptions
            self.client.schedule_task(member.add_roles(self.member_role))

        task.add_done_callback(remove_flow)

        self.flows.add(flow)

    @Cog.event(tp="on_member_join", member_bot=True)
    @Cog.wait_until_ready
    async def role_bot(self, member: Member) -> None:
        """Callback that gives bots the bot role."""
        assert member.bot
        await member.add_roles(self.bot_role)
