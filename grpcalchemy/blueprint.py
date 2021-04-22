from abc import ABC, abstractmethod
from functools import wraps
from inspect import signature
from operator import attrgetter
from typing import (
    Callable,
    List,
    Type,
    TYPE_CHECKING,
    TypeVar,
    cast,
    Iterable,
    Any,
    Iterator,
    Union,
)

from google.protobuf.message import Message as GeneratedProtocolMessageType
from grpc import ServicerContext
from grpc._server import _Context as Context

from .meta import ServiceMeta, __meta__
from .orm import Message
from .types import Streaming

if TYPE_CHECKING:  # pragma: no cover
    from .server import Server


class _Context(ServicerContext):
    # TODO use grpc._create_servicer_context to build our Context
    ...


class AbstractRpcMethod(ABC):
    __slots__ = ("name", "request_cls", "response_cls", "funcobj")

    def __init__(
        self,
        *,
        name: str,
        funcobj: Callable,
        request_cls: Type[Message],
        response_cls: Type[Message],
    ):
        self.name = name
        self.funcobj = funcobj
        self.request_cls = request_cls
        self.response_cls = response_cls

    @abstractmethod
    def to_rpc_method(self) -> str:  # pragma: no cover
        pass

    @abstractmethod
    def handle_call(
        self, bp: "Blueprint", message: Any, context: Context
    ) -> Any:  # pragma: no cover
        pass

    def request_iterator(
        self, message: Iterable[GeneratedProtocolMessageType]
    ) -> Iterator[Message]:
        for m in message:
            current_request = self.request_cls()
            current_request.init_grpc_message(grpc_message=m)
            yield current_request


gRPCMethodsType = List[AbstractRpcMethod]


class UnaryUnaryRpcMethod(AbstractRpcMethod):

    if TYPE_CHECKING:  # pragma: no cover

        @staticmethod
        def funcobj(bp: "Blueprint", request: Message, contest: Context) -> Message:
            pass

    def to_rpc_method(self) -> str:
        return f"rpc {self.name} ({self.request_cls.__name__}) returns ({self.response_cls.__name__}) {{}}"

    def handle_call(
        self, bp: "Blueprint", message: GeneratedProtocolMessageType, context: Context
    ) -> GeneratedProtocolMessageType:
        current_request = self.request_cls()
        current_request.init_grpc_message(grpc_message=message)
        with bp.current_app.app_context(bp, self.funcobj, context):
            # TODO: using cygrpc.install_context_from_request_call_event to prepare context
            try:
                current_request = bp.current_app.process_request(
                    current_request, context
                )
                current_request = bp.before_request(current_request, context)
                response = self.funcobj(bp, current_request, context)
                bp_response = bp.after_request(response, context)
                app_response = bp.current_app.process_response(bp_response, context)
                return app_response.__message__
            except Exception as e:
                response = bp.current_app.handle_exception(e, context)
                if response:
                    return response.__message__


class UnaryStreamRpcMethod(AbstractRpcMethod):
    if TYPE_CHECKING:  # pragma: no cover

        @staticmethod
        def funcobj(
            bp: "Blueprint", request: Message, contest: Context
        ) -> Iterator[Message]:
            pass

    def to_rpc_method(self) -> str:
        return f"rpc {self.name} ({self.request_cls.__name__}) returns (stream {self.response_cls.__name__}) {{}}"

    def handle_call(
        self, bp: "Blueprint", message: GeneratedProtocolMessageType, context: Context
    ) -> Iterable[GeneratedProtocolMessageType]:
        current_request = self.request_cls()
        current_request.init_grpc_message(grpc_message=message)
        with bp.current_app.app_context(bp, self.funcobj, context):
            # TODO: using cygrpc.install_context_from_request_call_event to prepare context
            try:
                current_request = bp.current_app.process_request(
                    current_request, context
                )
                current_request = bp.before_request(current_request, context)
                for response in self.funcobj(bp, current_request, context):
                    yield response.__message__
            except Exception as e:
                yield from map(
                    attrgetter("__message__"),
                    bp.current_app.handle_exception(e, context),
                )


class StreamUnaryRpcMethod(AbstractRpcMethod):
    if TYPE_CHECKING:  # pragma: no cover

        @staticmethod
        def funcobj(
            bp: "Blueprint", request: Iterator[Message], contest: Context
        ) -> Message:
            pass

    def to_rpc_method(self) -> str:
        return f"rpc {self.name} (stream {self.request_cls.__name__}) returns ({self.response_cls.__name__}) {{}}"

    def handle_call(
        self,
        bp: "Blueprint",
        message: Iterable[GeneratedProtocolMessageType],
        context: Context,
    ) -> GeneratedProtocolMessageType:
        request_iterator = self.request_iterator(message)
        with bp.current_app.app_context(bp, self.funcobj, context):
            # TODO: using cygrpc.install_context_from_request_call_event to prepare context
            try:
                response = self.funcobj(bp, request_iterator, context)
                bp_response = bp.after_request(response, context)
                app_response = bp.current_app.process_response(bp_response, context)
                return app_response.__message__
            except Exception as e:
                response = bp.current_app.handle_exception(e, context)
                if response:
                    return response.__message__


class StreamStreamRpcMethod(AbstractRpcMethod):
    if TYPE_CHECKING:  # pragma: no cover

        @staticmethod
        def funcobj(
            bp: "Blueprint", request: Iterator[Message], contest: Context
        ) -> Iterator[Message]:
            pass

    def to_rpc_method(self) -> str:
        return f"rpc {self.name} (stream {self.request_cls.__name__}) returns (stream {self.response_cls.__name__}) {{}}"

    def handle_call(
        self,
        bp: "Blueprint",
        message: Iterable[GeneratedProtocolMessageType],
        context: Context,
    ) -> Iterable[GeneratedProtocolMessageType]:
        request_iterator = self.request_iterator(message)
        with bp.current_app.app_context(bp, self.funcobj, context):
            # TODO: using cygrpc.install_context_from_request_call_event to prepare context
            try:
                for response in self.funcobj(bp, request_iterator, context):
                    yield response.__message__
            except Exception as e:
                yield from map(
                    attrgetter("__message__"),
                    bp.current_app.handle_exception(e, context),
                )


RequestType = TypeVar("RequestType", bound=Message)
ResponseType = TypeVar("ResponseType", bound=Message)


class InvalidRPCMethod(Exception):
    pass


class Blueprint:
    """gRPCAlchemy uses a concept of blueprints for making gRPC services and
    supporting common patterns within an application or across applications.
    Blueprints can greatly simplify how large applications work. A Blueprint object
    can be registered with :meth:`Server.register_blueprint`::

        from your_blueprint import FooService
        app.register_blueprint(FooService)
    """

    current_app: "Server"

    @classmethod
    def access_service_name(cls) -> str:
        return cls.__name__

    @classmethod
    def access_file_name(cls) -> str:
        return cls.access_service_name().lower()

    def before_request(self, request: RequestType, context: Context) -> RequestType:
        """The code to be executed for each request before
        the gRPC method in this blueprint are called. Only in **UnaryUnary** and **UnarySteam** method
        """
        return request

    def after_request(self, response: ResponseType, context: Context) -> ResponseType:
        """The code to be executed for each response after
        the gRPC method in this blueprint are called. **UnaryUnary** and **StreamUnary** method
        """
        return response

    @classmethod
    def as_view(cls) -> gRPCMethodsType:
        """Is there a necessary to implement this with Meta Programming"""
        file_name = cls.access_file_name()
        service_meta = ServiceMeta(name=cls.access_service_name(), rpcs=[])
        __meta__[file_name].services.append(service_meta)
        for method_str in dir(cls):
            method = getattr(cls, method_str)
            if getattr(method, "__grpcmethod__", False):
                service_meta.rpcs.append(method.__rpc_method__)
                rpc_method: AbstractRpcMethod = method.__rpc_method__
                request_cls = rpc_method.request_cls
                response_cls = rpc_method.response_cls
                if request_cls.__filename__ != file_name:
                    __meta__[file_name].import_files.add(request_cls.__filename__)

                if response_cls.__filename__ != file_name:
                    __meta__[file_name].import_files.add(response_cls.__filename__)
        return service_meta.rpcs


gRPCFunctionType = Callable[
    [Blueprint, Union[Message, Iterator[Message]], Context],
    Union[Message, Iterator[Message]],
]
F = TypeVar("F", bound=gRPCFunctionType)


def _validate_rpc_method(
    funcobj: gRPCFunctionType,
) -> AbstractRpcMethod:
    sig = signature(funcobj)

    if len(sig.parameters) == 3:
        request_streaming = False
        response_streaming = False

        request_type = getattr(sig.parameters.get("request"), "annotation")
        response_type = sig.return_annotation

        request_origin = getattr(request_type, "__origin__", None)
        if request_origin:
            if issubclass(request_origin, Streaming):
                request_type = request_type.__args__[0]
                request_streaming = True

        response_origin = getattr(response_type, "__origin__", None)
        if response_origin:
            if issubclass(response_origin, Streaming):
                response_type = response_type.__args__[0]
                response_streaming = True
        if all(
            [
                Message not in [request_type, response_type],
                issubclass(request_type, Message),
                issubclass(response_type, Message),
            ]
        ):
            if request_streaming:
                if response_streaming:
                    return StreamStreamRpcMethod(
                        name=funcobj.__name__,
                        funcobj=funcobj,
                        request_cls=request_type,
                        response_cls=response_type,
                    )
                else:
                    return StreamUnaryRpcMethod(
                        name=funcobj.__name__,
                        funcobj=funcobj,
                        request_cls=request_type,
                        response_cls=response_type,
                    )
            else:
                if response_streaming:
                    return UnaryStreamRpcMethod(
                        name=funcobj.__name__,
                        funcobj=funcobj,
                        request_cls=request_type,
                        response_cls=response_type,
                    )
                else:
                    return UnaryUnaryRpcMethod(
                        name=funcobj.__name__,
                        funcobj=funcobj,
                        request_cls=request_type,
                        response_cls=response_type,
                    )
    raise InvalidRPCMethod(
        """\
The RPC method is invalid.

The correct signature is blow::

    class MyMessage(Message):
        ...

    @grpcmethod
    def GetSomething(self, request: MyMessage, context: Context) -> MyMessage:
        ...
"""
    )


def grpcmethod(funcobj: F) -> F:
    """A decorator indicating gRPC methods.


    Requires that the class is inherited from Blueprint and according to:
    https://developers.google.com/protocol-buffers/docs/style#services,
    the function name should use CamelCase (with an initial capital).

    Any gRPC method must define request and response's Message Type with `Type Hint`.

    Usage::

        class FooService(Blueprint):
            @grpcmethod
            def GetSomething(self, request: Message, context: Context) -> Message:
                ...

    :param funcobj: gRPC Method
    :type funcobj: Callable[[Message, Context], Message]
    :rtype: Callable[[Message, Context], Message]
    """
    rpc_method = _validate_rpc_method(funcobj)

    @wraps(funcobj)
    def wrapper(
        self: Blueprint, origin_request: GeneratedProtocolMessageType, context: Context
    ):
        return rpc_method.handle_call(self, origin_request, context)

    wrapper.__grpcmethod__ = True  # type: ignore
    wrapper.__rpc_method__ = rpc_method  # type: ignore
    return cast(F, wrapper)
