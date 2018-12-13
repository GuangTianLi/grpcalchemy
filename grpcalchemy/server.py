import importlib
import time
from concurrent import futures

import grpc

from .blueprint import Blueprint
from .meta import default_config
from .utils import generate_proto_file

_ONE_DAY_IN_SECONDS = 60 * 60 * 24


class Server:
    def __init__(self, max_workers: int = 10):
        generate_proto_file()

        self.server = grpc.server(
            futures.ThreadPoolExecutor(max_workers=max_workers))

    def register(self, bp: Blueprint):
        grpc_pb2_module = importlib.import_module(f".{bp.file_name}_pb2_grpc",
                                                  self.config.template_path)
        getattr(grpc_pb2_module,
                f"add_{bp.file_name}Servicer_to_server")(bp, self.server)

    def run(self, port: int = 50051):

        self.server.add_insecure_port(f'[::]:{port}')
        self.server.start()

        try:
            while True:
                time.sleep(_ONE_DAY_IN_SECONDS)
        except KeyboardInterrupt:
            self.server.stop(0)

    @property
    def config(self):
        return default_config
