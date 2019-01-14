import importlib
import time
from collections import defaultdict
from concurrent import futures
from functools import partial
from typing import Type, Union, Dict, Callable, List, DefaultDict, Any

import grpc

from .blueprint import Blueprint
from .config import default_config
from .utils import generate_proto_file

_ONE_DAY_IN_SECONDS = 60 * 60 * 24


class Server:
    def __init__(self, config: Union[str, Type] = None):

        #: The configuration dictionary as :class:`Config`.  This behaves
        #: exactly like a regular dictionary but supports additional methods
        #: to load a config from files.
        self.config = default_config

        if config:
            self.config.from_object(config)

        self.server = grpc.server(
            futures.ThreadPoolExecutor(max_workers=self.config["MAX_WORKERS"]))

        #: all the attached blueprints in a dictionary by name.
        #:
        #: .. versionadded:: 0.1.6
        self.blueprints: Dict[str, Blueprint] = {}

        #: all the listened event in a dictionary by name.
        #: And the event will be called according to the name:
        #: ``before_server_start``
        #: ``after_server_stop``
        #:
        #: .. versionadded:: 0.1.6
        self.listeners: DefaultDict[str, List[
            Callable[[Server], None]]] = defaultdict(list)

        generate_proto_file()

    def register(self, bp: Blueprint):
        grpc_pb2_module = importlib.import_module(f".{bp.file_name}_pb2_grpc",
                                                  self.config["TEMPLATE_PATH"])
        getattr(grpc_pb2_module,
                f"add_{bp.file_name}Servicer_to_server")(bp, self.server)
        self.blueprints[bp.name] = bp

    def run(self, port: int = 50051, test=False):

        for func in self.listeners["before_server_start"]:
            func(self)

        self.server.add_insecure_port(f'[::]:{port}')
        self.server.start()

        if not test:
            try:
                while True:
                    time.sleep(_ONE_DAY_IN_SECONDS)
            finally:
                self.server.stop(0)
                for func in self.listeners["after_server_stop"]:
                    func(self)

    def listener(self,
                 event: str,
                 listener: Union[Callable[[Any], None], None] = None
                 ) -> Union[partial, Callable[[Any], None]]:
        """
        Create a listener from a decorated function.

        :param event: event to listen to
        """
        if listener is None:
            return partial(self.listener, event)

        self.listeners[event].append(listener)

        return listener
