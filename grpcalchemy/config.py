import asyncio
import errno
import json
import logging
import os
import sys
from collections import defaultdict
from itertools import chain
from threading import RLock
from typing import (
    Any,
    Callable,
    Coroutine,
    DefaultDict,
    Dict,
    KeysView,
    List,
    Mapping,
    Optional,
    Set,
    Tuple,
    Type,
    Union,
)

import yaml

_miss = lambda x: x


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


class ConfigMeta:
    def __init__(self, default=None):
        self.value_type: Callable[[Any], Any] = _miss
        self.project_value = default
        self.remote_center_value = None
        self.config_file_value = None
        self.env_value = None

    def get_config(self) -> Any:
        if self.env_value is not None:
            return self.env_value
        elif self.config_file_value is not None:
            return self.config_file_value
        elif self.remote_center_value is not None:
            return self.remote_center_value
        else:
            return self.project_value

    def get(self) -> Any:
        return self.value_type(self.get_config())

    def set(self, priority: int, value: Any) -> bool:
        if priority == 0:
            self.project_value = value
        elif priority == 1:
            self.remote_center_value = value
        elif priority == 2:
            self.config_file_value = value
        else:
            self.env_value = value
        return True


class Config(dict):
    """Init the :any:`Config` with the Priority。

    * Priority: *env > local config file > remote center > project config*

    Example of module-based configuration::

        config = Config('yourapplication.default_config')
        from yourapplication import default_config
        config = Config(default_config)

    :param obj: a string or an actual object
        -   a string: in this case the object with that name will be imported
        -   an actual object reference: that object is used directly
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
                 sync_access_config_list: List[Callable[[Dict], Dict]] = None,
                 async_access_config_list: List[
                     Callable[[Dict], Coroutine[Any, Any, Dict]]] = None,
                 root_path: str = "",
                 defaults: Optional[dict] = None):
        self.lock = RLock()
        self.config_meta: DefaultDict[str, ConfigMeta] = defaultdict(
            ConfigMeta)
        self.root_path = root_path
        self.sync_access_config_list = sync_access_config_list or []
        self.async_access_config_list = async_access_config_list or []

        self.from_mapping(defaults or {}, priority=0)
        #: Priority: env > local config file > remote center > project config

        #: project config
        self.from_object(obj)

        #: env
        env_prefix = self.get("ENV_PREFIX", "")
        if env_prefix:
            self.from_env(prefix=env_prefix)

        #: local config file
        config_file = self.get("CONFIG_FILE", "")
        if config_file:
            self.from_file(config_file)

        #: remote center
        if self.get("ENABLE_CONFIG_LIST", False):
            #: Sync
            if self.sync_access_config_list:
                self.from_sync_access_config_list()

            # Async
            loop = asyncio.get_event_loop()
            if self.async_access_config_list:
                loop.run_until_complete(self.from_async_access_config_list())
        super().__init__(**self)

    def from_file(self, filename: str, silent: bool = False,
                  priority: int = 2) -> bool:
        """Updates the values in the config from a JSON file or a YAML file.
        This function behaves as if the JSON or YAML object was a dictionary
        and passed to the :meth:`from_mapping` function.

        :param str filename: the filename of the JSON or YAML file. This can
                            either be an absolute filename or a filename relative
                            to the root path.
        :param bool silent: set to ``True`` if you want silent failure for missing
                       files.

        """
        filename = os.path.join(self.root_path, filename)
        try_json_file = 'json' in filename

        try:
            with open(filename) as f:
                if try_json_file:
                    obj = json.load(f)
                else:
                    obj = yaml.safe_load(f) or {}
        except IOError as e:
            if silent and e.errno in (errno.ENOENT, errno.EISDIR):
                return False
            e.strerror = 'Unable to load configuration file (%s)' % e.strerror
            raise
        logging.info(f'Loaded configuration file: {filename}')
        return self.from_mapping(obj, priority=priority)

    def from_mapping(self, *mapping, priority, **kwargs) -> bool:
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
                    self._set_value(key, value, priority=priority)
        return True

    def from_object(self, obj: Union[str, Type], priority: int = 0) -> bool:
        """Updates the values from the given object.  An object can be of one
        of the following two types:

        -   a string: in this case the object with that name will be imported
        -   an actual object reference: that object is used directly

        Objects are usually either modules or classes. :meth:`from_object`
        loads only the uppercase attributes of the module/class. A ``dict``
        object will not work with :meth:`from_object` because the keys of a
        ``dict`` are not attributes of the ``dict`` class.

        Example of module-based configuration::

            config = Config(obj=object)
            config.from_object('yourapplication.default_config')
            from yourapplication import default_config
            config.from_object(default_config)

        You should not use this function to load the actual configuration but
        rather configuration defaults.  The actual config should be loaded
        with :meth:`from_object` and ideally from a location not within the
        package because the package might be installed system wide.

        :param obj: a string or an actual object
        :type obj: Union[str, Type]

        """
        if isinstance(obj, str):
            obj = import_string(obj)()

        for key in dir(obj):
            if key.isupper():
                obj_value = getattr(obj, key)
                self._set_value(
                    key,
                    obj_value,
                    priority=priority,
                    value_type=type(obj_value))  # pyre-ignore
        return True

    def from_env(self, prefix: str, priority: int = 3) -> bool:
        """Updates the values in the config from the environment variable.

        :param str prefix: The prefix to construct the full environment variable
                        with the key.

        """
        for key, value in self.items():
            env_value = os.getenv(f"{prefix}{key}")
            if env_value is not None:
                self._set_value(key, env_value, priority=priority)
        return True

    def from_sync_access_config_list(self, priority: int = 1) -> bool:
        """Updates the values in the config from the sync_access_config_list.


        """
        for remote_center in self.sync_access_config_list:
            self.from_mapping(remote_center(self), priority=priority)
        return True

    async def from_async_access_config_list(self, priority: int = 1) -> bool:
        """Async updates the values in the config from the async_access_config_list.

        """
        for remote_center in self.async_access_config_list:
            self.from_mapping(await remote_center(self), priority=priority)
        return True

    def _set_value(self,
                   key: str,
                   value: Any,
                   priority: int,
                   value_type: Callable[[Any], Any] = _miss):
        """ Set self[key] to value. """
        with self.lock:
            if value_type is not _miss:
                self.config_meta[key].value_type = value_type
            self.config_meta[key].set(priority=priority, value=value)

    def __getitem__(self, key: str) -> Any:
        """ x.__getitem__(y) <==> x[y] """
        with self.lock:
            if key not in self.config_meta:
                raise KeyError(key)
            return self.config_meta[key].get()

    def items(self) -> Set[Tuple[Any, Any]]:
        config_meta_items = set()
        for key, config_meta in self.config_meta.items():
            config_meta_items.add((key, config_meta.get()))
        return config_meta_items

    def keys(self) -> KeysView[Any]:
        return self.config_meta.keys()

    def __contains__(self, key: object) -> bool:
        return key in self.config_meta

    def __iter__(self):
        return iter(self.config_meta)

    def __len__(self) -> int:
        return len(self.config_meta)

    def __setitem__(self, k, v) -> None:
        self._set_value(k, v, priority=3)

    def update(self, __m: Mapping, **F):
        for key, value in chain(__m.items(), F):
            self._set_value(key, value, priority=3)

    def get(self, key: str, default=None):
        with self.lock:
            return self.config_meta.get(key, ConfigMeta(default=default)).get()


default_config = dict(
    TEMPLATE_PATH="protos",
    MAX_WORKERS=10,
    OPTIONS=(),
    MAXIMUM_CONCURRENT_RPCS=None,
)
