import importlib
from typing import Tuple, Set, Type

from .meta import __meta__, MessageMeta, config


class InvalidMessage(Exception):
    pass


class BaseField:
    _type_name = ""

    def __init__(self, name=None):
        self._name = name

    def __set__(self, instance, value):
        instance.__dict__[self._name] = value

    def __str__(self):
        return f"{self._type_name} {self._name}"


class StringField(BaseField):
    _type_name = "string"


class Int32Field(BaseField):
    _type_name = "int32"


class Int64Field(BaseField):
    _type_name = "int64"


class BooleanField(BaseField):
    _type_name = "bool"


class BytesField(BaseField):
    _type_name = "bytes"


class EmptyFile:
    pass


class ReferenceField(BaseField):
    def __init__(self,
                 key_type: Type[BaseField],
                 value_type: Type[BaseField] = None):
        self._key_type = key_type
        self._type_name = key_type._type_name

        if value_type:
            self._value_type = value_type
            self._value_type_name = value_type._type_name
        else:
            self._value_type = EmptyFile

        super().__init__()


class ListField(ReferenceField):
    def __str__(self):
        return f"repeated {super().__str__()}"


class MapField(ReferenceField):
    def __str__(self):
        return f"map<{self._type_name}, {self._value_type_name}> {self._name}"


class DeclarativeMeta(type):
    def __new__(cls, clsname: str, bases: Tuple, clsdict: dict):
        if clsname != "Message":
            file_name = (clsdict.get("__filename__", clsname)
                         or clsname).lower()
            clsdict["__filename__"] = file_name
            clsdict["__meta__"] = set()
            clsdict["_type_name"] = clsname

            message_meta = MessageMeta(name=clsname, fields=[])
            for key, value in clsdict.items():
                if isinstance(value, BaseField):
                    value._name = key
                    message_meta.fields.append(value)
                    if isinstance(value, ReferenceField):
                        if issubclass(value._key_type, Message):
                            if value._key_type.__filename__ != file_name:
                                __meta__[file_name]['import_files'].add(
                                    value._key_type.__filename__)

                        if issubclass(value._value_type, Message):
                            if value._value_type.__filename__ != file_name:
                                __meta__[file_name]['import_files'].add(
                                    value._value_type.__filename__)
                    clsdict["__meta__"].add(key)

            __meta__[file_name]['messages'].append(message_meta)
        return super().__new__(cls, clsname, bases, clsdict)


class Message(BaseField, metaclass=DeclarativeMeta):
    __filename__ = ""
    _type_name = ""
    _message = None

    __meta__: Set[str] = None

    def __init__(self, grpc_message: object = None, **kwargs):
        if grpc_message:
            object.__setattr__(self, "_message", grpc_message)
        else:
            gpr_message_module = importlib.import_module(
                f".{self.__filename__}_pb2", config.DEFAULT_TEMPLATE_PATH)
            gRPCMessageClass = getattr(gpr_message_module,
                                       f"{self._type_name}")
            # TODO Handle map field
            for key, item in kwargs.items():
                if isinstance(item, list):
                    for index, value in enumerate(item):
                        if isinstance(value, Message):
                            item[index] = value._message
                elif isinstance(item, Message):
                    kwargs[key] = item._message

            object.__setattr__(self, "_message", gRPCMessageClass(**kwargs))

        super().__init__()

    def __setattr__(self, key, value):
        if key in object.__getattribute__(self, "__meta__"):
            setattr(self._message, key, value)
        else:
            object.__setattr__(self, key, value)

    def __getattribute__(self, item):
        if item in object.__getattribute__(self, "__meta__"):
            return getattr(object.__getattribute__(self, "_message"), item)
        else:
            return object.__getattribute__(self, item)
