from contextlib import AbstractContextManager

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .server import Server
    from .blueprint import RpcWrappedCallable


class BaseRequestContextManager(AbstractContextManager):
    """Base Request Context manager that does no additional processing.
    """

    current_app: "Server"
    current_rpc: "RpcWrappedCallable"

    def __init__(self, app: "Server"):
        self.current_app = app

    def set_current_rpc(
        self, current_rpc: "RpcWrappedCallable"
    ) -> "BaseRequestContextManager":
        self.current_rpc = current_rpc
        return self

    def __enter__(self):
        pass

    def __exit__(self, *excinfo):
        pass
