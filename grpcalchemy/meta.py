from collections import defaultdict, namedtuple
from typing import DefaultDict, List, Set

MessageMeta = namedtuple('MessageMeta', ['name', 'fields'])
ServiceMeta = namedtuple('Service', ['name', 'rpcs'])


class ProtoBuffMeta:
    def __init__(self):
        self.import_files: Set[str] = set()
        self.messages: List[MessageMeta] = []
        self.services: List[ServiceMeta] = []


__meta__: DefaultDict[str, ProtoBuffMeta] = defaultdict(ProtoBuffMeta)
