import asyncio
import sys
import types
import importlib
from contextlib import suppress

from discord import Client
from discord.ext.commands import errors

from ..utils import get_logger as _utils_get_logger
from .websocket import WebsocketServer
from .scheduler import TaskScheduler
from .cog import Cog


def _is_submodule(parent, child):
    return parent == child or child.startswith(parent + ".")


LOGGER = _utils_get_logger(__name__)


class ClientBase(Client, TaskScheduler):
    logger = LOGGER

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        TaskScheduler.__init__(self, self.loop)
        self.extra_events = {}
        self.__cogs = {}
        self.__extensions = {}
        self._wss = wss = WebsocketServer(self)
        self.schedule_task(wss.serve())

    # Properties

    @property
    def wss(self):
        return self._wss

    @property
    def cogs(self):
        """Mapping[:class:`str`, :class:`Cog`]: A read-only mapping of cog name to cog."""
        return types.MappingProxyType(self.__cogs)

    @property
    def extensions(self):
        """Mapping[:class:`str`, :class:`py:types.ModuleType`]: A read-only mapping of extension name to extension."""
        return types.MappingProxyType(self.__extensions)

    # Default event handlers

    async def on_connect(self):
        self.logger.info("Connected")

    async def on_ready(self):
        self.logger.info("Ready")

    # listener registration

    def add_listener(self, func, name=None):
        """The non decorator alternative to :meth:`.listen`.

        Parameters
        -----------
        func: :ref:`coroutine <coroutine>`
            The function to call.
        name: Optional[:class:`str`]
            The name of the event to listen for. Defaults to ``func.__name__``.

        Example
        --------
        .. code-block:: python3
            async def on_ready(): pass
            async def my_message(message): pass
            bot.add_listener(on_ready)
            bot.add_listener(my_message, 'on_message')
        """
        name = func.__name__ if name is None else name

        if not asyncio.iscoroutinefunction(func):
            raise TypeError("Listeners must be coroutines")

        if name in self.extra_events:
            self.extra_events[name].append(func)
        else:
            self.extra_events[name] = [func]

    def remove_listener(self, func, name=None):
        """Removes a listener from the pool of listeners.

        Parameters
        -----------
        func
            The function that was used as a listener to remove.
        name: :class:`str`
            The name of the event we want to remove. Defaults to
            ``func.__name__``.
        """

        name = func.__name__ if name is None else name

        if name in self.extra_events:
            try:
                self.extra_events[name].remove(func)
            except ValueError:
                pass

    def listen(self, name=None):
        """A decorator that registers another function as an external
        event listener. Basically this allows you to listen to multiple
        events from different places e.g. such as :func:`.on_ready`
        The functions being listened to must be a :ref:`coroutine <coroutine>`.

        Example
        --------
        .. code-block:: python3
            @bot.listen()
            async def on_message(message):
                print('one')
            # in some other file...
            @bot.listen('on_message')
            async def my_message(message):
                print('two')

        Would print one and two in an unspecified order.

        Raises
        -------
        TypeError
            The function being listened to is not a coroutine.
        """

        def decorator(func):
            self.add_listener(func, name)
            return func

        return decorator

    # Cog/extension logic

    def add_cog(self, cog):
        """Adds a "cog" to the bot.

        A cog is a class that has its own event listeners and commands.

        Parameters
        -----------
        cog: :class:`.Cog`
            The cog to register to the bot.

        Raises
        -------
        TypeError
            The cog does not inherit from :class:`.Cog`.
        CommandError
            An error happened during loading.
        """
        if not isinstance(cog, Cog):
            raise TypeError("cogs must derive from Cog")

        self.logger.info("Adding cog: %s", repr(cog))

        cog = cog.cog_inject(self)
        self.__cogs[cog.__cog_name__] = cog

    def get_cog(self, name):
        """Gets the cog instance requested.

        If the cog is not found, ``None`` is returned instead.

        Parameters
        -----------
        name: :class:`str`
            The name of the cog you are requesting.
            This is equivalent to the name passed via keyword
            argument in class creation or the class name if unspecified.
        """
        return self.__cogs.get(name)

    def remove_cog(self, name):
        """Removes a cog from the bot.

        All registered commands and event listeners that the
        cog has registered will be removed as well.
        If no cog is found then this method has no effect.

        Parameters
        -----------
        name: :class:`str`
            The name of the cog to remove.
        """

        cog = self.__cogs.pop(name, None)
        if cog is None:
            return

        cog.cog_eject(self)

    # extensions

    def _remove_module_references(self, name):
        # find all references to the module
        # remove the cogs registered from the module
        for cogname, cog in self.__cogs.copy().items():
            if _is_submodule(name, cog.__module__):
                self.remove_cog(cogname)

        # remove all the listeners from the module
        for event_list in self.extra_events.copy().values():
            remove = []
            for index, event in enumerate(event_list):
                if event.__module__ is not None and _is_submodule(
                    name, event.__module__
                ):
                    remove.append(index)

            for index in reversed(remove):
                del event_list[index]

    def _call_module_finalizers(self, lib, key):
        try:
            func = getattr(lib, "teardown")
        except AttributeError:
            pass
        else:
            with suppress(Exception):
                func(self)
        finally:
            self.__extensions.pop(key, None)
            sys.modules.pop(key, None)
            name = lib.__name__
            for module in list(sys.modules.keys()):
                if _is_submodule(name, module):
                    del sys.modules[module]

    def _load_from_module_spec(self, spec, key):
        # precondition: key not in self.__extensions
        lib = importlib.util.module_from_spec(spec)
        sys.modules[key] = lib
        try:
            spec.loader.exec_module(lib)
        except Exception as err:
            del sys.modules[key]
            raise errors.ExtensionFailed(key, err) from err

        try:
            setup = getattr(lib, "setup")
        except AttributeError:
            del sys.modules[key]
            raise errors.NoEntryPointError(key)

        try:
            setup(self)
        except Exception as err:  # pylint: disable=broad-except
            del sys.modules[key]
            self._remove_module_references(lib.__name__)
            self._call_module_finalizers(lib, key)
            raise errors.ExtensionFailed(key, err) from err
        else:
            self.__extensions[key] = lib

    def load_extension(self, name):
        """Loads an extension.

        An extension is a python module that contains commands, cogs, or
        listeners.

        An extension must have a global function, ``setup`` defined as
        the entry point on what to do when the extension is loaded. This entry
        point must have a single argument, the ``bot``.

        Parameters
        ------------
        name: :class:`str`
            The extension name to load. It must be dot separated like
            regular Python imports if accessing a sub-module. e.g.
            ``foo.test`` if you want to import ``foo/test.py``.

        Raises
        --------
        ExtensionNotFound
            The extension could not be imported.
        ExtensionAlreadyLoaded
            The extension is already loaded.
        NoEntryPointError
            The extension does not have a setup function.
        ExtensionFailed
            The extension or its setup function had an execution error.
        """

        if name in self.__extensions:
            raise errors.ExtensionAlreadyLoaded(name)

        spec = importlib.util.find_spec(name)
        if spec is None:
            raise errors.ExtensionNotFound(name)

        self._load_from_module_spec(spec, name)

    def unload_extension(self, name):
        """Unloads an extension.

        When the extension is unloaded, all commands, listeners, and cogs are
        removed from the bot and the module is un-imported.
        The extension can provide an optional global function, ``teardown``,
        to do miscellaneous clean-up if necessary. This function takes a single
        parameter, the ``bot``, similar to ``setup`` from
        :meth:`~.Bot.load_extension`.

        Parameters
        ------------
        name: :class:`str`
            The extension name to unload. It must be dot separated like
            regular Python imports if accessing a sub-module. e.g.
            ``foo.test`` if you want to import ``foo/test.py``.

        Raises
        -------
        ExtensionNotLoaded
            The extension was not loaded.
        """

        lib = self.__extensions.get(name)
        if lib is None:
            raise errors.ExtensionNotLoaded(name)

        self._remove_module_references(lib.__name__)
        self._call_module_finalizers(lib, name)

    def reload_extension(self, name):
        """Atomically reloads an extension.

        This replaces the extension with the same extension, only refreshed. This is
        equivalent to a :meth:`unload_extension` followed by a :meth:`load_extension`
        except done in an atomic way. That is, if an operation fails mid-reload then
        the bot will roll-back to the prior working state.

        Parameters
        ------------
        name: :class:`str`
            The extension name to reload. It must be dot separated like
            regular Python imports if accessing a sub-module. e.g.
            ``foo.test`` if you want to import ``foo/test.py``.

        Raises
        -------
        ExtensionNotLoaded
            The extension was not loaded.
        ExtensionNotFound
            The extension could not be imported.
        NoEntryPointError
            The extension does not have a setup function.
        ExtensionFailed
            The extension setup function had an execution error.
        """

        lib = self.__extensions.get(name)
        if lib is None:
            raise errors.ExtensionNotLoaded(name)

        # get the previous module states from sys modules
        modules = {
            name: module
            for name, module in sys.modules.items()
            if _is_submodule(lib.__name__, name)
        }

        try:
            # Unload and then load the module...
            self._remove_module_references(lib.__name__)
            self._call_module_finalizers(lib, name)
            self.load_extension(name)
        except Exception:
            # if the load failed, the remnants should have been
            # cleaned from the load_extension function call
            # so let's load it from our old compiled library.
            lib.setup(self)
            self.__extensions[name] = lib

            # revert sys.modules back to normal and raise back to caller
            sys.modules.update(modules)
            raise
