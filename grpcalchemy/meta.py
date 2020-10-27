from collections import defaultdict
from typing import DefaultDict, List, Set, TYPE_CHECKING, Type

if TYPE_CHECKING:  # pragma: no cover
    from grpcalchemy.blueprint import gRPCMethodsType
    from grpcalchemy.orm import Message


class ServiceMeta:
    name: str
    rpcs: "gRPCMethodsType"

    def __init__(self, name: str, rpcs: "gRPCMethodsType"):
        self.name = name
        self.rpcs = rpcs


class ProtoBuffMeta:
    def __init__(self):
        self.import_files: Set[str] = set()
        self.messages: List[Type["Message"]] = []
        self.services: List[ServiceMeta] = []


__meta__: DefaultDict[str, ProtoBuffMeta] = defaultdict(ProtoBuffMeta)
