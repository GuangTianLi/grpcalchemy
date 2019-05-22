import importlib
import logging
import time
from collections import defaultdict
from concurrent import futures
from functools import partial
from threading import Event
from typing import (
    Any,
    Callable,
    DefaultDict,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
)

import grpc
from grpc import GenericRpcHandler
from grpc._cython import cygrpc
from grpc._server import (
    _add_generic_handlers,
    _ServerState,
    _start,
    _stop,
    _validate_generic_rpc_handlers,
)

from .blueprint import Blueprint, Context
from .config import default_config
from .ctx import AppContext
from .orm import Message
from .utils import generate_proto_file

_ONE_DAY_IN_SECONDS = 60 * 60 * 24


class Server(Blueprint, grpc.Server):
    """The Server object implements a base application and acts as the central
    object. It is passed the name of gRPC Service of the application. Once it is
    created it will act as a central registry for the gRPC Service.

    Usually you create a :class:`Server` instance in your main module or
    in the :file:`__init__.py` file of your package like this::

        from grpcalchemy import Server
        app = Server('server')

    :param str name:
    :param str file_name:
    :param pre_processes:
    :type pre_processes: List[Callable[[Message, Context], Message]]
    :param post_processes:
    :type post_processes: List[Callable[[Message, Context], Message]]
    :param config:
    :type config: Union[str, Type]

    .. versionadded:: 0.2.0
    """

    def __init__(
            self,
            name: str,
            file_name: str = '',
            pre_processes: List[Callable[[Message, Context], Message]] = None,
            post_processes: List[Callable[[Message, Context], Message]] = None,
            config: Optional[dict] = None):
        super().__init__(
            name=name,
            file_name=file_name,
            pre_processes=pre_processes,
            post_processes=post_processes)

        if config is not None:
            default_config.update(config)

        #: The configuration dictionary as :class:`Config`.  This behaves
        #: exactly like a regular dictionary but supports additional methods
        #: to load a config from files.
        self.config = default_config

        thread_pool = futures.ThreadPoolExecutor(
            max_workers=self.config["MAX_WORKERS"])
        completion_queue = cygrpc.CompletionQueue()
        server = cygrpc.Server(self.config["OPTIONS"])
        server.register_completion_queue(completion_queue)

        #: gRPC Server State
        #:
        #: .. versionadded:: 0.2.1
        self._state = _ServerState(completion_queue, server, (), None,
                                   thread_pool,
                                   self.config["MAXIMUM_CONCURRENT_RPCS"])

        #: all the attached blueprints in a dictionary by name.
        #:
        #: .. versionadded:: 0.1.6
        self.blueprints: Dict[str, Blueprint] = {self.name: self}

        #: all the listened event in a dictionary by name.
        #: And the event will be called according to the name:
        #: ``before_server_start``
        #: ``after_server_stop``
        #:
        #: .. versionadded:: 0.1.6
        self.listeners: DefaultDict[str, List[
            Callable[[Server], None]]] = defaultdict(list)

        #: init logger
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(logging.StreamHandler())

        self.register_blueprint(self)

        #: Create an :class:`~grpcalchemy.ctx.AppContext`. Use as a ``with``
        #: block to push the context, which will make :data:`current_app`
        #: point at this application.
        #:
        #: .. versionchanged:: 0.2.4
        self.app_context: AppContext = AppContext(self)

    def register_blueprint(self, bp: Blueprint) -> None:
        """
        all the gRPC service register in a dictionary by name.

        :param Blueprint bp:
        :rtype: None

        .. versionadded:: 0.2.0
        """
        self.blueprints[bp.name] = bp

    def run(self, port: int = 50051, test=False) -> None:
        generate_proto_file(template_path=self.config["TEMPLATE_PATH"])
        for name, bp in self.blueprints.items():
            grpc_pb2_module = importlib.import_module(
                f".{bp.file_name}_pb2_grpc", self.config["TEMPLATE_PATH"])
            getattr(grpc_pb2_module, f"add_{bp.name}Servicer_to_server")(bp,
                                                                         self)
            for rpc in bp.service_meta.rpcs:
                rpc.ctx = self.app_context

        for func in self.listeners["before_server_start"]:
            func(self)

        self.add_insecure_port(f'[::]:{port}'.encode("utf-8"))
        self.start()

        self.logger.info(f"gRPC server is running on 0.0.0.0:{port}")

        if not test:
            try:
                while True:
                    time.sleep(_ONE_DAY_IN_SECONDS)
            except:
                pass
            finally:
                self.stop(0)
                for func in self.listeners["after_server_stop"]:
                    func(self)

    def listener(self,
                 event: str,
                 listener: Optional[Callable[[Any], None]] = None
                 ) -> Union[partial, Callable[[Any], None]]:
        """
        Create a listener from a decorated function.

        :param event: event to listen to
        """
        if listener is None:
            return partial(self.listener, event)

        self.listeners[event].append(listener)

        return listener

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
        return _stop(self._state, grace)

    def add_generic_rpc_handlers(
            self, generic_rpc_handlers: Tuple[GenericRpcHandler]) -> None:
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

    def add_secure_port(self, address: bytes,
                        server_credentials: grpc.ServerCredentials):
        with self._state.lock:
            return self._state.server.add_http2_port(
                address, server_credentials._credentials)

    def __del__(self):
        """
        .. versionadded:: 0.2.1
        """
        if hasattr(self, '_state'):
            # We can not grab a lock in __del__(), so set a flag to signal the
            # serving daemon thread (if it exists) to initiate shutdown.
            self._state.server_deallocated = True
