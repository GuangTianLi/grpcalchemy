from itertools import chain
from typing import (
    Dict,
    Iterator,
    List,
    Tuple,
    Type,
    TypeVar,
    TYPE_CHECKING,
    cast,
    Union,
)

from google.protobuf.json_format import MessageToDict, MessageToJson
from google.protobuf.message import Message as GeneratedProtocolMessageType

from .meta import __meta__

# sentinel
_missing = object()


class DeclarativeMeta(type):
    def __new__(cls, clsname: str, bases: Tuple, clsdict: dict):
        if bases:
            file_name = clsdict.get("__filename__", clsname).lower()
            clsdict["__filename__"] = file_name
            clsdict["__meta__"] = {}
            clsdict["__type_name__"] = clsname

            def iter_base_meta() -> Iterator:
                for base in bases:
                    if base.__meta__:
                        yield from base.__meta__.items()

            for key, field in chain(clsdict.items(), iter_base_meta()):
                if isinstance(field, BaseField):
                    field.__field_name__ = key
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
            MessageCls = super().__new__(cls, clsname, bases, clsdict)
            __meta__[file_name].messages.append(MessageCls)
            return MessageCls
        return super().__new__(cls, clsname, bases, clsdict)


class _gRPCMessageClass(GeneratedProtocolMessageType):
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class Message(metaclass=DeclarativeMeta):
    __meta__: Dict[str, "BaseField"] = {}
    __filename__: str = ""
    gRPCMessageClass: Type = _gRPCMessageClass
    # populated dynamic, defined here to help IDEs only
    __message__: GeneratedProtocolMessageType

    if TYPE_CHECKING:  # pragma: no cover
        # populated by the metaclass, defined here to help IDEs only
        __type_name__: str

    def __init__(__message_self__, **kwargs):
        # Uses something other than `self` the first arg to allow "self" as a settable attribute
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
        __message_self__.__message__ = __message_self__.gRPCMessageClass(**kwargs)
        super().__init__()

    def init_grpc_message(self, grpc_message: GeneratedProtocolMessageType):
        self.__message__ = grpc_message

    def message_to_dict(
        self,
        *,
        including_default_value_fields: bool = True,
        preserving_proto_field_name: bool = True,
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
        *,
        including_default_value_fields: bool = True,
        preserving_proto_field_name: bool = True,
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


_SupportValueType = Union[str, bytes, int, float, list, dict, bool, Message]
_DefaultValueType = Type[_SupportValueType]


class BaseField:
    _default: _DefaultValueType
    __type_name__: str = ""

    if TYPE_CHECKING:  # pragma: no cover
        # populated by the metaclass, defined here to help IDEs only
        __field_name__: str
        _default_value: _SupportValueType

    def __new__(cls):
        self = super().__new__(cls)
        self._default_value = cls._default()
        return self

    def __get__(self, instance: Message, owner):
        if instance is None:
            return self  # type: ignore
        value = instance.__dict__.get(self.__field_name__, _missing)
        if value is _missing:
            value = getattr(
                instance.__message__, self.__field_name__, self._default_value
            )
            instance.__dict__[self.__field_name__] = value
        return value

    def __set__(self, instance: Message, value: _SupportValueType) -> None:
        if value is None:
            value = self._default()
            if isinstance(value, Message):
                value = value.__message__
        setattr(instance.__message__, self.__field_name__, value)
        instance.__dict__[self.__field_name__] = value

    def __str__(self):
        return f"{self.__type_name__} {self.__field_name__}"


class StringField(BaseField):
    _default = str
    __type_name__ = "string"
    if TYPE_CHECKING:  # pragma: no cover
        # defined this to help IDEs only
        def __new__(cls, *args, **kwargs) -> str:
            ...


class Int32Field(BaseField):
    _default = int
    __type_name__ = "int32"
    if TYPE_CHECKING:  # pragma: no cover
        # defined this to help IDEs only
        def __new__(cls, *args, **kwargs) -> int:
            ...


class FloatField(BaseField):
    _default = float
    __type_name__ = "float"
    if TYPE_CHECKING:  # pragma: no cover
        # defined this to help IDEs only
        def __new__(cls, *args, **kwargs) -> float:
            ...


class DoubleField(BaseField):
    _default = float
    __type_name__ = "double"
    if TYPE_CHECKING:  # pragma: no cover
        # defined this to help IDEs only
        def __new__(cls, *args, **kwargs) -> float:
            ...


class Int64Field(BaseField):
    _default = int
    __type_name__ = "int64"
    if TYPE_CHECKING:  # pragma: no cover
        # defined this to help IDEs only
        def __new__(cls, *args, **kwargs) -> int:
            ...


class BooleanField(BaseField):
    _default = bool
    __type_name__ = "bool"
    if TYPE_CHECKING:  # pragma: no cover
        # defined this to help IDEs only
        def __new__(cls, *args, **kwargs) -> bool:
            ...


class BytesField(BaseField):
    _default = bytes
    __type_name__ = "bytes"
    if TYPE_CHECKING:  # pragma: no cover
        # defined this to help IDEs only
        def __new__(cls, *args, **kwargs) -> bytes:
            ...


ReferenceFieldType = TypeVar("ReferenceFieldType", bound=Message)
ReferenceKeyFieldType = TypeVar("ReferenceKeyFieldType", bound=BaseField)
ReferenceValueFieldType = TypeVar("ReferenceValueFieldType", Message, BaseField)


class ReferenceField(BaseField):
    __key_type__: Type[Message]

    def __new__(cls, key_type: Type[ReferenceFieldType]) -> ReferenceFieldType:
        cls._default = key_type
        self = super().__new__(cls)
        self.__key_type__ = key_type
        self.__type_name__ = key_type.__type_name__
        return cast(ReferenceFieldType, self)


class ListField(BaseField):
    _default = list
    # using this way to help IDEs only
    __key_type__: Union[Type[BaseField], Type[Message]]

    # using __new__ rather than __init__ to help IDEs only
    def __new__(
        cls, key_type: Type[ReferenceValueFieldType]
    ) -> List[ReferenceValueFieldType]:
        self = super().__new__(cls)
        self.__key_type__ = key_type
        self.__type_name__ = key_type.__type_name__
        return cast(List[ReferenceValueFieldType], self)

    def __str__(self):
        return f"repeated {super().__str__()}"


class MapField(BaseField):
    _default = dict
    __key_type__: Type[BaseField]
    __value_type__: Union[Type[BaseField], Type[Message]]

    # using __new__ rather than __init__ to help IDEs only
    def __new__(
        cls,
        key_type: Type[ReferenceKeyFieldType],
        value_type: Type[ReferenceValueFieldType],
    ) -> Dict[ReferenceKeyFieldType, ReferenceValueFieldType]:
        self = super().__new__(cls)
        self.__key_type__ = key_type
        self.__type_name__ = key_type.__type_name__

        self.__value_type__ = value_type
        self.__value_type_name__ = value_type.__type_name__
        return cast(Dict[ReferenceKeyFieldType, ReferenceValueFieldType], self)

    def __str__(self):
        return f"map<{self.__type_name__}, {self.__value_type_name__}> {self.__field_name__}"
