from collections import namedtuple
from functools import update_wrapper
from inspect import signature
from typing import Tuple, Union, Type, Callable

from grpc._server import _Context

from .meta import ServiceMeta, __meta__, GRPCMessage
from .orm import Message

Rpc = namedtuple('Rpc', ['name', 'request', 'response'])

Context = _Context


class InvalidRPCMethod(Exception):
    pass


class DuplicatedRPCMethod(Exception):
    pass


def rpc_call_wrap(func: Callable[[Message, Context], Message],
                  request: Type[Message], response: Type[Message]):
    def preprocess(origin_request: GRPCMessage) -> Message:
        return request(grpc_message=origin_request)

    def postprocess(origin_response: Message) -> GRPCMessage:
        return origin_response._message

    def call(origin_request: GRPCMessage, context: Context) -> GRPCMessage:
        request = preprocess(origin_request)
        return postprocess(func(request, context))

    call.name = func.__name__
    call.request = request
    call.response = response
    update_wrapper(call, func)

    return call


class Blueprint:
    def __init__(self, name: str, file_name: str = None):
        if file_name is None:
            self.file_name = name.lower()
        else:
            self.file_name = file_name

        self.name = name
        self.service_meta = ServiceMeta(name=self.name, rpcs=[])

        __meta__[self.file_name]['services'].append(self.service_meta)

    def register(self, rpc: Callable = None) -> Callable:
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
            rpc_call = rpc_call_wrap(
                func=rpc, request=request, response=response)
            setattr(self, rpc.__name__, rpc_call)
            return rpc_call

    def check_service(
            self, func: Callable
    ) -> Tuple[bool, Union[Type[Message], None], Union[Type[Message], None]]:
        sig = signature(func)

        if len(sig.parameters) != 2:
            return False, None, None

        request = getattr(sig.parameters.get("request"), "annotation")
        response = sig.return_annotation

        if issubclass(request, Message) and issubclass(response, Message):
            return True, request, response
        else:
            return False, None, None
