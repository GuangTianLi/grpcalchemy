from collections import namedtuple
from inspect import signature
from typing import Tuple, Union, Type, List, Callable

from grpc._server import _Context

from .meta import ServiceMeta, __meta__, GRPCMessage
from .orm import Message

Rpc = namedtuple('Rpc', ['name', 'request', 'response'])

Context = _Context


class InvalidRPCMethod(Exception):
    pass


class DuplicatedRPCMethod(Exception):
    pass


class RPCObject:
    def __init__(self, func: Callable, request: Type[Message]):
        self.func = func
        self.request = request

    def preprocess(self, origin_request: GRPCMessage) -> Message:
        return self.request(origin_request)

    def postprocess(self, origin_response: Message) -> GRPCMessage:
        return origin_response._message

    def __call__(self, origin_request: GRPCMessage, context) -> GRPCMessage:
        request = self.preprocess(origin_request)
        return self.postprocess(self.func(request, context))


class Blueprint:
    def __init__(self, name: str, file_name: str = None):
        if file_name is None:
            self.file_name = name.lower()
        else:
            self.file_name = file_name

        self.name = name
        self.service_meta = ServiceMeta(name=self.name, rpcs=[])
        self.rpc_list: List[RPCObject] = []

        __meta__[self.file_name]['services'].append(self.service_meta)

    def register(self, rpc: Callable = None):
        status, request, response = self.check_service(rpc)
        if not status:
            raise InvalidRPCMethod("注册服务不合法")

        self.service_meta.rpcs.append(
            Rpc(name=rpc.__name__,
                request=request._type_name,
                response=response._type_name))
        if request.__filename__ != self.file_name:
            __meta__[self.file_name]['import_files'].add(request.__filename__)

        if response.__filename__ != self.file_name:
            __meta__[self.file_name]['import_files'].add(response.__filename__)

        if hasattr(self, rpc.__name__):
            raise DuplicatedRPCMethod("Service Duplicate!")
        else:
            grpc_object = RPCObject(func=rpc, request=request)
            setattr(self, rpc.__name__, grpc_object)
            self.rpc_list.append(grpc_object)

    def check_service(self, func: Callable
                      ) -> Tuple[bool, Union[type, None], Union[type, None]]:
        sig = signature(func)

        if len(sig.parameters) != 2:
            return False, None, None

        request = getattr(sig.parameters.get("request"), "annotation")
        response = sig.return_annotation

        if issubclass(request, Message) and issubclass(response, Message):
            return True, request, response
        else:
            return False, None, None
