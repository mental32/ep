from re import compile as re_compile, Pattern
from typing import Union

from ..event import EventHandler


RegexPattern = Union[str, Pattern]
LITERAL_TYPES = (
    int,
    str,
    float,
    list,
    tuple,
    dict,
    set,
    frozenset,
)


class RegexHandler(EventHandler):
    async def should_run(self, args, kwargs) -> bool:
        if not await super().should_run(args, kwargs):
            return False

        return await self._should_run(args, kwargs, self.pattern)

    async def _should_run(self, args, kwargs, pattern: Pattern) -> bool:
        # Named groups in a pattern have the potential to be arguments in the signiture
        kwargs.update(dict(zip(pattern.groupindex, cycle([None]))))

        bound = self.signiture.bind(*args, **kwargs)

        try:
            content = bound.arguments["message"].content
        except KeyError:
            if not any(isinstance(arg, Message) and (content := arg.content) for arg in bound.args):
                raise ValueError("could not infer message object (needed for a regex match.)")

        filter_ = {
            None: (lambda match: match is None),
            True: (lambda _: True),
            False: (lambda _: False),
        }.get(self.filter_, self.filter_)

        loop = asyncio.get_event_loop()
        match = await loop.run_in_executor(None, partial(pattern.fullmatch, content))
        del loop

        if filter_(match):
            return False

        if match is not None:
            group_dict = match.groupdict()
            annotations = corofunc.__annotations__

            kwargs_ = {**group_dict}

            for name in (set(group_dict) & set(annotations)):
                argument_annotation = annotations[name]
                argument = value = group_dict[name]

                # TODO: Tuples, ...

                if argument_annotation in LITERAL_TYPES:
                    try:
                        value = ast.literal_eval(argument)
                    except (ValueError, SyntaxError):
                        value = argument

                elif argument_annotation.__origin__ is Union:
                    for arg in argument_annotation.__args__:
                        try:
                            value = ast.literal_eval(argument)
                        except ValueError:
                            continue
                        else:
                            break

                else:
                    value = argument

                kwargs_[name] = value

            kwargs.update(kwargs_)

        return True


class FormattedRegexHandler(RegexHandler):
    async def _should_run(self, args, kwargs, pattern: Pattern) -> bool:
        bound = self.signature.bind(*args, **kwargs)

        template = Template(pattern)
        fmt = template.substitute(formatter(bound.arguments["self"].client))

        return await super()._should_run(args, kwargs, re_compile(fmt))
