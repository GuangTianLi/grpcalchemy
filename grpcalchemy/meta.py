from collections import defaultdict
from typing import DefaultDict, List, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from .blueprint import RpcWrappedCallable
    from .orm import BaseField


class ServiceMeta:
    name: str
    rpcs: List["RpcWrappedCallable"]

    def __init__(self, name: str, rpcs: List["RpcWrappedCallable"]):
        self.name = name
        self.rpcs = rpcs


class MessageMeta:
    name: str
    fields: List["BaseField"]

    def __init__(self, name: str, fields: List["BaseField"]):
        self.name = name
        self.fields = fields


class ProtoBuffMeta:
    def __init__(self):
        self.import_files: Set[str] = set()
        self.messages: List[MessageMeta] = []
        self.services: List[ServiceMeta] = []


__meta__: DefaultDict[str, ProtoBuffMeta] = defaultdict(ProtoBuffMeta)
