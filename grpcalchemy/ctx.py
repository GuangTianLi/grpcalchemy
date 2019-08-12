from contextlib import AbstractContextManager

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .server import Server
    from .orm import Message


class BaseRequestContextManager(AbstractContextManager):
    """Base Request Context manager that does no additional processing.
    """

    def __init__(self, app: "Server", current_message: "Message"):
        self.current_app = app
        self.current_message = current_message

    def __enter__(self):
        pass

    def __exit__(self, *excinfo):
        pass
