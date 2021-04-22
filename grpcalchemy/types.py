from typing import (
    Iterator,
    Generic,
    TypeVar,
    Collection,
    Iterable,
    overload,
    Callable,
    Any,
    Mapping,
)

from typing_extensions import Protocol


class _SupportsLessThan(Protocol):
    def __lt__(self, __other: Any) -> bool:
        ...


_SupportsLessThanT = TypeVar("_SupportsLessThanT", bound=_SupportsLessThan)

_T = TypeVar("_T")
_KT = TypeVar("_KT", str, int)  # Key type.
_VT = TypeVar("_VT")  # Value type.

Streaming = Iterator


class Map(Mapping[_KT, _VT], Generic[_KT, _VT]):
    def clear(self) -> None:
        ...

    @overload
    def pop(self, key: _KT) -> _VT:
        ...

    @overload
    def pop(self, key: _KT, default: _VT = ...) -> _VT:
        ...

    def pop(self, *args, **kwargs):
        ...

    def get_or_create(self, k: _KT) -> _VT:
        ...

    def __delitem__(self, v: _KT) -> None:
        ...


class Repeated(Collection[_T], Generic[_T]):
    def add(self) -> _T:
        ...

    def append(self, value: _T) -> None:
        ...

    def extend(self, values: Iterable[_T]) -> None:
        ...

    def insert(self, index: int, value: _T) -> None:
        ...

    def pop(self, index: int = ...) -> _T:
        ...

    def remove(self, value: _T) -> None:
        ...

    @overload
    def sort(self, *, key: None = ..., reverse: bool = ...) -> None:
        ...

    @overload
    def sort(
        self, *, key: Callable[[_T], _SupportsLessThanT], reverse: bool = ...
    ) -> None:
        ...

    def sort(self, *args, **kwargs):
        ...

    def __getitem__(self, i: int) -> _T:
        ...

    def __delitem__(self, v: _T) -> None:
        ...

    def __len__(self) -> int:
        ...
