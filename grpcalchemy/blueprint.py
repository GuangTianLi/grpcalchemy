from collections import namedtuple
from functools import partial, update_wrapper
from inspect import signature
from typing import Callable, List, Tuple, Type, TypeVar, Union

from google.protobuf.message import Message as GeneratedProtocolMessageType
from grpc import ServicerContext

from .meta import ServiceMeta, __meta__
from .orm import Message

Rpc = namedtuple('Rpc', ['name', 'request', 'response'])

Context = ServicerContext

_T = TypeVar("_T")


class InvalidRPCMethod(Exception):
    pass


class DuplicatedRPCMethod(Exception):
    pass


class RpcWrappedCallable:
    name: str = ...
    request_type: Type[Message] = ...
    response_type: Type[Message] = ...
    pre_processes: List[Callable[[Message, Context], Message]] = ...
    post_processes: List[Callable[[Message, Context], Message]] = ...

    def preprocess(self,
                   origin_request: GeneratedProtocolMessageType) -> Message:
        ...

    def postprocess(self,
                    origin_response: Message) -> GeneratedProtocolMessageType:
        ...

    def __call__(self, origin_request: GeneratedProtocolMessageType,
                 context: Context) -> GeneratedProtocolMessageType:
        ...


def _validate_rpc_method(rpc_method: Callable[[Message, Context], Message]
                         ) -> Tuple[Type[Message], Type[Message]]:
    sig = signature(rpc_method)

    if len(sig.parameters) == 2:
        request_type = getattr(sig.parameters.get("request"), "annotation")
        response_type = sig.return_annotation
        if issubclass(request_type, Message) and issubclass(
                response_type, Message):
            return request_type, response_type
    raise InvalidRPCMethod("Invalid rpc Method!")


def _validate_rpc_processes(
        rpc_processes: Union[List[Callable[[Message, Context], Message]], None]
) -> List[Callable[[Message, Context], Message]]:
    rpc_processes = rpc_processes or []
    for rpc_process in rpc_processes:
        _validate_rpc_method(rpc_process)
    return rpc_processes


def rpc_call_wrap(func: Callable[[Message, Context], Message],
                  request_type: Type[Message], response_type: Type[Message],
                  pre_processes: List[Callable[[Message, Context], Message]],
                  post_processes: List[Callable[[Message, Context], Message]]
                  ) -> RpcWrappedCallable:
    def preprocess(origin_request: GeneratedProtocolMessageType,
                   context: Context) -> Message:
        current_request = request_type()
        current_request.init_grpc_message(grpc_message=origin_request)
        for pre_process in pre_processes:
            current_request = pre_process(current_request, context)
        return current_request

    def postprocess(origin_response: Message,
                    context: Context) -> GeneratedProtocolMessageType:
        current_response = origin_response
        for post_process in post_processes:
            current_response = post_process(current_response, context)
        return current_response._message

    def call(origin_request: GeneratedProtocolMessageType,
             context: Context) -> GeneratedProtocolMessageType:
        request = preprocess(origin_request, context)
        return postprocess(func(request, context), context)

    call.name = func.__name__
    call.request_type = request_type
    call.response_type = response_type
    call.pre_processes = pre_processes
    call.post_processes = post_processes
    update_wrapper(call, func)

    return call  # pyre-ignore


class Blueprint:
    """gRPCAlchemy uses a concept of blueprints for making gRPC services and
    supporting common patterns within an application or across applications.
    Blueprints can greatly simplify how large applications work. A Blueprint object
    can be registered with :meth:`Server.register_blueprint`::

        from grpcalchemy import Blueprint
        the_blueprint = Blueprint('blueprint')
        app.register_blueprint(the_blueprint)

    :param str name:
    :param str file_name:
    :param pre_processes:
    :type pre_processes: List[Callable[[Message, Context], Message]]
    :param post_processes:
    :type post_processes: List[Callable[[Message, Context], Message]]
    """

    def __init__(
            self,
            name: str,
            file_name: str = '',
            pre_processes: List[Callable[[Message, Context], Message]] = None,
            post_processes: List[
                Callable[[Message, Context], Message]] = None):
        if file_name == '':
            self.file_name = name.lower()
        else:
            self.file_name = file_name
        self.file_name.replace('.', '_')
        self.name = name
        self.service_meta = ServiceMeta(name=self.name, rpcs=[])

        #: all the processes function in a list.
        #: And the function must be Callable[[`Message`, Context], `Message`]:
        #:
        #: .. versionadded:: 0.1.6
        self.pre_processes = _validate_rpc_processes(pre_processes)
        #: all the processes function in a list.
        #: And the function must be Callable[[`Message`, Context], `Message`]:
        #:
        #: .. versionadded:: 0.1.6
        self.post_processes = _validate_rpc_processes(post_processes)

        __meta__[self.file_name].services.append(self.service_meta)

    def register(
            self,
            rpc: Union[Callable[[Message, Context], Message], None] = None,
            *,
            pre_processes: Union[List[Callable[[Message, Context], Message]],
                                 None] = None,
            post_processes: Union[List[Callable[[Message, Context], Message]],
                                  None] = None
    ) -> Union[RpcWrappedCallable, partial]:
        """Any gRPC method can be defined like this::

            @app.register
            def test(request: Message, context) -> Message:
                pass

        :param rpc:
        :type rpc: Callable[[Message, Context], Message]
        :param pre_processes:
        :type pre_processes: List[Callable[[Message, Context], Message]
        :param post_processes:
        :type post_processes: List[Callable[[Message, Context], Message]
        :return:
        """
        if rpc is None:
            return partial(
                self.register,
                pre_processes=pre_processes,
                post_processes=post_processes)
        request_type, response_type = _validate_rpc_method(rpc)
        current_pre_process = self.pre_processes + _validate_rpc_processes(
            pre_processes)
        current_post_processes = self.post_processes + _validate_rpc_processes(
            post_processes)
        rpc_call: RpcWrappedCallable = rpc_call_wrap(
            func=rpc,
            request_type=request_type,
            response_type=response_type,
            pre_processes=current_pre_process,
            post_processes=current_post_processes)
        self.service_meta.rpcs.append(rpc_call)
        if request_type.__filename__ != self.file_name:
            __meta__[self.file_name].import_files.add(
                request_type.__filename__)

        if response_type.__filename__ != self.file_name:
            __meta__[self.file_name].import_files.add(
                response_type.__filename__)

        if hasattr(self, rpc.__name__):
            raise DuplicatedRPCMethod("Service Duplicate!")
        else:
            setattr(self, rpc_call.name, rpc_call)
            return rpc_call
