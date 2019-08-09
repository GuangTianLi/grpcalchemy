import importlib
from itertools import chain
from threading import RLock
from typing import Dict, Iterator, List, Tuple, Type, Generic, TypeVar

from google.protobuf.json_format import MessageToDict, MessageToJson
from google.protobuf.message import Message as GeneratedProtocolMessageType

from .config import default_config
from .meta import MessageMeta, __meta__

# sentinel
_missing = object()


class DeclarativeMeta(type):
    def __new__(cls, clsname: str, bases: Tuple, clsdict: dict):
        if bases:
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
                                    value._key_type.__filename__
                                )
                        if isinstance(value, MapField):
                            if issubclass(value._value_type, Message):
                                if value._value_type.__filename__ != file_name:
                                    __meta__[file_name].import_files.add(
                                        value._value_type.__filename__
                                    )
                    clsdict["__meta__"][key] = value
            __meta__[file_name].messages.append(message_meta)
        return super().__new__(cls, clsname, bases, clsdict)


class Message(metaclass=DeclarativeMeta):
    _type_name = ""
    _name = ""
    __filename__ = ""
    _message: GeneratedProtocolMessageType = None
    __meta__: Dict[str, "BaseField"] = {}

    def __init__(__message_self__, **kwargs):
        # Uses something other than `self` the first arg to allow "self" as a settable attribute
        gpr_message_module = importlib.import_module(
            f".{__message_self__.__filename__}_pb2", default_config["TEMPLATE_PATH"]
        )
        gRPCMessageClass = getattr(gpr_message_module, f"{__message_self__._type_name}")
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
        __message_self__._message = gRPCMessageClass(**kwargs)
        super().__init__()

    def init_grpc_message(self, grpc_message: GeneratedProtocolMessageType):
        self._message = grpc_message

    def message_to_dict(
        self,
        including_default_value_fields: bool = False,
        preserving_proto_field_name: bool = False,
        use_integers_for_enums: bool = False,
    ) -> dict:
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
            use_integers_for_enums=use_integers_for_enums,
        )

    def message_to_json(
        self,
        including_default_value_fields: bool = False,
        preserving_proto_field_name: bool = False,
        indent: int = 2,
        sort_keys: bool = False,
        use_integers_for_enums: bool = False,
    ) -> str:
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
            use_integers_for_enums=use_integers_for_enums,
        )

    def __str__(self):
        return f"{self._type_name} {self._name}"


FieldType = TypeVar("FieldType")


class BaseField(Generic[FieldType]):
    _type_name = ""
    _name = ""

    def __init__(self):
        self.lock = RLock()

    def __get__(self, obj: Message, type: Type) -> FieldType:
        if obj is None:
            return self  # type: ignore
        with self.lock:
            value = obj.__dict__.get(self._name, _missing)
            if value is _missing:
                value = getattr(obj._message, self._name)
                obj.__dict__[self._name] = value
            return value

    def __set__(self, instance: Message, value: FieldType) -> None:
        with self.lock:
            setattr(instance._message, self._name, value)
            instance.__dict__[self._name] = value

    def __str__(self):
        return f"{self._type_name} {self._name}"


class StringField(BaseField[str]):
    _type_name = "string"


class Int32Field(BaseField[int]):
    _type_name = "int32"


class FloatField(BaseField[float]):
    _type_name = "float"


class DoubleField(BaseField[float]):
    _type_name = "double"


class Int64Field(BaseField[int]):
    _type_name = "int64"


class BooleanField(BaseField[bool]):
    _type_name = "bool"


class BytesField(BaseField[bytes]):
    _type_name = "bytes"


ReferenceFieldType = TypeVar("ReferenceFieldType", bound=Type[Message])
ReferenceKeyFieldType = TypeVar("ReferenceKeyFieldType", bound=Type[BaseField])
ReferenceValueFieldType = TypeVar(
    "ReferenceValueFieldType", Type[Message], Type[BaseField]
)


class ReferenceField(BaseField[ReferenceFieldType]):
    def __init__(self, key_type: ReferenceFieldType):
        self._key_type = key_type
        self._type_name = key_type._type_name

        super().__init__()


class ListField(ReferenceField[List[ReferenceValueFieldType]]):
    def __str__(self):
        return f"repeated {super().__str__()}"


class MapField(ReferenceField[Dict[ReferenceKeyFieldType, ReferenceValueFieldType]]):
    def __init__(
        self, key_type: ReferenceKeyFieldType, value_type: ReferenceValueFieldType
    ):
        super().__init__(key_type)
        self._value_type = value_type
        self._value_type_name = value_type._type_name

    def __str__(self):
        return f"map<{self._type_name}, {self._value_type_name}> {self._name}"
