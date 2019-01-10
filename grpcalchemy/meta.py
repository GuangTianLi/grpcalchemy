from collections import defaultdict, namedtuple
from typing import DefaultDict, Dict, List, Set, TypeVar, Union

GRPCMessage = TypeVar('GRPCMessage')

MessageMeta = namedtuple('MessageMeta', ['name', 'fields'])
ServiceMeta = namedtuple('Service', ['name', 'rpcs'])

FileMeta = Dict[str, Union[List, Set]]

__meta__: DefaultDict[str, FileMeta] = defaultdict(
    lambda: dict(import_files=set(), messages=[], services=[]))
