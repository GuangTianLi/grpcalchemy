import importlib
import time
from concurrent import futures
from os import getcwd, mkdir, walk
from os.path import join, abspath, dirname, exists

import grpc
import grpc_tools.protoc
import pkg_resources
from jinja2 import Environment, FileSystemLoader

from .blueprint import Blueprint
from .meta import __meta__, config

_ONE_DAY_IN_SECONDS = 60 * 60 * 24


class Server:
    def __init__(self, template_path: str = None, max_workers: int = 10):
        if template_path:
            self.template_path = template_path
            config.DEFAULT_TEMPLATE_PATH = template_path
        else:
            self.template_path = config.DEFAULT_TEMPLATE_PATH

        self.abs_template_path = join(getcwd(), self.template_path)

        self.generate_proto_file()
        self.server = grpc.server(
            futures.ThreadPoolExecutor(max_workers=max_workers))

    def register(self, bp: Blueprint):
        grpc_pb2_module = importlib.import_module(f".{bp.file_name}_pb2_grpc",
                                                  self.template_path)
        getattr(grpc_pb2_module,
                f"add_{bp.file_name}Servicer_to_server")(bp, self.server)

    def run(self, port: int=50051):
        self.server.add_insecure_port(f'[::]:{port}')
        self.server.start()
        try:
            while True:
                time.sleep(_ONE_DAY_IN_SECONDS)
        except KeyboardInterrupt:
            self.server.stop(0)

    def generate_proto_file(self):
        env = Environment(
            loader=FileSystemLoader(
                searchpath=abspath(join(dirname(__file__), 'templates'))),
            trim_blocks=True,
            lstrip_blocks=True)

        if not exists(self.abs_template_path):
            mkdir(self.abs_template_path)
            env.get_template('__init__.py.tmpl').stream().dump(
                join(self.abs_template_path, "__init__.py"))
            env.get_template('README.md.tmpl').stream().dump(
                join(self.abs_template_path, "README.md"))

        template = env.get_template('rpc.proto.tmpl')
        for filename, meta in __meta__.items():
            template.stream(**meta).dump(
                join(self.abs_template_path, f"{filename}.proto"))

        # copy from grpc_tools
        protoc_file = pkg_resources.resource_filename('grpc_tools',
                                                      'protoc.py')
        proto_include = pkg_resources.resource_filename('grpc_tools', '_proto')
        for root, dirs, files in walk(f'./{self.template_path}/'):
            for file in files:
                if file[-5:] == "proto":
                    grpc_tools.protoc.main([
                        protoc_file,
                        '-I.',
                        '--python_out=.',
                        '--grpc_python_out=.',
                        f'./{self.template_path}/{file}',
                    ] + ['-I{}'.format(proto_include)])
