from grpcalchemy.meta import __meta__
from grpcalchemy.orm import Message, StringField
from grpcalchemy.server import Server
from .test_grpcalchemy import TestGrpcalchemy


class TestServer(TestGrpcalchemy):
    def setUp(self):
        __meta__.clear()

    def test_server(self):
        class TestMessage(Message):
            test_name = StringField()

        app = Server()

        TestMessage(test_name="test")
