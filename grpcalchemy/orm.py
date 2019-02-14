import importlib
from itertools import chain
from threading import RLock
from typing import Any, Dict, Iterator, List, Tuple, Type

from google.protobuf.json_format import MessageToDict, MessageToJson
from google.protobuf.message import Message as GeneratedProtocolMessageType

from .config import default_config
from .meta import MessageMeta, __meta__

# sentinel
_missing = object()


class BaseField:
    _type_name = ""

    def __init__(self, name=None):
        self._name = name
        self.lock = RLock()

    def __get__(self, obj: Any, type: Type) -> Any:
        if obj is None:
            return self
        with self.lock:
            value = obj.__dict__.get(self._name, _missing)
            if value is _missing:
                value = getattr(obj._message, self._name)
                obj.__dict__[self._name] = value
            return value

    def __set__(self, instance, value: Any) -> None:
        with self.lock:
            setattr(instance._message, self._name, value)
            instance.__dict__[self._name] = value

    def __str__(self):
        return f"{self._type_name} {self._name}"


class StringField(BaseField):
    _type_name = "string"

    def __get__(self, obj: Any, type: Type) -> str:
        return super().__get__(obj, type)

    def __set__(self, instance, value: str) -> None:
        super().__set__(instance, value)


class Int32Field(BaseField):
    _type_name = "int32"

    def __get__(self, obj: Any, type: Type) -> int:
        return super().__get__(obj, type)

    def __set__(self, instance, value: int) -> None:
        super().__set__(instance, value)


class FloatField(BaseField):
    _type_name = "float"

    def __get__(self, obj: Any, type: Type) -> float:
        return super().__get__(obj, type)

    def __set__(self, instance, value: float) -> None:
        super().__set__(instance, value)


class DoubleField(BaseField):
    _type_name = "double"

    def __get__(self, obj: Any, type: Type) -> float:
        return super().__get__(obj, type)

    def __set__(self, instance, value: float) -> None:
        super().__set__(instance, value)


class Int64Field(BaseField):
    _type_name = "int64"

    def __get__(self, obj: Any, type: Type) -> int:
        return super().__get__(obj, type)

    def __set__(self, instance, value: int) -> None:
        super().__set__(instance, value)


class BooleanField(BaseField):
    _type_name = "bool"

    def __get__(self, obj: Any, type: Type) -> bool:
        return super().__get__(obj, type)

    def __set__(self, instance, value: bool) -> None:
        super().__set__(instance, value)


class BytesField(BaseField):
    _type_name = "bytes"

    def __get__(self, obj: Any, type: Type) -> bytes:
        return super().__get__(obj, type)

    def __set__(self, instance, value: bytes) -> None:
        super().__set__(instance, value)


class ReferenceField(BaseField):
    def __init__(self, key_type: Type[BaseField]):
        self._key_type = key_type
        self._type_name = key_type._type_name

        super().__init__()


class ListField(ReferenceField):
    def __get__(self, obj: Any, type: Type) -> List[Any]:
        return super().__get__(obj, type)

    def __str__(self):
        return f"repeated {super().__str__()}"

    def __set__(self, instance, value: List) -> None:
        super().__set__(instance, value)


class MapField(ReferenceField):
    def __init__(self, key_type: Type[BaseField], value_type: Type[BaseField]):
        super().__init__(key_type)
        self._value_type = value_type
        self._value_type_name = value_type._type_name

    def __get__(self, obj: Any, type: Type) -> Dict:
        return super().__get__(obj, type)

    def __set__(self, instance, value: Dict) -> None:
        super().__set__(instance, value)

    def __str__(self):
        return f"map<{self._type_name}, {self._value_type_name}> {self._name}"


class DeclarativeMeta(type):
    def __new__(cls, clsname: str, bases: Tuple, clsdict: dict):
        if bases[0] is not BaseField:
            file_name = clsdict.get("__filename__", clsname).lower()
            clsdict["__filename__"] = file_name
            clsdict["__meta__"]: Dict[str, BaseField] = {}
            clsdict["_type_name"] = clsname

            message_meta = MessageMeta(name=clsname, fields=[])

            def iter_base_meta() -> Iterator:
                for base in bases:
                    if base.__meta__:
                        yield from base.__meta__.items()

            for key, value in chain(clsdict.items(), iter_base_meta()):
                if isinstance(value, BaseField):
                    value._name = key
                    message_meta.fields.append(value)
                    if isinstance(value, ReferenceField):
                        if issubclass(value._key_type, Message):
                            if value._key_type.__filename__ != file_name:
                                __meta__[file_name].import_files.add(
                                    value._key_type.__filename__)
                        if isinstance(value, MapField):
                            if issubclass(value._value_type, Message):
                                if value._value_type.__filename__ != file_name:
                                    __meta__[file_name].import_files.add(
                                        value._value_type.__filename__)
                    clsdict["__meta__"][key] = value
            __meta__[file_name].messages.append(message_meta)
        return super().__new__(cls, clsname, bases, clsdict)


class Message(BaseField, metaclass=DeclarativeMeta):
    __filename__ = ""
    _message: GeneratedProtocolMessageType = None
    __meta__: Dict[str, BaseField] = {}

    def __init__(self, **kwargs):
        gpr_message_module = importlib.import_module(
            f".{self.__filename__}_pb2", default_config["TEMPLATE_PATH"])
        gRPCMessageClass = getattr(gpr_message_module, f"{self._type_name}")
        for key, item in kwargs.items():
            if isinstance(item, list):
                for index, value in enumerate(item):
                    if isinstance(value, Message):
                        item[index] = value._message
            elif isinstance(item, Message):
                kwargs[key] = item._message
            elif isinstance(item, dict):
                for key, tmp in item.items():
                    if isinstance(tmp, Message):
                        item[key] = tmp._message
        self._message = gRPCMessageClass(**kwargs)
        super().__init__()

    def init_grpc_message(self, grpc_message: GeneratedProtocolMessageType):
        self._message = grpc_message

    def message_to_dict(self,
                        including_default_value_fields: bool = False,
                        preserving_proto_field_name: bool = False,
                        use_integers_for_enums: bool = False) -> dict:
        """Converts protobuf message to a dictionary.

        When the dictionary is encoded to JSON, it conforms to proto3 JSON spec.

        Args:
          including_default_value_fields: If True, singular primitive fields,
              repeated fields, and map fields will always be serialized.  If
              False, only serialize non-empty fields.  Singular message fields
              and oneof fields are not affected by this option.
          preserving_proto_field_name: If True, use the original proto field
              names as defined in the .proto file. If False, convert the field
              names to lowerCamelCase.
          use_integers_for_enums: If true, print integers instead of enum names.

        Returns:
          A dict representation of the protocol buffer message.

        #: .. versionadded:: 0.1.7
        """
        return MessageToDict(
            self._message,
            including_default_value_fields=including_default_value_fields,
            preserving_proto_field_name=preserving_proto_field_name,
            use_integers_for_enums=use_integers_for_enums)

    def message_to_json(self,
                        including_default_value_fields: bool = False,
                        preserving_proto_field_name: bool = False,
                        indent: int = 2,
                        sort_keys: bool = False,
                        use_integers_for_enums: bool = False) -> str:
        """Converts protobuf message to JSON format.

          Args:
            including_default_value_fields: If True, singular primitive fields,
                repeated fields, and map fields will always be serialized.  If
                False, only serialize non-empty fields.  Singular message fields
                and oneof fields are not affected by this option.
            preserving_proto_field_name: If True, use the original proto field
                names as defined in the .proto file. If False, convert the field
                names to lowerCamelCase.
            indent: The JSON object will be pretty-printed with this indent level.
                An indent level of 0 or negative will only insert newlines.
            sort_keys: If True, then the output will be sorted by field names.
            use_integers_for_enums: If true, print integers instead of enum names.

          Returns:
            A string containing the JSON formatted protocol buffer message.

        #: .. versionadded:: 0.1.7
        """
        return MessageToJson(
            self._message,
            including_default_value_fields=including_default_value_fields,
            preserving_proto_field_name=preserving_proto_field_name,
            indent=indent,
            sort_keys=sort_keys,
            use_integers_for_enums=use_integers_for_enums)
