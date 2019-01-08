import importlib
import time
from concurrent import futures
from typing import Type, Union

import grpc

from .blueprint import Blueprint
from .config import default_config
from .utils import generate_proto_file

_ONE_DAY_IN_SECONDS = 60 * 60 * 24


class Server:
    def __init__(self, max_workers: int = 10, config: Union[str, Type] = None):
        self.config = default_config
        if config:
            self.config.from_object(config)
        self.server = grpc.server(
            futures.ThreadPoolExecutor(max_workers=max_workers))
        generate_proto_file()

    def register(self, bp: Blueprint):
        grpc_pb2_module = importlib.import_module(f".{bp.file_name}_pb2_grpc",
                                                  self.config["TEMPLATE_PATH"])
        getattr(grpc_pb2_module,
                f"add_{bp.file_name}Servicer_to_server")(bp, self.server)

    def run(self, port: int = 50051, test=False):

        self.server.add_insecure_port(f'[::]:{port}')
        self.server.start()

        if not test:
            try:
                while True:
                    time.sleep(_ONE_DAY_IN_SECONDS)
            except KeyboardInterrupt:
                self.server.stop(0)
