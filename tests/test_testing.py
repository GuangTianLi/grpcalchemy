from grpcalchemy.blueprint import Blueprint, Context
from grpcalchemy.orm import Message, StringField
from grpcalchemy.testing import Client

from .test_grpcalchemy import TestGrpcalchemy


class TestTesting(TestGrpcalchemy, Client):
    def test_test_method(self):
        class TestMessage(Message):
            test_name = StringField()

        test_blueprint = Blueprint("test_blueprint")

        @test_blueprint.register
        def test_message(request: TestMessage,
                         context: Context) -> TestMessage:
            return TestMessage(test_name=request.test_name)

        response = self.rpc_call(
            test_message, request=TestMessage(test_name="test"))
        self.assertEqual("test", response.test_name)
