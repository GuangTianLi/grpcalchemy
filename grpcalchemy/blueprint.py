from collections import namedtuple
from inspect import signature
from typing import Tuple, Union, Type, List, Callable

from .meta import ServiceMeta, __meta__, GRPCMessage
from .orm import Message

Rpc = namedtuple('Rpc', ['name', 'request', 'response'])


class RpcObject:
    def __init__(self, func, request, response):
        self.func = func
        self.request: Type[Message] = request
        self.response: Type[Message] = response

        self.grpc_response: Type[GRPCMessage] = None

    def preprocess(self, origin_request: GRPCMessage) -> Message:
        return self.request(**{
            key: getattr(origin_request, key, None)
            for key in self.request.__meta__
        })

    def postprocess(self, origin_response: Message) -> GRPCMessage:
        return self.grpc_response(**origin_response.to_grpc())

    def __call__(self, origin_request: GRPCMessage, context) -> GRPCMessage:
        request = self.preprocess(origin_request)
        return self.postprocess(self.func(request, context))


class Blueprint:
    def __init__(self, name: str, file_name=None):
        if file_name is None:
            self.file_name = name.lower()
        else:
            self.file_name = file_name

        self.name = name
        self.service_meta = ServiceMeta(name=self.name, rpcs=[])
        self.rpc_list: List[RpcObject] = []

    def register(self, service: Callable = None):
        status, request, response = self.check_service(service)
        if not status:
            raise Exception("注册服务不合法")
        self.service_meta.rpcs.append(
            Rpc(name=service.__name__,
                request=request.__name__,
                response=response.__name__))
        if request.__filename__ != self.file_name:
            __meta__[self.file_name]['import_files'].add(request.__filename__)

        if response.__filename__ != self.file_name:
            __meta__[self.file_name]['import_files'].add(response.__filename__)

        __meta__[self.file_name]['services'].append(self.service_meta)

        if hasattr(self, service.__name__):
            raise Exception("Service Duplicate!")
        else:
            grpc_object = RpcObject(
                func=service, request=request, response=response)
            setattr(self, service.__name__, grpc_object)
            self.rpc_list.append(grpc_object)

    def check_service(
            self, func) -> Tuple[bool, Union[type, None], Union[type, None]]:
        sig = signature(func)

        if len(sig.parameters) != 2:
            return False, None, None

        request = getattr(sig.parameters.get("request"), "annotation")
        response = sig.return_annotation

        if issubclass(request, Message) and issubclass(response, Message):
            return True, request, response
        else:
            return False, None, None
