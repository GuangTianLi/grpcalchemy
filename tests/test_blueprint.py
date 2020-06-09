from typing import Iterator

from grpcalchemy.blueprint import (
    InvalidRPCMethod,
    Blueprint,
    grpcmethod,
    UnaryUnaryRpcMethod,
    UnaryStreamRpcMethod,
    StreamUnaryRpcMethod,
    StreamStreamRpcMethod,
)
from grpcalchemy.orm import Message, StringField
from tests.test_grpcalchemy import TestGrpcalchemy


class TestMessage(Message):
    name = StringField()


class BlueprintTestCase(TestGrpcalchemy):
    def test_init_blueprint(self):
        class FooService(Blueprint):
            @grpcmethod
            def GetSomething(self, request: TestMessage, context) -> TestMessage:
                ...

        test = FooService()
        self.assertEqual("fooservice", test.access_file_name())
        self.assertEqual("FooService", test.access_service_name())

    def test_register_invalid_rpc_method(self):
        class TestMessage(Message):
            name = StringField()

        with self.assertRaises(InvalidRPCMethod):

            @grpcmethod
            def test_without_typing(self, request, context):
                ...

        with self.assertRaises(InvalidRPCMethod):

            @grpcmethod
            def test_one_args(self, request):
                ...

        with self.assertRaises(InvalidRPCMethod):

            @grpcmethod
            def test_more_than_two_args(self, request, context, test):
                ...

        with self.assertRaises(InvalidRPCMethod):

            @grpcmethod
            def test_message_one(self, request: TestMessage, context):
                ...

        with self.assertRaises(InvalidRPCMethod):

            @grpcmethod
            def test_message_two(self, request, context) -> TestMessage:
                ...

        with self.assertRaises(InvalidRPCMethod):

            @grpcmethod
            def test_message_two(self, request: int, context) -> int:
                ...

    def test_unary_unary_grpcmethod(self):
        @grpcmethod
        def UnaryUnary(self, request: TestMessage, context) -> TestMessage:
            pass

        self.assertIsInstance(UnaryUnary.__rpc_method__, UnaryUnaryRpcMethod)

    def test_unary_stream_grpcmethod(self):
        @grpcmethod
        def UnaryStream(self, request: TestMessage, context) -> Iterator[TestMessage]:
            pass

        self.assertIsInstance(UnaryStream.__rpc_method__, UnaryStreamRpcMethod)

    def test_stream_unary_grpcmethod(self):
        @grpcmethod
        def StreamUnary(self, request: Iterator[TestMessage], context) -> TestMessage:
            pass

        self.assertIsInstance(StreamUnary.__rpc_method__, StreamUnaryRpcMethod)

    def test_stream_stream_grpcmethod(self):
        @grpcmethod
        def StreamStream(
            self, request: Iterator[TestMessage], context
        ) -> Iterator[TestMessage]:
            pass

        self.assertIsInstance(StreamStream.__rpc_method__, StreamStreamRpcMethod)
