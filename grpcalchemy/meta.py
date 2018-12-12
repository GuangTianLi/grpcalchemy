from collections import defaultdict, namedtuple
from typing import NewType, Dict, List, DefaultDict, Union, Set, TypeVar

GRPCMessage = TypeVar('GRPCMessage')

MessageMeta = namedtuple('MessageMeta', ['name', 'fields'])
ServiceMeta = namedtuple('Service', ['name', 'rpcs'])

FileName = NewType("FileName", str)
FileMeta = Dict[str, Union[List, Set]]

__meta__: DefaultDict[FileName, FileMeta] = defaultdict(
    lambda: dict(import_files=set(), messages=[], services=[]))


class Config:
    DEFAULT_TEMPLATE_PATH = "protos"


config = Config()
