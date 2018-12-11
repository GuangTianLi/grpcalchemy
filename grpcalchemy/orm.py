from typing import Tuple, List

from .meta import __meta__, MessageMeta
from .fields import BaseField, ReferenceField


class DeclarativeMeta(type):
    def __new__(cls, clsname: str, bases: Tuple, clsdict: dict):
        if bases:
            file_name = (clsdict.get("__filename__", clsname)
                         or clsname).lower()
            clsdict["__filename__"] = file_name
            clsdict["__meta__"] = []
            message_meta = MessageMeta(name=clsname, fields=[])
            for key, value in clsdict.items():
                if isinstance(value, BaseField):
                    value.name = key
                    message_meta.fields.append(value)
                    if isinstance(value, ReferenceField):

                        if issubclass(value.key_type, Message):
                            if value.key_type.__filename__ != file_name:
                                __meta__[file_name]['import_files'].add(
                                    value.key_type.file_name)

                        if issubclass(value.value_type, Message):
                            if value.value_type.__filename__ != file_name:
                                __meta__[file_name]['import_files'].add(
                                    value.value_type.file_name)
                    clsdict["__meta__"].append(key)

            __meta__[file_name]['messages'].append(message_meta)
        return super().__new__(cls, clsname, bases, clsdict)


class Message(metaclass=DeclarativeMeta):
    __filename__ = ""

    __meta__: List[str] = None

    def __init__(self, **kwargs):
        for key in self.__meta__:
            setattr(self, key, kwargs.get(key))

    def to_grpc(self) -> dict:
        return {key: getattr(self, key) for key in self.__meta__}

    def __str__(self):
        return f"{self.__name__}"
