import logging
import logging
import os.path
import time
from concurrent import futures
from threading import Event
from typing import Callable, Dict, Optional, Tuple, Type, ContextManager, List
from importlib import import_module
import grpc
from configalchemy.utils import import_reference
from grpc import GenericRpcHandler
from grpc._cython import cygrpc
from grpc._server import (
    _add_generic_handlers,
    _ServerState,
    _start,
    _stop,
    _validate_generic_rpc_handlers,
)

from .blueprint import Blueprint, RequestType, ResponseType, Context
from .config import DefaultConfig
from .utils import generate_proto_file, socket_bind_test

_ONE_DAY_IN_SECONDS = 60 * 60 * 24


class Server(Blueprint, grpc.Server):
    """The Server object implements a base application and acts as the central
    object. It is passed the name of gRPC Service of the application. Once it is
    created it will act as a central registry for the gRPC Service.

        from grpcalchemy import Server
        class FooService(Server):
            ...

    :param config: Your Custom Configuration
    :type config: Optional[DefaultConfig]

    .. versionadded:: 0.2.0
    """

    def __init__(self, config: Optional[DefaultConfig] = None):
        self.config = config or DefaultConfig()

        thread_pool = futures.ThreadPoolExecutor(
            max_workers=self.config.GPRC_SERVER_MAX_WORKERS
        )
        completion_queue = cygrpc.CompletionQueue()
        server = cygrpc.Server(self.config.GRPC_SERVER_OPTIONS)
        server.register_completion_queue(completion_queue)

        #: gRPC Server State
        #:
        #: .. versionadded:: 0.2.1
        self._state = _ServerState(
            completion_queue,
            server,
            (),
            None,
            thread_pool,
            self.config.GRPC_SERVER_MAXIMUM_CONCURRENT_RPCS,
        )

        #: all the attached blueprints in a dictionary by name.
        #:
        #: .. versionadded:: 0.1.6
        self.blueprints: Dict[str, Blueprint] = {self.service_name: self}

        #: init logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(self.config.GRPC_ALCHEMY_LOGGER_LEVEL)
        self.logger.addHandler(logging.StreamHandler())

        super().__init__()
        self.current_app = self

    def register_blueprint(self, bp_cls: Type[Blueprint]) -> None:
        """
        all the gRPC service register in a dictionary by service name.

        .. versionadded:: 0.3.0
        """
        bp = bp_cls()
        bp.current_app = self
        self.blueprints[bp.service_name] = bp

    def run(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        server_credentials: Optional[grpc.ServerCredentials] = None,
        block: Optional[bool] = None,
    ) -> None:
        host = host or self.config.GRPC_SERVER_HOST
        port = port or self.config.GRPC_SERVER_PORT

        if block is None:
            block = self.config.GRPC_SERVER_RUN_WITH_BLOCK

        socket_bind_test(host, port)

        for bp_cls in self.get_blueprints():
            self.register_blueprint(bp_cls)

        generate_proto_file(
            template_path_root=self.config.PROTO_TEMPLATE_ROOT,
            template_path=self.config.PROTO_TEMPLATE_PATH,
        )
        for name, bp in self.blueprints.items():
            grpc_pb2_module = import_module(
                f"{os.path.join(self.config.PROTO_TEMPLATE_ROOT, self.config.PROTO_TEMPLATE_PATH, bp.file_name).replace('/', '.')}_pb2_grpc"
            )
            getattr(grpc_pb2_module, f"add_{bp.service_name}Servicer_to_server")(
                bp, self
            )

        self.before_server_start()

        if server_credentials:
            self.add_secure_port(
                f"{host}:{port}".encode("utf-8"), server_credentials=server_credentials
            )
        else:
            self.add_insecure_port(f"{host}:{port}".encode("utf-8"))
        self.start()

        self.logger.info(f"gRPC server is running on {host}:{port}")

        if block:  # pragma: no cover
            try:
                while True:
                    time.sleep(_ONE_DAY_IN_SECONDS)
            except:
                pass
            finally:
                self.stop(0)

    def before_server_start(self):
        pass

    def after_server_stop(self):
        pass

    def start(self) -> None:
        """Starts this Server.

        This method may only be called once. (i.e. it is not idempotent).
        .. versionadded:: 0.2.1
        """
        _start(self._state)

    def stop(self, grace: int) -> Event:
        """Stops this Server.

        This method immediately stop service of new RPCs in all cases.

        If a grace period is specified, this method returns immediately
        and all RPCs active at the end of the grace period are aborted.
        If a grace period is not specified (by passing None for `grace`),
        all existing RPCs are aborted immediately and this method
        blocks until the last RPC handler terminates.

        This method is idempotent and may be called at any time.
        Passing a smaller grace value in a subsequent call will have
        the effect of stopping the Server sooner (passing None will
        have the effect of stopping the server immediately). Passing
        a larger grace value in a subsequent call *will not* have the
        effect of stopping the server later (i.e. the most restrictive
        grace value is used).

        :param int grace: A duration of time in seconds or None.

        :return:
          A threading.Event that will be set when this Server has completely
          stopped, i.e. when running RPCs either complete or are aborted and
          all handlers have terminated.
        :rtype: Event

        .. versionadded:: 0.2.1
        """
        event = _stop(self._state, grace)
        self.after_server_stop()
        return event

    def add_generic_rpc_handlers(
        self, generic_rpc_handlers: Tuple[GenericRpcHandler]
    ) -> None:
        """Registers GenericRpcHandlers with this Server.

        This method is only safe to call before the server is started.

        Args:
          generic_rpc_handlers: An iterable of GenericRpcHandlers that will be
          used to service RPCs.

        :param generic_rpc_handlers: An Tuple of GenericRpcHandlers that will be
          used to service RPCs.
        :type generic_rpc_handlers: Tuple[GenericRpcHandler]
        :rtype: None

        .. versionadded:: 0.2.1
        """
        _validate_generic_rpc_handlers(generic_rpc_handlers)
        _add_generic_handlers(self._state, generic_rpc_handlers)

    def add_insecure_port(self, address: bytes):
        with self._state.lock:
            return self._state.server.add_http2_port(address)

    def add_secure_port(
        self, address: bytes, server_credentials: grpc.ServerCredentials
    ):
        with self._state.lock:
            return self._state.server.add_http2_port(
                address, server_credentials._credentials
            )

    def process_request(self, request: RequestType, context: Context) -> RequestType:
        """The code to be executed for each request before
         the gRPC method are called.
        """
        return request

    def process_response(
        self, response: ResponseType, context: Context
    ) -> ResponseType:
        """The code to be executed for each response after
        the gRPC method are called.
        """
        return response

    def __del__(self):
        """
        .. versionadded:: 0.2.1
        """
        if hasattr(self, "_state"):
            # We can not grab a lock in __del__(), so set a flag to signal the
            # serving daemon thread (if it exists) to initiate shutdown.
            self._state.server_deallocated = True

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def app_context(
        self,
        current_service: Blueprint,
        current_method: Callable,
        current_request: RequestType,
    ) -> ContextManager:
        #: Use to construct context for each request.
        #:
        #: .. versionchanged:: 0.3.0
        return self

    def handle_exception(
        self, e: Exception, request: RequestType, context: Context
    ) -> ResponseType:
        raise e

    def get_blueprints(self) -> List[Type[Blueprint]]:
        return []
