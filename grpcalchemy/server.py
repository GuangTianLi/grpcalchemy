import logging
import multiprocessing
import socket
import sys
import time
from concurrent import futures
from threading import Event
from typing import Callable, Dict, Optional, Tuple, Type, ContextManager, List

import grpc
from grpc import __version__ as GRPC_VERSION
from grpc._server import _Server as BaseServer
from grpc_health.v1 import health
from grpc_health.v1 import health_pb2_grpc
from grpc_reflection.v1alpha import reflection

from grpcalchemy.blueprint import Blueprint, RequestType, ResponseType, Context
from grpcalchemy.config import DefaultConfig
from grpcalchemy.utils import (
    socket_bind_test,
    select_address_family,
    get_sockaddr,
    add_blueprint_to_server,
)

_ONE_DAY_IN_SECONDS = 60 * 60 * 24


class Server(BaseServer, Blueprint):
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

    #: All multiple processor.
    #:
    #: .. versionadded:: 0.6.0
    workers: List[multiprocessing.Process] = []

    def __init__(self, config: DefaultConfig):
        self.config: DefaultConfig = config

        #: init logger
        self.logger = logging.getLogger(__name__)
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(self.config.GRPC_ALCHEMY_LOGGER_FORMATTER)
        handler.setFormatter(formatter)
        self.logger.setLevel(self.config.GRPC_ALCHEMY_LOGGER_LEVEL)
        self.logger.addHandler(handler)

        self.logger.info(f"workers number: {self.config.GRPC_SERVER_MAX_WORKERS}")

        thread_pool = futures.ThreadPoolExecutor(
            max_workers=self.config.GRPC_SERVER_MAX_WORKERS
        )
        self.logger.info(f"server options: {self.config.GRPC_SERVER_OPTIONS}")
        if tuple(map(int, GRPC_VERSION.split("."))) >= (1, 36, 0):
            super().__init__(
                thread_pool=thread_pool,
                generic_handlers=(),
                interceptors=None,
                options=self.config.GRPC_SERVER_OPTIONS,
                maximum_concurrent_rpcs=self.config.GRPC_SERVER_MAXIMUM_CONCURRENT_RPCS,
                compression=None,
                xds=self.config.GRPC_XDS_SUPPORT,
            )
        else:
            super().__init__(
                thread_pool=thread_pool,
                generic_handlers=(),
                interceptors=None,
                options=self.config.GRPC_SERVER_OPTIONS,
                maximum_concurrent_rpcs=self.config.GRPC_SERVER_MAXIMUM_CONCURRENT_RPCS,
                compression=None,
            )

        #: all the attached blueprints in a dictionary by name.
        #:
        #: .. versionadded:: 0.1.6
        self.blueprints: Dict[str, Blueprint] = {self.access_service_name(): self}
        self.current_app = self

    def register_blueprint(self, bp_cls: Type[Blueprint]) -> None:
        """
        all the gRPC service register in a dictionary by service name.

        .. versionadded:: 0.3.0
        """
        bp = bp_cls()
        bp.current_app = self
        self.blueprints[bp.access_service_name()] = bp

    @classmethod
    def run(
        cls,
        config: Optional[DefaultConfig] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        server_credentials: Optional[grpc.ServerCredentials] = None,
        forever: Optional[bool] = None,
    ):
        if config is None:
            config = DefaultConfig()
        host = host or config.GRPC_SERVER_HOST
        port = port or config.GRPC_SERVER_PORT

        socket_bind_test(host, port)

        cls.as_view()
        for bp_cls in cls.get_blueprints():
            bp_cls.as_view()

        cls.generate_proto_file(config)

        if config.GRPC_SERVER_PROCESS_COUNT > 1:
            address_family = select_address_family(host)
            server_address = get_sockaddr(host, port, address_family)
            with socket.socket(address_family, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                if sock.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT) == 0:
                    raise RuntimeError("Failed to set SO_REUSEPORT.")
                sock.bind(server_address)
                config.GRPC_SERVER_OPTIONS.append(("grpc.so_reuseport", 1))
                for _ in range(config.GRPC_SERVER_PROCESS_COUNT):
                    # NOTE: It is imperative that the worker subprocesses be forked before
                    # any gRPC servers start up. See
                    # https://github.com/grpc/grpc/issues/16001 for more details.
                    worker = multiprocessing.Process(
                        target=cls._run,
                        kwargs=dict(
                            config=config,
                            target=f"{host}:{port}",
                            server_credentials=server_credentials,
                            block=True,
                        ),
                    )
                    worker.start()
                    cls.workers.append(worker)
                if forever:
                    for worker in cls.workers:
                        worker.join()
        else:
            return cls._run(
                config=config,
                target=f"{host}:{port}",
                server_credentials=server_credentials,
                forever=forever,
            )

    @classmethod
    def _run(
        cls,
        config: DefaultConfig,
        target: str,
        server_credentials: Optional[grpc.ServerCredentials] = None,
        forever: Optional[bool] = None,
    ):
        self = cls(config)

        for bp_cls in self.get_blueprints():
            self.register_blueprint(bp_cls)

        services: Tuple[str, ...] = (reflection.SERVICE_NAME, health.SERVICE_NAME)
        for name, bp in self.blueprints.items():
            services += add_blueprint_to_server(self.config, bp, self)

        if self.config.GRPC_HEALTH_CHECKING_ENABLE:
            health_service = health.HealthServicer(
                experimental_non_blocking=True,
                experimental_thread_pool=futures.ThreadPoolExecutor(
                    max_workers=self.config.GRPC_HEALTH_CHECKING_THREAD_POOL_NUM
                ),
            )
            health_pb2_grpc.add_HealthServicer_to_server(health_service, self)

        if self.config.GRPC_SEVER_REFLECTION_ENABLE:
            reflection.enable_server_reflection(services, self)

        if forever is None:
            forever = self.config.GRPC_SERVER_RUN_WITH_BLOCK

        self.before_server_start()

        if server_credentials:
            self.add_secure_port(
                target.encode("utf-8"), server_credentials=server_credentials
            )
        else:
            self.add_insecure_port(target.encode("utf-8"))

        self.start()

        self.logger.info(f"gRPC server is running on {target}")

        if forever:  # pragma: no cover
            try:
                while True:
                    time.sleep(_ONE_DAY_IN_SECONDS)
            except:
                pass
            finally:
                self.stop(0)
        return self

    def before_server_start(self):
        pass

    def after_server_stop(self):
        pass

    def stop(self, grace: int) -> Event:
        event = super().stop(grace)
        self.after_server_stop()
        return event

    def process_request(self, request: RequestType, context: Context) -> RequestType:
        """The code to be executed for each request before
        the gRPC method are called. Only in **UnaryUnary** and **UnarySteam** method
        """
        return request

    def process_response(
        self, response: ResponseType, context: Context
    ) -> ResponseType:
        """The code to be executed for each response after
        the gRPC method are called. Only in **UnaryUnary** and **StreamUnary** method
        """
        return response

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def app_context(
        self, current_service: Blueprint, current_method: Callable, context: Context
    ) -> ContextManager:
        #: Use to construct context for each request.
        #: TODO: using cygrpc.install_context_from_request_call_event to prepare context
        #: .. versionchanged:: 0.5.0
        return self

    def handle_exception(self, e: Exception, context: Context) -> ResponseType:
        raise e

    @classmethod
    def get_blueprints(self) -> List[Type[Blueprint]]:
        return []
