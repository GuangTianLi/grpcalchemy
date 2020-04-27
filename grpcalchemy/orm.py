from itertools import chain
from typing import (
    Dict,
    Iterator,
    List,
    Tuple,
    Type,
    TypeVar,
    TYPE_CHECKING,
    Generic,
    Any,
    Callable,
    Iterable,
    Mapping,
    Set,
)

from google.protobuf.json_format import MessageToDict, MessageToJson
from google.protobuf.message import Message as GeneratedProtocolMessageType

from .meta import __meta__

# sentinel
_missing: Any = object()
_missing_factory = lambda: _missing


class DeclarativeMeta(type):
    def __new__(cls, clsname: str, bases: Tuple, clsdict: dict):
        if bases:
            clsdict["__meta__"] = {}
            clsdict["__type_name__"] = clsname

            def iter_base_meta() -> Iterator:
                for base in bases:
                    if base.__meta__:
                        yield from base.__meta__.items()

            need_import_files: Set[str] = set()
            for key, field in iter_attributes(
                chain(
                    filter(
                        lambda x: not x[0].startswith("_"),
                        clsdict.get("__annotations__", {}).items(),
                    ),
                    iter_base_meta(),
                    clsdict.items(),
                )
            ):
                if isinstance(field, ReferenceField):
                    need_import_files.add(field.__key_type__.__filename__)
                elif isinstance(field, ListField):
                    if isinstance(field.__key_type__, ReferenceField):
                        need_import_files.add(
                            field.__key_type__.__key_type__.__filename__
                        )
                elif isinstance(field, MapField):
                    if isinstance(field.__value_type__, ReferenceField):
                        need_import_files.add(
                            field.__value_type__.__key_type__.__filename__
                        )
                clsdict["__meta__"][key] = field
                clsdict[key] = field
            MessageCls = super().__new__(cls, clsname, bases, clsdict)
            file_name = getattr(MessageCls, "__filename__", clsname.lower())
            setattr(MessageCls, "__filename__", file_name)
            need_import_files.discard(file_name)
            __meta__[file_name].messages.append(MessageCls)
            __meta__[file_name].import_files |= need_import_files
            return MessageCls
        return super().__new__(cls, clsname, bases, clsdict)


class _gRPCMessageClass(GeneratedProtocolMessageType):
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if isinstance(value, Iterator):
                value = list(value)
            setattr(self, key, value)


class Message(metaclass=DeclarativeMeta):
    __meta__: Dict[str, "BaseField"] = {}

    gRPCMessageClass: Type = _gRPCMessageClass
    # populated dynamic, defined here to help IDEs only
    __message__: GeneratedProtocolMessageType

    if TYPE_CHECKING:  # pragma: no cover
        # populated by the metaclass, defined here to help IDEs only
        __type_name__: str
        # optional. if no filename is specified, class name's lowercase is used.
        __filename__: str

    def __str__(self) -> str:
        return str(self.__message__)

    def __repr__(self) -> str:
        return repr(self.__message__)

    def __init__(__message_self__, **kwargs):
        # Uses something other than `self` the first arg to allow "self" as a settable attribute
        for key, item in kwargs.items():
            if isinstance(__message_self__.__meta__[key], ReferenceField):
                kwargs[key] = getattr(item, "__message__", item)
            elif isinstance(__message_self__.__meta__[key], ListField):
                kwargs[key] = map(lambda item: getattr(item, "__message__", item), item)
            elif isinstance(__message_self__.__meta__[key], MapField) and isinstance(
                __message_self__.__meta__[key].__value_type__, ReferenceField
            ):
                for key, tmp in item.items():
                    item[key] = getattr(tmp, "__message__", tmp)

        __message_self__.__message__ = __message_self__.gRPCMessageClass(**kwargs)

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


FieldType = TypeVar("FieldType")
M = TypeVar("M", bound=Message)


class BaseField(Generic[FieldType]):
    __type_name__: str = ""

    if TYPE_CHECKING:  # pragma: no cover
        # populated by the metaclass, defined here to help IDEs only
        default: FieldType
        __orig_bases__: Tuple[Any, ...]

    def __init__(
        self,
        default: FieldType = _missing,
        default_factory: Callable[[], FieldType] = _missing_factory,
        **kwargs,
    ):
        if default is not _missing and default_factory is not _missing_factory:
            raise ValueError("cannot specify both default and default_factory")
        if default is not _missing:
            self.default = default
        elif default_factory is not _missing_factory:
            self.default = default_factory()
        else:
            self.default = self.type()

    def __get__(self, instance: Message, owner):
        if instance is None:
            return self  # type: ignore
        value = getattr(instance.__message__, self.__field_name__, None) or self.default
        return value

    def __set__(self, instance: Message, value: FieldType) -> None:
        if value is None:
            value = self.default
            if isinstance(value, Message):
                value = value.__message__
        setattr(instance.__message__, self.__field_name__, value)

    def __str__(self):
        return f"{self.__type_name__} {self.__field_name__}"

    @property
    def type(self) -> Type[FieldType]:
        return self.__orig_bases__[0].__args__[0]

    def __set_name__(self, owner, name: str):
        self.__field_name__ = name


class StringField(BaseField[str]):
    __type_name__ = "string"
    if TYPE_CHECKING:  # pragma: no cover
        # defined this to help IDEs only
        def __get__(self, instance: Message, owner) -> str:
            ...

        def __set__(self, instance: Message, value: str) -> None:
            ...


class Int32Field(BaseField[int]):
    __type_name__ = "int32"
    if TYPE_CHECKING:  # pragma: no cover
        # defined this to help IDEs only
        def __get__(self, instance: Message, owner) -> int:
            ...

        def __set__(self, instance: Message, value: int) -> None:
            ...


class FloatField(BaseField[float]):
    __type_name__ = "float"
    if TYPE_CHECKING:  # pragma: no cover
        # defined this to help IDEs only
        def __get__(self, instance: Message, owner) -> float:
            ...

        def __set__(self, instance: Message, value: float) -> None:
            ...


class DoubleField(BaseField[float]):
    __type_name__ = "double"
    if TYPE_CHECKING:  # pragma: no cover
        # defined this to help IDEs only
        def __get__(self, instance: Message, owner) -> float:
            ...

        def __set__(self, instance: Message, value: float) -> None:
            ...


class Int64Field(BaseField[int]):
    __type_name__ = "int64"
    if TYPE_CHECKING:  # pragma: no cover
        # defined this to help IDEs only
        def __get__(self, instance: Message, owner) -> int:
            ...

        def __set__(self, instance: Message, value: int) -> None:
            ...


class BooleanField(BaseField[bool]):
    __type_name__ = "bool"
    if TYPE_CHECKING:  # pragma: no cover
        # defined this to help IDEs only
        def __get__(self, instance: Message, owner) -> bool:
            ...

        def __set__(self, instance: Message, value: bool) -> None:
            ...


class BytesField(BaseField[bytes]):
    __type_name__ = "bytes"
    if TYPE_CHECKING:  # pragma: no cover
        # defined this to help IDEs only
        def __get__(self, instance: Message, owner) -> bytes:
            ...

        def __set__(self, instance: Message, value: bytes) -> None:
            ...


ReferenceFieldType = TypeVar("ReferenceFieldType", bound=Message)
ReferenceKeyFieldType = TypeVar("ReferenceKeyFieldType", bound=BaseField)
ReferenceValueFieldType = TypeVar("ReferenceValueFieldType", bound=BaseField)


class ReferenceField(BaseField):

    if TYPE_CHECKING:  # pragma: no cover
        # defined this to help IDEs only
        def __get__(self, instance: M, owner) -> ReferenceFieldType:
            ...

        def __set__(self, instance: M, value: ReferenceFieldType) -> None:
            ...

    def __init__(
        self,
        key_type: ReferenceFieldType,
        *,
        default: ReferenceFieldType = _missing,
        default_factory: Callable[[], ReferenceFieldType] = _missing_factory,
    ):
        self.__key_type__ = key_type
        self.__type_name__ = key_type.__type_name__
        super().__init__(default=default, default_factory=default_factory)

    @property
    def type(self) -> Type[ReferenceFieldType]:
        return type(self.__key_type__)


class ListField(BaseField[list]):
    _default = list

    if TYPE_CHECKING:  # pragma: no cover
        # defined this to help IDEs only
        def __get__(self, instance: M, owner) -> List[ReferenceKeyFieldType]:
            ...

        def __set__(self, instance: M, value: List[ReferenceKeyFieldType]) -> None:
            ...

    def __init__(
        self,
        key_type: ReferenceKeyFieldType,
        *,
        default: List[ReferenceKeyFieldType] = _missing,
        default_factory: Callable[[], List[ReferenceKeyFieldType]] = _missing_factory,
    ):
        self.__key_type__ = key_type
        self.__type_name__ = key_type.__type_name__
        super().__init__(default=default, default_factory=default_factory)

    def __str__(self):
        return f"repeated {super().__str__()}"


class MapField(BaseField[dict]):
    _default = dict

    if TYPE_CHECKING:  # pragma: no cover
        # defined this to help IDEs only
        def __get__(
            self, instance: Message, owner
        ) -> Dict[ReferenceKeyFieldType, ReferenceKeyFieldType]:
            ...

        def __set__(
            self,
            instance: Message,
            value: Dict[ReferenceKeyFieldType, ReferenceKeyFieldType],
        ) -> None:
            ...

    def __init__(
        self,
        key_type: ReferenceKeyFieldType,
        value_type: ReferenceValueFieldType,
        *,
        default: Dict[ReferenceKeyFieldType, ReferenceValueFieldType] = _missing,
        default_factory: Callable[
            [], Dict[ReferenceKeyFieldType, ReferenceValueFieldType]
        ] = _missing_factory,
    ):
        self.__key_type__ = key_type
        self.__type_name__ = key_type.__type_name__

        self.__value_type__ = value_type
        self.__value_type_name__ = value_type.__type_name__
        super().__init__(default=default, default_factory=default_factory)

    def __str__(self):
        return f"map<{self.__type_name__}, {self.__value_type_name__}> {self.__field_name__}"


_TYPE_FIELD_MAP: Dict[type, Type[BaseField]] = {
    str: StringField,
    int: Int32Field,
    float: DoubleField,
    bytes: BytesField,
    bool: BooleanField,
}


def iter_attributes(
    attributes: Iterable[Tuple[str, Any]]
) -> Iterator[Tuple[str, BaseField]]:
    for name, o in attributes:
        origin = getattr(o, "__origin__", None)
        if origin:
            if isinstance(origin, type):
                if issubclass(origin, List):  #: typing.List
                    name, p = next(iter_attributes([(name, o.__args__[0])]))
                    yield name, ListField(p)
                elif issubclass(origin, Mapping):
                    name, k = next(iter_attributes([(name, o.__args__[0])]))
                    name, v = next(iter_attributes([(name, o.__args__[1])]))
                    yield name, MapField(k, v)
        elif isinstance(o, BaseField):
            yield name, o
        elif isinstance(o, type):
            if issubclass(o, BaseField):
                yield name, o()
            elif o in _TYPE_FIELD_MAP:
                yield name, _TYPE_FIELD_MAP[o]()
            elif issubclass(o, Message):
                yield name, ReferenceField(o())
