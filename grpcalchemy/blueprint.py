from functools import wraps
from inspect import signature
from typing import Callable, List, Tuple, Type, TYPE_CHECKING, TypeVar, cast

from google.protobuf.message import Message as GeneratedProtocolMessageType
from grpc._server import _Context as Context

from .meta import ServiceMeta, __meta__
from .orm import Message

if TYPE_CHECKING:  # pragma: no cover
    from .server import Server

gRPCMethodsType = List[Callable[[Message, Context], Message]]
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

    def __init__(self):
        self.service_meta = ServiceMeta(name=self.service_name, rpcs=[])

        __meta__[self.file_name].services.append(self.service_meta)
        self.as_view()

    @property
    def service_name(self) -> str:
        return self.__class__.__name__

    @property
    def file_name(self) -> str:
        return self.service_name.lower()

    def before_request(self, request: RequestType, context: Context) -> RequestType:
        """The code to be executed for each request before
        the gRPC method in this blueprint are called.
        """
        return request

    def after_request(self, response: ResponseType, context: Context) -> ResponseType:
        """The code to be executed for each response after
        the gRPC method in this blueprint are called.
        """
        return response

    def as_view(self) -> gRPCMethodsType:
        """Is there a necessary to implement this with Meta Programming"""
        for method_str in dir(self):
            method = getattr(self, method_str)
            if getattr(method, "__grpcmethod__", False):
                self.service_meta.rpcs.append(method)
                request_type = getattr(method, "request_type")
                response_type = getattr(method, "response_type")
                if request_type.__filename__ != self.file_name:
                    __meta__[self.file_name].import_files.add(request_type.__filename__)

                if response_type.__filename__ != self.file_name:
                    __meta__[self.file_name].import_files.add(
                        response_type.__filename__
                    )
        return self.service_meta.rpcs


gRPCFunctionType = Callable[[Blueprint, Message, Context], Message]
F = TypeVar("F", bound=gRPCFunctionType)


def _validate_rpc_method(
    rpc_method: gRPCFunctionType,
) -> Tuple[Type[Message], Type[Message]]:
    sig = signature(rpc_method)

    if len(sig.parameters) == 3:
        request_type = getattr(sig.parameters.get("request"), "annotation")
        response_type = sig.return_annotation
        if all(
            [
                Message not in [request_type, response_type],
                issubclass(request_type, Message),
                issubclass(response_type, Message),
            ]
        ):
            return request_type, response_type
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
    request_type, response_type = _validate_rpc_method(funcobj)

    @wraps(funcobj)
    def wrapper(
        self: Blueprint, origin_request: GeneratedProtocolMessageType, context: Context
    ):
        current_request = request_type()
        current_request.init_grpc_message(grpc_message=origin_request)
        with self.current_app.app_context(self, funcobj, current_request):
            try:
                current_request = self.current_app.process_request(
                    current_request, context
                )
                current_request = self.before_request(current_request, context)
                response = funcobj(self, current_request, context)
                bp_response = self.after_request(response, context)
                app_response = self.current_app.process_response(bp_response, context)
                return app_response.__message__
            except Exception as e:
                return self.current_app.handle_exception(e, current_request, context)

    wrapper.__grpcmethod__ = True  # type: ignore
    wrapper.request_type = request_type  # type: ignore
    wrapper.response_type = response_type  # type: ignore
    return cast(F, wrapper)
