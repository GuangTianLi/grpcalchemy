from collections import namedtuple
from functools import partial
from functools import update_wrapper
from inspect import signature
from typing import Tuple, Type, Callable, Generic, TypeVar, List, Union

from grpc._server import _Context

from .meta import ServiceMeta, __meta__, GRPCMessage
from .orm import Message

Rpc = namedtuple('Rpc', ['name', 'request', 'response'])

Context = _Context

_T = TypeVar("_T")


class InvalidRPCMethod(Exception):
    pass


class DuplicatedRPCMethod(Exception):
    pass


class RpcWrappedCallable(Generic[_T]):
    name: str = ...
    request: Type[Message] = ...
    response: Type[Message] = ...
    pre_processes: List[Callable[[Message, Context], Message]] = ...
    post_processes: List[Callable[[Message, Context], Message]]= ...

    def preprocess(origin_request: GRPCMessage) -> Message:
        ...

    def postprocess(origin_response: Message) -> GRPCMessage:
        ...

    def __call__(origin_request: GRPCMessage, context: Context) -> GRPCMessage:
        ...


def _validate_rpc_method(rpc_method: Callable[[Message, Context], Message]
                         ) -> Tuple[Type[Message], Type[Message]]:
    sig = signature(rpc_method)

    if len(sig.parameters) == 2:
        request = getattr(sig.parameters.get("request"), "annotation")
        response = sig.return_annotation
        if issubclass(request, Message) and issubclass(response, Message):
            return request, response
    raise InvalidRPCMethod("注册服务不合法")


def _validate_rpc_processes(
        rpc_processes: List[Callable[[Message, Context], Message]]
) -> List[Callable[[Message, Context], Message]]:
    rpc_processes = rpc_processes or []
    for rpc_process in rpc_processes:
        _validate_rpc_method(rpc_process)
    return rpc_processes


def rpc_call_wrap(func: Callable[[Message, Context], Message],
                  request: Type[Message], response: Type[Message],
                  pre_processes: List[Callable[[Message, Context], Message]],
                  post_processes: List[Callable[[Message, Context], Message]]
                  ) -> RpcWrappedCallable:
    def preprocess(origin_request: GRPCMessage, context: Context) -> Message:
        current_request = request(grpc_message=origin_request)
        for pre_process in pre_processes:
            current_request = pre_process(current_request, context)
        return current_request

    def postprocess(origin_response: Message, context: Context) -> GRPCMessage:
        current_response = origin_response
        for post_process in post_processes:
            current_response = post_process(current_response, context)
        return current_response._message

    def call(origin_request: GRPCMessage, context: Context) -> GRPCMessage:
        request = preprocess(origin_request, context)
        return postprocess(func(request, context), context)

    call.name = func.__name__
    call.request = request
    call.response = response
    call.pre_processes = pre_processes
    call.post_processes = post_processes
    update_wrapper(call, func)

    return call


class Blueprint:
    def __init__(
            self,
            name: str,
            file_name: str = None,
            pre_processes: List[Callable[[Message, Context], Message]] = None,
            post_processes: List[
                Callable[[Message, Context], Message]] = None):
        if file_name is None:
            self.file_name = name.lower()
        else:
            self.file_name = file_name

        self.name = name
        self.service_meta = ServiceMeta(name=self.name, rpcs=[])
        self.pre_processes = _validate_rpc_processes(pre_processes)
        self.post_processes = _validate_rpc_processes(post_processes)

        __meta__[self.file_name]['services'].append(self.service_meta)

    def register(
            self,
            rpc: Callable[[Message, Context], Message] = None,
            *,
            pre_processes: List[Callable[[Message, Context], Message]] = None,
            post_processes: List[Callable[[Message, Context], Message]] = None
    ) -> Union[RpcWrappedCallable, partial]:
        if rpc is None:
            return partial(
                self.register,
                pre_processes=pre_processes,
                post_processes=post_processes)
        request, response = _validate_rpc_method(rpc)

        rpc_call: RpcWrappedCallable = rpc_call_wrap(
            func=rpc,
            request=request,
            response=response,
            pre_processes=self.pre_processes +
            _validate_rpc_processes(pre_processes),
            post_processes=self.post_processes +
            _validate_rpc_processes(post_processes))
        self.service_meta.rpcs.append(rpc_call)
        if request.__filename__ != self.file_name:
            __meta__[self.file_name]['import_files'].add(request.__filename__)

        if response.__filename__ != self.file_name:
            __meta__[self.file_name]['import_files'].add(response.__filename__)

        if hasattr(self, rpc.__name__):
            raise DuplicatedRPCMethod("Service Duplicate!")
        else:
            setattr(self, rpc_call.name, rpc_call)
            return rpc_call
