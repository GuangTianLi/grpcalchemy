from grpcalchemy.blueprint import InvalidRPCMethod, Blueprint, grpcmethod
from grpcalchemy.orm import Message, StringField
from tests.test_grpcalchemy import TestGrpcalchemy


class BlueprintTestCase(TestGrpcalchemy):
    def test_init_blueprint(self):
        class TestMessage(Message):
            name = StringField()

        class FooService(Blueprint):
            @grpcmethod
            def GetSomething(self, request: TestMessage, context) -> TestMessage:
                ...

        test = FooService()
        self.assertEqual("fooservice", test.file_name)
        self.assertEqual("FooService", test.service_name)

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
