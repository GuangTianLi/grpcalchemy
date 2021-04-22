import socket
import sys
from importlib import import_module
from os import walk, path, mkdir
from os.path import abspath, dirname, exists, join
from typing import Union, Optional, TYPE_CHECKING, Tuple

import grpc_tools.protoc
import pkg_resources
from jinja2 import Environment, FileSystemLoader

from grpcalchemy.config import DefaultConfig

if TYPE_CHECKING:  # pragma: no cover
    from grpcalchemy.server import Server
    from grpcalchemy.blueprint import Blueprint


try:
    af_unix = socket.AF_UNIX
except AttributeError:  # pragma: no cover
    af_unix = None  # type: ignore

from .meta import __meta__

if sys.platform == "win32":
    FILE_SEPARATOR = "\\"
else:
    FILE_SEPARATOR = "/"

curdir = "."


def make_packages(name, mode=0o777, exist_ok=False):
    """make_packages(name [, mode=0o777][, exist_ok=False])

    Super-mkdir; create a leaf directory with python package and all intermediate ones.
    Works like mkdir, except that any intermediate path segment (not just the rightmost)
    will be created if it does not exist. If the target directory already
    exists, raise an OSError if exist_ok is False. Otherwise no exception is
    raised.  This is recursive.

    """
    head, tail = path.split(name)
    if not tail:
        head, tail = path.split(head)
    if head and tail and not path.exists(head):
        try:
            make_packages(head, exist_ok=exist_ok)
        except FileExistsError:
            # Defeats race condition when another thread created the path
            pass
        cdir = curdir
        if isinstance(tail, bytes):
            cdir = bytes(curdir, "ASCII")
        if tail == cdir:  # xxx/newdir/. exists if xxx/newdir exists
            return
    try:
        mkdir(name, mode)
    except OSError:
        # Cannot rely on checking for EEXIST, since the operating system
        # could give priority to other errors like EACCES or EROFS
        if not exist_ok or not path.isdir(name):
            raise
    else:
        init_file = join(name, "__init__.py")
        if not path.exists(init_file):
            open(init_file, "a").close()


def generate_proto_file(
    template_path_root: str = "",
    template_path: str = "protos",
    auto_generate: bool = True,
):
    abs_template_path = join(template_path_root, template_path)

    if auto_generate:
        env = Environment(
            loader=FileSystemLoader(
                searchpath=abspath(join(dirname(__file__), "templates"))
            ),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )

        if not exists(abs_template_path):
            make_packages(abs_template_path)
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
        for _, dirs, files in walk(f"{template_path}"):
            for file in files:
                if file[-5:] == "proto":
                    grpc_tools.protoc.main(
                        [
                            protoc_file,
                            "-I.",
                            "--python_out=.",
                            "--grpc_python_out=.",
                            f".{FILE_SEPARATOR}{template_path}{FILE_SEPARATOR}{file}",
                        ]
                        + ["-I{}".format(proto_include)]
                    )
    for meta in __meta__.values():
        import_module(abs_template_path.split(FILE_SEPARATOR, 1)[0])
        for messageCls in meta.messages:
            # populated exact gRPCMessageClass from pb2 file
            gpr_message_module = import_module(
                f"{join(abs_template_path, messageCls.__filename__).replace(FILE_SEPARATOR, '.')}_pb2"
            )
            gRPCMessageClass = getattr(
                gpr_message_module, f"{messageCls.__type_name__}"
            )
            messageCls.gRPCMessageClass = gRPCMessageClass


def add_blueprint_to_server(
    config: DefaultConfig, bp: "Blueprint", server: "Server"
) -> Tuple[str, ...]:
    grpc_pb2_grpc_module = import_module(
        f"{join(config.PROTO_TEMPLATE_ROOT, config.PROTO_TEMPLATE_PATH, bp.access_file_name()).replace(FILE_SEPARATOR, '.')}_pb2_grpc"
    )
    grpc_pb2_module = import_module(
        f"{join(config.PROTO_TEMPLATE_ROOT, config.PROTO_TEMPLATE_PATH, bp.access_file_name()).replace(FILE_SEPARATOR, '.')}_pb2"
    )
    getattr(grpc_pb2_grpc_module, f"add_{bp.access_service_name()}Servicer_to_server")(
        bp, server
    )
    return tuple(
        service.full_name
        for service in getattr(grpc_pb2_module, "DESCRIPTOR").services_by_name.values()
    )


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


def get_sockaddr(
    host: str, port: Optional[int], family: int
) -> Union[tuple, str, bytes]:
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


def socket_bind_test(host: str, port: Optional[int] = None):
    address_family = select_address_family(host)
    server_address = get_sockaddr(host, port, address_family)
    with socket.socket(address_family, socket.SOCK_STREAM) as s:
        s.bind(server_address)
