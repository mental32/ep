"""Captcha based authentication for discord."""

from asyncio import wait, Future, Task, TimeoutError  # pylint: disable=redefined-builtin
from dataclasses import dataclass, field
from functools import partial
from os import close
from pathlib import Path
from random import choice
from string import ascii_letters, digits
from tempfile import mkstemp
from typing import Tuple, ClassVar, Set, Dict

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

    def __hash__(self):
        return hash(self.member)

    def generate(self) -> Tuple[Path, str]:
        """Generate a secret and an image captcha."""
        secret = "".join(choice(ASCII) for _ in range(8))

        desc, filepath = mkstemp(suffix=".png")
        close(desc)

        self.__captcha.write(secret, filepath)

        return Path(filepath), secret

    async def start(self):
        """Begin the captcha flow for a given :class:`discord.Member`."""
        path, secret = await self.client.loop.run_in_executor(None, self.generate)

        self.client.logger.info("Started captcha auth flow for %s with secret %s", str(self.member), repr(secret))

        file = File(str(path))
        embed = Embed(title="Captcha flow")
        embed.set_image(url=f"attachment://{path.name!s}")

        await self.member.send(file=file, embed=embed)

        def check(message: Message) -> bool:
            return message.author == self.member and message.guild is None

        while True:
            try:
                message = await self.client.wait_for("message", check=check, timeout=300)
            except TimeoutError:
                path.unlink()
                return await self.start()

            if message.content == secret:
                self.done = True
                break


@Cog.export
class Captcha(Cog):
    """A :class:`ep.Cog` responsible for state tracking of all :class:`CaptchaFlow`s."""
    flows: Dict[int, Tuple[CaptchaFlow, Task]]

    _member_role_id: int
    _bot_role_id: int

    # Internals

    def __post_init__(self):
        self.flows = {}
        self._guild_id = self.config["default"]["guild_snowflake"]
        self._member_role_id = self.config["default"]["guild_member_role"]
        self._bot_role_id = self.config["default"]["guild_bot_role"]

    def __get_role(self, name: str) -> Role:
        if not self.client.is_ready():
            return None

        snowflake: int = getattr(self, f"_{name}_id")

        guild = self.client.get_guild(self._guild_id)
        assert guild is not None

        role = guild.get_role(snowflake)
        assert role is not None, f"{name} => {snowflake}"

        return role

    # Properties

    member_role = property((lambda self: self.__get_role("member_role")))
    bot_role = property((lambda self: self.__get_role("bot_role")))

    # Event handlers

    @Cog.event(tp="on_member_leave", member_bot=False)
    @Cog.wait_until_ready
    async def pop_member_flow(self, member: Member) -> None:
        """Remove the flow for a given :class:`discord.Member`."""
        if (pair := self.flows.pop(member.id, None)) is not None:
            flow, task = pair
            task.cancel()
            await flow.member.send("The captcha has been invalidated since you've left the guild.")

    @Cog.event(tp="on_member_join", member_bot=False)
    @Cog.wait_until_ready
    async def start_user_captcha(self, member: Member) -> None:
        """Given a :class:`discord.Member` begin a captcha authentication flow."""
        if member.id in self.flows:
            return

        flow = CaptchaFlow(member, self.client)

        task = self.client.schedule_task(flow.start())

        def remove_flow(future: Future) -> None:
            self.flows.pop(flow, None)
            future.result()  # Propagate exceptions
            self.logger.info("Successfully completed captcha auth flow for %s", str(member))
            self.client.schedule_task(member.add_roles(self.member_role))

        task.add_done_callback(remove_flow)

        self.flows[member.id] = (flow, task)

    @Cog.event(tp="on_member_join", member_bot=True)
    @Cog.wait_until_ready
    async def role_bot(self, member: Member) -> None:
        """Callback that gives bots the bot role."""
        assert member.bot
        await member.add_roles(self.bot_role)
