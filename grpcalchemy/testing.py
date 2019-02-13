import unittest

from .blueprint import Context, RpcWrappedCallable
from .orm import GeneratedProtocolMessageType, Message


class TestContext(Context):
    def is_active(self):
        pass

    def time_remaining(self):
        pass

    def cancel(self):
        pass

    def add_callback(self, callback):
        pass

    def disable_next_message_compression(self):
        pass

    def invocation_metadata(self):
        pass

    def peer(self):
        pass

    def peer_identities(self):
        pass

    def peer_identity_key(self):
        pass

    def auth_context(self):
        pass

    def send_initial_metadata(self, initial_metadata):
        pass

    def set_trailing_metadata(self, trailing_metadata):
        pass

    def abort(self, code, details):
        pass

    def abort_with_status(self, status):
        pass

    def set_code(self, code):
        pass

    def set_details(self, details):
        pass


class Client(unittest.TestCase):
    def rpc_call(self,
                 method: RpcWrappedCallable,
                 request: Message,
                 context=TestContext()) -> GeneratedProtocolMessageType:
        return method(origin_request=request._message, context=context)
