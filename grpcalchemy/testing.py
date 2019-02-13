import unittest

from .blueprint import Context, RpcWrappedCallable
from .orm import GeneratedProtocolMessageType, Message


class Client(unittest.TestCase):
    def test_method(self, method: RpcWrappedCallable,
                    request: Message) -> GeneratedProtocolMessageType:
        return method(origin_request=request._message, context=Context())
