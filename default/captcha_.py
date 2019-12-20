"""Captcha based authentication for discord."""

from asyncio import Future, Task, TimeoutError  # pylint: disable=redefined-builtin
from functools import partial
from os import close
from pathlib import Path
from random import choice
from string import ascii_uppercase, digits
from tempfile import mkstemp
from typing import Tuple, ClassVar, Dict, Optional

from captcha.image import ImageCaptcha
from discord import Member, Message, Role, File, Embed, Invite
from ep import Cog, ConfigValue

__all__ = {"Captcha"}

ASCII: str = ascii_uppercase + digits


@Cog.export
class Captcha(Cog):
    """A :class:`ep.Cog` responsible for state tracking of all :class:`CaptchaFlow`s."""

    flows: Dict[Member, Task]
    __captcha: ClassVar[ImageCaptcha] = ImageCaptcha()

    _TIMED_OUT: str = "You've been timed out. I've had to remove you from the guild."

    _guild_id: int = ConfigValue("default", "guild_snowflake")
    _member_role_id: int = ConfigValue("default", "guild_member_role")
    _bot_role_id: int = ConfigValue("default", "guild_bot_role")
    _is_enabled: bool = ConfigValue("default", "captcha", "enabled", default=True)

    def __post_init__(self):
        self.flows = {}

    # Internals

    def _generate_captcha(self) -> Tuple[Path, str]:
        """Generate a secret and an image captcha."""
        secret = "".join(choice(ASCII) for _ in range(8))

        desc, filepath = mkstemp(suffix=".png")
        close(desc)

        self.__captcha.write(secret, filepath)

        return Path(filepath), secret

    async def _start_flow(self, member: Member, invite: Optional[Invite] = None):
        """Begin the captcha flow for a given :class:`discord.Member`."""
        path, secret = await self.client.loop.run_in_executor(
            None, self._generate_captcha
        )

        self.client.logger.info(
            "Started captcha auth flow for %s with secret %s", str(member), repr(secret)
        )

        file = File(str(path))
        embed = Embed(title="Captcha flow")
        embed.set_image(url=f"attachment://{path.name!s}")

        message = await member.send(file=file, embed=embed)

        def check(message: Message) -> bool:
            return message.author == member

        wait_for = partial(self.client.wait_for, check=check, timeout=300)
        invite_fmt: str = f" if you'd like to rejoin use {invite}." if invite is not None else "."

        while message.content != secret:
            try:
                message = await wait_for("message")
            except TimeoutError:
                await member.send(self._TIMED_OUT + invite_fmt)
                raise
            finally:
                path.unlink()

    def _get_role(self, ident: int) -> Role:
        guild = self.client.get_guild(self._guild_id)

        if self.client.is_ready():
            assert guild is not None

        return guild.get_role(ident)

    # Event handlers

    @Cog.event(tp="on_member_leave", member_bot=False)
    @Cog.wait_until_ready
    async def pop_member_flow(self, member: Member) -> None:
        """Remove the flow for a given :class:`discord.Member`."""
        if (task := self.flows.pop(member, None)) is not None:
            task.cancel()

    @Cog.event(tp="on_member_join", member_bot=False)
    @Cog.wait_until_ready
    async def start_user_captcha(self, member: Member) -> None:
        """Given a :class:`discord.Member` begin a captcha authentication flow."""
        if (member_role := self._get_role(self._member_role_id)) is None:
            self.logger.error(
                "Could not get the member role with ID %s", self._member_role_id
            )
            return

        if not self._is_enabled:
            await member.add_roles(member_role)
            return

        assert member not in self.flows

        task = self.client.schedule_task(self._start_flow(member))

        def remove_flow(future: Future) -> None:
            try:
                future.result()  # Propagates any exceptions
            except TimeoutError:
                self.client.schedule_task(member.kick(reason="Captcha timeout exceeded."))
                return
            finally:
                self.flows.pop(member, None)

            self.client.schedule_task(member.add_roles(member_role))
            self.logger.info(
                "Successfully completed captcha auth flow for %s adding roles: %s",
                str(member),
                repr(member_role),
            )

        task.add_done_callback(remove_flow)

        self.flows[member] = task

    @Cog.event(tp="on_member_join", member_bot=True)
    @Cog.wait_until_ready
    async def role_bot(self, member: Member) -> None:
        """Callback that gives bots the bot role."""
        assert member.bot, "Wait...something really bad just happened."

        if (bot_role := self._get_role(self._bot_role_id)) is None:
            self.logger.error(
                "Could not get the bot role with ID %s", self._bot_role_id
            )
            return

        await member.add_roles(bot_role)
