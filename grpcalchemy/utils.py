from os import getcwd, mkdir, walk
from os.path import abspath, dirname, exists, join

import grpc_tools.protoc
import pkg_resources
from jinja2 import Environment, FileSystemLoader

from .meta import __meta__


def generate_proto_file(template_path: str = "protos"):
    abs_template_path = join(getcwd(), template_path)

    env = Environment(
        loader=FileSystemLoader(
            searchpath=abspath(join(dirname(__file__), 'templates'))),
        trim_blocks=True,
        lstrip_blocks=True)

    if not exists(abs_template_path):
        mkdir(abs_template_path)
        env.get_template('__init__.py.tmpl').stream().dump(
            join(abs_template_path, "__init__.py"))
        env.get_template('README.md.tmpl').stream().dump(
            join(abs_template_path, "README.md"))

    template = env.get_template('rpc.proto.tmpl')
    for filename, meta in __meta__.items():
        meta.import_files = sorted(meta.import_files)
        template.stream(
            file_path=template_path,
            import_files=meta.import_files,
            messages=meta.messages,
            services=meta.services).dump(
                join(abs_template_path, f"{filename}.proto"))

    # copy from grpc_tools
    protoc_file = pkg_resources.resource_filename('grpc_tools', 'protoc.py')
    proto_include = pkg_resources.resource_filename('grpc_tools', '_proto')
    for root, dirs, files in walk(f'./{template_path}/'):
        for file in files:
            if file[-5:] == "proto":
                grpc_tools.protoc.main([
                    protoc_file,
                    '-I.',
                    '--python_out=.',
                    '--grpc_python_out=.',
                    f'./{template_path}/{file}',
                ] + ['-I{}'.format(proto_include)])
