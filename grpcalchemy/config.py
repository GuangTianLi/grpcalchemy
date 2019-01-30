import errno
import json
import os
import sys
from typing import Dict, Type, Union


def import_string(import_name: str) -> Type:
    """Imports an object based on a string.  This is useful if you want to
    use import paths as endpoints or something similar.  An import path can
    be specified either in dotted notation (``xml.sax.saxutils.escape``)
    or with a colon as object delimiter (``xml.sax.saxutils:escape``).

    If `silent` is True the return value will be `None` if the import fails.

    :param str import_name: the dotted name for the object to import.
    :return Type: imported object
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
    def __init__(self, root_path: str = "", defaults: Dict = None):
        super().__init__(defaults or {})
        self.root_path = root_path

    def from_json(self, filename: str, silent: bool = False) -> bool:
        """Updates the values in the config from a JSON file. This function
        behaves as if the JSON object was a dictionary and passed to the
        :meth:`from_mapping` function.

        :param str filename: the filename of the JSON file.  This can either be an
                         absolute filename or a filename relative to the
                         root path.
        :param bool silent: set to ``True`` if you want silent failure for missing
                       files.

        .. versionadded:: 0.1.6
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

        .. versionadded:: 0.1.6
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

            app.config.from_object('yourapplication.default_config')
            from yourapplication import default_config
            app.config.from_object(default_config)

        You should not use this function to load the actual configuration but
        rather configuration defaults.  The actual config should be loaded
        with :meth:`from_object` and ideally from a location not within the
        package because the package might be installed system wide. If the
        ``__json_file__`` is an attribute of the ``object`` class, the actual
        config will also be loaded with :meth:`from_json`.

        using :meth:`from_object`.

        :param obj: an import name or object

        .. versionadded:: 0.1.5
        """
        if isinstance(obj, str):
            obj = import_string(obj)
        for key in dir(obj):
            if key.isupper():
                self[key] = getattr(obj, key)
        load_from_json = getattr(obj, "__json_file__", None)
        return self.from_json(load_from_json) if load_from_json else True


default_config = Config(
    defaults=dict(
        TEMPLATE_PATH="protos",
        MAX_WORKERS=10,
    ))
