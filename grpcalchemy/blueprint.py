from functools import partial, update_wrapper
from inspect import signature
from typing import Callable, List, Optional, Tuple, Type, Union

from google.protobuf.message import Message as GeneratedProtocolMessageType
from grpc import ServicerContext as Context

from .ctx import AppContext, RequestContext
from .globals import LocalProxy, _find_rpc
from .meta import ServiceMeta, __meta__
from .orm import Message

current_rpc: 'RpcWrappedCallable' = LocalProxy(_find_rpc)


class InvalidRPCMethod(Exception):
    pass


class DuplicatedRPCMethod(Exception):
    pass


class RpcWrappedCallable:
    name: str
    ctx: AppContext
    origin_request: GeneratedProtocolMessageType
    context: Context

    def __init__(self, server_name: str,
                 func: Callable[[Message, Context], Message],
                 request_type: Type[Message], response_type: Type[Message],
                 pre_processes: List[Callable[[Message, Context], Message]],
                 post_processes: List[Callable[[Message, Context], Message]]):
        self._func = func
        self.server_name = server_name
        self.name: str = func.__name__
        self.request_type = request_type
        self.response_type = response_type
        self.pre_processes = pre_processes
        self.post_processes = post_processes
        self.__signature__ = signature(func)
        update_wrapper(self, func)

    def preprocess(self, origin_request: GeneratedProtocolMessageType,
                   context: Context) -> Message:
        current_request = self.request_type()
        current_request.init_grpc_message(grpc_message=origin_request)
        for pre_process in self.pre_processes:
            current_request = pre_process(current_request, context)
        return current_request

    def postprocess(self, origin_response: Message,
                    context: Context) -> GeneratedProtocolMessageType:
        current_response = origin_response
        for post_process in self.post_processes:
            current_response = post_process(current_response, context)
        return current_response._message

    def __call__(self, origin_request: GeneratedProtocolMessageType,
                 context: Context) -> GeneratedProtocolMessageType:
        self.origin_request = origin_request
        self.context = context
        with RequestContext(app_context=self.ctx, rpc=self):
            request = self.preprocess(origin_request, context)
            return self.postprocess(self._func(request, context), context)


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
        rpc_processes: Optional[List[Callable[[Message, Context], Message]]]
) -> List[Callable[[Message, Context], Message]]:
    rpc_processes = rpc_processes or []
    for rpc_process in rpc_processes:
        _validate_rpc_method(rpc_process)
    return rpc_processes


class ServiceMetaTypeshed:
    name: str
    rpcs: List[RpcWrappedCallable]


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
        self.service_meta: ServiceMetaTypeshed = ServiceMeta(
            name=self.name, rpcs=[])

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

    def register(self,
                 rpc: Optional[Callable[[Message, Context], Message]] = None,
                 *,
                 pre_processes: Optional[List[
                     Callable[[Message, Context], Message]]] = None,
                 post_processes: Optional[List[
                     Callable[[Message, Context], Message]]] = None
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
        wrapped_rpc: RpcWrappedCallable = RpcWrappedCallable(
            server_name=self.name,
            func=rpc,
            request_type=request_type,
            response_type=response_type,
            pre_processes=current_pre_process,
            post_processes=current_post_processes)
        self.service_meta.rpcs.append(wrapped_rpc)
        if request_type.__filename__ != self.file_name:
            __meta__[self.file_name].import_files.add(
                request_type.__filename__)

        if response_type.__filename__ != self.file_name:
            __meta__[self.file_name].import_files.add(
                response_type.__filename__)

        if hasattr(self, rpc.__name__):
            raise DuplicatedRPCMethod("Service Duplicate!")
        else:
            setattr(self, wrapped_rpc.name, wrapped_rpc)
            return wrapped_rpc
