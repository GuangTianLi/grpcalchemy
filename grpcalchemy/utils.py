import importlib
import socket
from os import getcwd, mkdir, walk
from os.path import abspath, dirname, exists, join
from typing import Union

import grpc_tools.protoc
import pkg_resources
from jinja2 import Environment, FileSystemLoader

try:
    af_unix = socket.AF_UNIX
except AttributeError:
    af_unix = None  # type: ignore

from .meta import __meta__


def generate_proto_file(template_path: str = "protos"):
    abs_template_path = join(getcwd(), template_path)

    env = Environment(
        loader=FileSystemLoader(
            searchpath=abspath(join(dirname(__file__), "templates"))
        ),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    if not exists(abs_template_path):
        mkdir(abs_template_path)
        env.get_template("__init__.py.tmpl").stream().dump(
            join(abs_template_path, "__init__.py")
        )
        env.get_template("README.md.tmpl").stream().dump(
            join(abs_template_path, "README.md")
        )

    template = env.get_template("rpc.proto.tmpl")
    for filename, meta in __meta__.items():
        template.stream(
            file_path=template_path,
            import_files=sorted(meta.import_files),
            messages=meta.messages,
            services=meta.services,
        ).dump(join(abs_template_path, f"{filename}.proto"))

    # copy from grpc_tools
    protoc_file = pkg_resources.resource_filename("grpc_tools", "protoc.py")
    proto_include = pkg_resources.resource_filename("grpc_tools", "_proto")
    for root, dirs, files in walk(f"./{template_path}/"):
        for file in files:
            if file[-5:] == "proto":
                grpc_tools.protoc.main(
                    [
                        protoc_file,
                        "-I.",
                        "--python_out=.",
                        "--grpc_python_out=.",
                        f"./{template_path}/{file}",
                    ]
                    + ["-I{}".format(proto_include)]
                )
    for meta in __meta__.values():
        # populated exact gRPCMessageClass from pb2 file
        for messageCls in meta.messages:
            gpr_message_module = importlib.import_module(
                f".{messageCls.__filename__}_pb2", template_path
            )
            gRPCMessageClass = getattr(
                gpr_message_module, f"{messageCls.__type_name__}"
            )
            messageCls.gRPCMessageClass = gRPCMessageClass


def select_address_family(host: str) -> int:
    """Return ``AF_INET4``, ``AF_INET6``, or ``AF_UNIX`` depending on
    the host and port."""
    # disabled due to problems with current ipv6 implementations
    # and various operating systems.  Probably this code also is
    # not supposed to work, but I can't come up with any other
    # ways to implement this.
    # try:
    #     info = socket.getaddrinfo(host, port, socket.AF_UNSPEC,
    #                               socket.SOCK_STREAM, 0,
    #                               socket.AI_PASSIVE)
    #     if info:
    #         return info[0][0]
    # except socket.gaierror:
    #     pass
    if host.startswith("unix://"):
        return socket.AF_UNIX
    elif ":" in host and hasattr(socket, "AF_INET6"):
        return socket.AF_INET6
    return socket.AF_INET


def get_sockaddr(host: str, port: int, family: int) -> Union[tuple, str, bytes]:
    """Return a fully qualified socket address that can be passed to
    :func:`socket.bind`."""
    if family == af_unix:
        return host.split("://", 1)[1]
    try:
        res = socket.getaddrinfo(
            host, port, family, socket.SOCK_STREAM, socket.IPPROTO_TCP
        )
    except socket.gaierror:
        return host, port
    return res[0][4]


def socket_bind_test(host: str, port: int):
    address_family = select_address_family(host)
    server_address = get_sockaddr(host, port, address_family)
    with socket.socket(address_family, socket.SOCK_STREAM) as s:
        s.bind(server_address)
