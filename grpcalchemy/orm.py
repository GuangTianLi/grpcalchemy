import importlib
from itertools import chain
from threading import RLock
from typing import Dict, Iterator, List, Tuple, Type, Generic, TypeVar, TYPE_CHECKING

from google.protobuf.json_format import MessageToDict, MessageToJson
from google.protobuf.message import Message as GeneratedProtocolMessageType

from .config import get_current_proto_path
from .meta import MessageMeta, __meta__

# sentinel
_missing = object()


class DeclarativeMeta(type):
    def __new__(cls, clsname: str, bases: Tuple, clsdict: dict):
        if bases:
            file_name = clsdict.get("__filename__", clsname).lower()
            clsdict["__filename__"] = file_name
            clsdict["__meta__"] = {}
            clsdict["__type_name__"] = clsname

            message_meta = MessageMeta(name=clsname, fields=[])

            def iter_base_meta() -> Iterator:
                for base in bases:
                    if base.__meta__:
                        yield from base.__meta__.items()

            for key, field in chain(clsdict.items(), iter_base_meta()):
                if isinstance(field, BaseField):
                    field.__field_name__ = key
                    message_meta.fields.append(field)
                    if isinstance(field, (ReferenceField, ListField, MapField)):
                        if issubclass(field.__key_type__, Message):
                            if field.__key_type__.__filename__ != file_name:
                                __meta__[file_name].import_files.add(
                                    field.__key_type__.__filename__
                                )
                        if isinstance(field, MapField):
                            if issubclass(field.__value_type__, Message):
                                if field.__value_type__.__filename__ != file_name:
                                    __meta__[file_name].import_files.add(
                                        field.__value_type__.__filename__
                                    )
                    clsdict["__meta__"][key] = field
            __meta__[file_name].messages.append(message_meta)
        return super().__new__(cls, clsname, bases, clsdict)


class Message(metaclass=DeclarativeMeta):
    __meta__: Dict[str, "BaseField"] = {}
    __filename__: str = ""
    __message__: GeneratedProtocolMessageType

    if TYPE_CHECKING:
        # populated by the metaclass, defined here to help IDEs only
        __type_name__: str

    def __init__(__message_self__, **kwargs):
        # Uses something other than `self` the first arg to allow "self" as a settable attribute
        gpr_message_module = importlib.import_module(
            f".{__message_self__.__filename__}_pb2", get_current_proto_path()
        )
        gRPCMessageClass = getattr(
            gpr_message_module, f"{__message_self__.__type_name__}"
        )
        for key, item in kwargs.items():
            if isinstance(item, list):
                for index, value in enumerate(item):
                    if isinstance(value, Message):
                        item[index] = value.__message__
            elif isinstance(item, Message):
                kwargs[key] = item.__message__
            elif isinstance(item, dict):
                for key, tmp in item.items():
                    if isinstance(tmp, Message):
                        item[key] = tmp.__message__
        __message_self__.__message__ = gRPCMessageClass(**kwargs)
        super().__init__()

    def init_grpc_message(self, grpc_message: GeneratedProtocolMessageType):
        self.__message__ = grpc_message

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
            self.__message__,
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
            self.__message__,
            including_default_value_fields=including_default_value_fields,
            preserving_proto_field_name=preserving_proto_field_name,
            indent=indent,
            sort_keys=sort_keys,
            use_integers_for_enums=use_integers_for_enums,
        )


FieldType = TypeVar("FieldType")


class BaseField(Generic[FieldType]):
    __type_name__: str = ""
    if TYPE_CHECKING:
        # populated by the metaclass, defined here to help IDEs only
        __field_name__: str

    def __init__(self):
        self.lock = RLock()

    def __get__(self, obj: Message, type: Type) -> FieldType:
        if obj is None:
            return self  # type: ignore
        with self.lock:
            value = obj.__dict__.get(self.__field_name__, _missing)
            if value is _missing:
                value = getattr(obj.__message__, self.__field_name__)
                obj.__dict__[self.__field_name__] = value
            return value

    def __set__(self, instance: Message, value: FieldType) -> None:
        with self.lock:
            setattr(instance.__message__, self.__field_name__, value)
            instance.__dict__[self.__field_name__] = value

    def __str__(self):
        return f"{self.__type_name__} {self.__field_name__}"


class StringField(BaseField[str]):
    __type_name__ = "string"


class Int32Field(BaseField[int]):
    __type_name__ = "int32"


class FloatField(BaseField[float]):
    __type_name__ = "float"


class DoubleField(BaseField[float]):
    __type_name__ = "double"


class Int64Field(BaseField[int]):
    __type_name__ = "int64"


class BooleanField(BaseField[bool]):
    __type_name__ = "bool"


class BytesField(BaseField[bytes]):
    __type_name__ = "bytes"


ReferenceFieldType = TypeVar("ReferenceFieldType", bound=Type[Message])
ReferenceKeyFieldType = TypeVar("ReferenceKeyFieldType", bound=Type[BaseField])
ReferenceValueFieldType = TypeVar(
    "ReferenceValueFieldType", Type[Message], Type[BaseField]
)


class ReferenceField(BaseField[ReferenceFieldType]):
    def __init__(self, key_type: ReferenceFieldType):
        self.__key_type__ = key_type  # type: ignore
        self.__type_name__ = key_type.__type_name__

        super().__init__()


class ListField(BaseField[List[ReferenceValueFieldType]]):
    def __init__(self, key_type: ReferenceValueFieldType):
        self.__key_type__ = key_type  # type: ignore
        self.__type_name__ = key_type.__type_name__
        super().__init__()

    def __str__(self):
        return f"repeated {super().__str__()}"


class MapField(BaseField[Dict[ReferenceKeyFieldType, ReferenceValueFieldType]]):
    def __init__(
        self, key_type: ReferenceKeyFieldType, value_type: ReferenceValueFieldType
    ):
        self.__key_type__: ReferenceKeyFieldType = key_type  # type: ignore
        self.__type_name__ = key_type.__type_name__

        self.__value_type__: ReferenceValueFieldType = value_type
        self.__value_type_name__ = value_type.__type_name__
        super().__init__()

    def __str__(self):
        return f"map<{self.__type_name__}, {self.__value_type_name__}> {self.__field_name__}"
