import importlib

from .blueprint import Blueprint, RpcWrappedCallable
from .config import default_config
from .orm import Message
from .utils import generate_proto_file


class Client:
    config = default_config

    def __init__(self, target, credentials=None, options=None):
        from grpc import _channel

        self.channel = _channel.Channel(
            target, () if options is None else options, credentials)

    def __enter__(self):
        generate_proto_file(self.config["TEMPLATE_PATH"])
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.channel._close()
        return False

    def register(self, bp: Blueprint):
        grpc_pb2_module = importlib.import_module(f".{bp.file_name}_pb2_grpc",
                                                  self.config["TEMPLATE_PATH"])
        stub = getattr(grpc_pb2_module, f"{bp.name}Stub")(self.channel)
        setattr(self, bp.name, gRPCRequest(stub))


class gRPCRequest:
    def __init__(self, stub):
        self.stub = stub

    def __call__(self, rpc: RpcWrappedCallable, message: Message) -> Message:
        stub = object.__getattribute__(self, "stub")
        func = getattr(stub, rpc.name)
        response = rpc.response_type()
        response.init_grpc_message(grpc_message=func(message._message))
        return response
