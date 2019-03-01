from grpcalchemy import Context, Server
from grpcalchemy.orm import Message, StringField
from grpcalchemy.testing import Client

from .test_grpcalchemy import TestGrpcalchemy


class TestTesting(TestGrpcalchemy):
    def test_test_method(self):
        class TestMessage(Message):
            test_name = StringField()

        test_server = Server("test_blueprint")

        @test_server.register
        def test_message(request: TestMessage,
                         context: Context) -> TestMessage:
            return TestMessage(test_name=request.test_name)

        test_client = Client(test_server)
        response = test_client.rpc_call(
            test_message, request=TestMessage(test_name="test"))
        self.assertEqual("test", response.test_name)
