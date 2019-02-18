import asyncio
import errno
import json
import os
import sys
from typing import Any, Callable, Coroutine, Dict, List, Type, Union


def import_string(import_name: str) -> Type:
    """Imports an object based on a string.  This is useful if you want to
    use import paths as endpoints or something similar.  An import path can
    be specified either in dotted notation (``xml.sax.saxutils.escape``)
    or with a colon as object delimiter (``xml.sax.saxutils:escape``).

    If `silent` is True the return value will be `None` if the import fails.

    :param import_name: the dotted name for the object to import.
    :return: imported object
    """
    # force the import name to automatically convert to strings
    # __import__ is not able to handle unicode strings in the fromlist
    # if the module is a package
    import_name = import_name.replace(':', '.')

    try:
        __import__(import_name)
    except ImportError:
        if '.' not in import_name:
            raise
    else:
        return sys.modules[import_name]  # pyre-ignore

    module_name, obj_name = import_name.rsplit('.', 1)
    try:
        module = __import__(module_name, fromlist=[obj_name])
    except ImportError:
        # support importing modules not yet set up by the parent module
        # (or package for that matter)
        module = import_string(module_name)

    return getattr(module, obj_name)


class Config(dict):
    """Init the :any:`Config` with the Priority。

    * Priority: *env > local config file > remote center > project config*

    :param obj: Raw Object
    :type obj: Union[str, Type]
    :param sync_access_config_list:
    :type sync_access_config_list: List[Callable[[], Dict]]
    :param async_access_config_list:
    :type async_access_config_list: List[Callable[[], Coroutine[Any, Any, Dict]]]
    :param str root_path:
    :param Dict defaults: defaults value to init the dict
    """

    def __init__(self,
                 obj: Union[str, Type],
                 sync_access_config_list: List[Callable[[], Dict]] = None,
                 async_access_config_list: List[
                     Callable[[], Coroutine[Any, Any, Dict]]] = None,
                 root_path: str = "",
                 defaults: Dict = None):
        super().__init__(defaults or {})
        self.root_path = root_path
        self.sync_access_config_list = sync_access_config_list or []
        self.async_access_config_list = async_access_config_list or []

        #: Priority: env > local config file > remote center > project config

        #: project config
        self.from_object(obj)

        #: remote center
        #: Sync
        if self.sync_access_config_list:
            self.from_remote_center()

        # Async
        loop = asyncio.get_event_loop()
        if self.async_access_config_list:
            loop.run_until_complete(self.from_remote_center_async())

        #: local config file
        config_file = self.get("CONFIG_FILE", "")
        if config_file:
            self.from_json(config_file)

        #: env
        env_prefix = self.get("ENV_PREFIX", "")
        if env_prefix:
            self.from_env(prefix=env_prefix)

    def from_json(self, filename: str, silent: bool = False) -> bool:
        """Updates the values in the config from a JSON file. This function
        behaves as if the JSON object was a dictionary and passed to the
        :meth:`from_mapping` function.

        :param str filename: the filename of the JSON file. This can either be
                            an absolute filename or a filename relative to the
                            root path.
        :param bool silent: set to ``True`` if you want silent failure for missing
                       files.

        """
        filename = os.path.join(self.root_path, filename)

        try:
            with open(filename) as json_file:
                obj = json.loads(json_file.read())
        except IOError as e:
            if silent and e.errno in (errno.ENOENT, errno.EISDIR):
                return False
            e.strerror = 'Unable to load configuration file (%s)' % e.strerror
            raise
        return self.from_mapping(obj)

    def from_mapping(self, *mapping, **kwargs) -> bool:
        """Updates the config like :meth:`update` ignoring items with non-upper
        keys.

        """
        mappings = []
        if len(mapping) == 1:
            if hasattr(mapping[0], 'items'):
                mappings.append(mapping[0].items())
            else:
                mappings.append(mapping[0])
        elif len(mapping) > 1:
            raise TypeError('expected at most 1 positional argument, got %d' %
                            len(mapping))
        mappings.append(kwargs.items())
        for mapping in mappings:
            for (key, value) in mapping:
                if key.isupper():
                    self[key] = value
        return True

    def from_object(self, obj: Union[str, Type]) -> bool:
        """Updates the values from the given object.  An object can be of one
        of the following two types:

        -   a string: in this case the object with that name will be imported
        -   an actual object reference: that object is used directly

        Objects are usually either modules or classes. :meth:`from_object`
        loads only the uppercase attributes of the module/class. A ``dict``
        object will not work with :meth:`from_object` because the keys of a
        ``dict`` are not attributes of the ``dict`` class.

        Example of module-based configuration::

            config = Config()
            config.from_object('yourapplication.default_config')
            from yourapplication import default_config
            config.from_object(default_config)

        You should not use this function to load the actual configuration but
        rather configuration defaults.  The actual config should be loaded
        with :meth:`from_object` and ideally from a location not within the
        package because the package might be installed system wide. If the
        ``__json_file__`` is an attribute of the ``object`` class, the actual
        config will also be loaded with :meth:`from_json`.

        using :meth:`from_object`.

        :param obj: an import name or object
        :type obj: Union[str, Type]

        """
        if isinstance(obj, str):
            obj = import_string(obj)
        for key in dir(obj):
            if key.isupper():
                self[key] = getattr(obj, key)
        return True

    def from_env(self, prefix: str) -> bool:
        """Updates the values in the config from the environment variable.

        :param str prefix: The prefix to construct the full environment variable
                        with the key.

        """
        for key, value in self.items():
            self[key] = os.getenv(f"{prefix}{key}", value)
        return True

    def from_remote_center(self) -> bool:
        """Updates the values in the config from the remote center.


        """
        for remote_center in self.sync_access_config_list:
            self.from_mapping(remote_center())
        return True

    async def from_remote_center_async(self) -> bool:
        """Async updates the values in the config from the remote center.


        """
        for remote_center in self.async_access_config_list:
            self.from_mapping(await remote_center())
        return True


default_config = Config(
    obj=object,
    defaults=dict(
        TEMPLATE_PATH="protos",
        MAX_WORKERS=10,
        OPTIONS=(),
        MAXIMUM_CONCURRENT_RPCS=None,
    ))
