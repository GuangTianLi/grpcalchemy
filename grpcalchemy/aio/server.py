import logging
import multiprocessing
import sys
from concurrent import futures
from typing import Dict, Optional, Tuple, Type, List

import grpc
from grpc.aio._server import Server as BaseServer
from grpc_health.v1 import health
from grpc_health.v1 import health_pb2_grpc
from grpc_reflection.v1alpha import reflection

from grpcalchemy.blueprint import Blueprint
from grpcalchemy.config import DefaultConfig
from grpcalchemy.utils import socket_bind_test, add_blueprint_to_server


class Server(BaseServer, Blueprint):
    """The Server object implements a base application and acts as the central
    object. It is passed the name of gRPC Service of the application. Once it is
    created it will act as a central registry for the gRPC Service.

        from grpcalchemy.aio import Server
        class FooService(Server):
            ...

    :param config: Your Custom Configuration
    :type config: Optional[DefaultConfig]

    .. versionadded:: 0.7.4
    """

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
        super().__init__(
            thread_pool=thread_pool,
            generic_handlers=None,
            interceptors=None,
            options=self.config.GRPC_SERVER_OPTIONS,
            maximum_concurrent_rpcs=self.config.GRPC_SERVER_MAXIMUM_CONCURRENT_RPCS,
            compression=None,
        )

        self.blueprints: Dict[str, Blueprint] = {self.access_service_name(): self}
        self.current_app = self

    def register_blueprint(self, bp_cls: Type[Blueprint]) -> None:
        """
        all the gRPC service register in a dictionary by service name.
        """
        bp = bp_cls()
        bp.current_app = self
        self.blueprints[bp.access_service_name()] = bp

    @classmethod
    async def run(
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

        await cls._run(
            config=config,
            target=f"{host}:{port}",
            server_credentials=server_credentials,
            forever=forever,
        )

    @classmethod
    async def _run(
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
            health_service = health.aio.HealthServicer()
            health_pb2_grpc.add_HealthServicer_to_server(health_service, self)

        if self.config.GRPC_SEVER_REFLECTION_ENABLE:
            reflection.enable_server_reflection(services, self)

        if forever is None:
            forever = self.config.GRPC_SERVER_RUN_WITH_BLOCK

        await self.before_server_start()

        if server_credentials:
            self.add_secure_port(target, server_credentials=server_credentials)
        else:
            self.add_insecure_port(target)

        await self.start()

        self.logger.info(f"gRPC server is running on {target}")

        if forever:  # pragma: no cover
            try:
                await self.wait_for_termination()
            except Exception:
                # Shuts down the server with 0 seconds of grace period. During the
                # grace period, the server won't accept new connections and allow
                # existing RPCs to continue within the grace period.
                await self.stop(0)
        return self

    async def stop(self, grace: Optional[float]) -> None:
        await super().stop(grace)
        await self.after_server_stop()

    @classmethod
    def get_blueprints(self) -> List[Type[Blueprint]]:
        return []

    async def before_server_start(self):
        pass

    async def after_server_stop(self):
        pass
