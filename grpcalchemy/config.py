from typing import Optional, Tuple, List

from configalchemy import BaseConfig

PROTO_TEMPLATE_PATH = "protos"


def set_current_proto_path(path: str):
    global PROTO_TEMPLATE_PATH
    PROTO_TEMPLATE_PATH = path


def get_current_proto_path():
    return PROTO_TEMPLATE_PATH


class DefaultConfig(BaseConfig):

    PROTO_TEMPLATE_PATH = "protos"

    # max workers in service thread pool
    GPRC_SERVER_MAX_WORKERS = 10
    #  An optional list of key-value pairs (channel args in gRPC runtime)
    #  to configure the channel.
    GRPC_SERVER_OPTIONS: List[Tuple[str, str]] = []

    # The maximum number of concurrent RPCs this server
    # will service before returning RESOURCE_EXHAUSTED status, or None to
    # indicate no limit.
    GRPC_SERVER_MAXIMUM_CONCURRENT_RPCS: Optional[int] = None

    GRPC_SERVER_TEST = False
    GRPC_SERVER_HOST = "[::]"
    GRPC_SERVER_PORT = 50051
