from typing import Tuple, List, Type

from .meta import __meta__, MessageMeta


class BaseField:
    _type_name = ""

    def __init__(self, name=None):
        self._name = name

    def __set__(self, instance, value):
        instance.__dict__[self._name] = value

    def __get__(self, instance, owner):
        if not instance:
            return f"{self._type_name} {self._name}"
        else:
            return instance.__dict__.get(self._name)


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
    def __get__(self, instance, owner):
        if not instance:
            return f"repeated {self._type_name} {self._name}"
        else:
            return instance.__dict__.get(self._name)


class MapField(ReferenceField):
    def __get__(self, instance, owner):
        if not instance:
            return f"map<{self._type_name}, {self._value_type_name}> {self._name}"
        else:
            return instance.__dict__.get(self._name)


class DeclarativeMeta(type):
    def __new__(cls, clsname: str, bases: Tuple, clsdict: dict):
        if bases:
            file_name = (clsdict.get("__filename__", clsname)
                         or clsname).lower()
            clsdict["__filename__"] = file_name
            clsdict["__meta__"] = []
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
                    clsdict["__meta__"].append(key)

            __meta__[file_name]['messages'].append(message_meta)
        return super().__new__(cls, clsname, bases, clsdict)


class Message(BaseField, metaclass=DeclarativeMeta):
    __filename__ = ""
    _type_name = ""

    __meta__: List[str] = None

    def __init__(self, **kwargs):
        for key in self.__meta__:
            setattr(self, key, kwargs.get(key))
        super().__init__()

    def to_grpc(self) -> dict:
        return {key: getattr(self, key) for key in self.__meta__}
