from unittest.mock import Mock

from grpcalchemy.blueprint import Blueprint, RPCObject
from grpcalchemy.blueprint import InvalidRPCMethod, DuplicatedRPCMethod
from grpcalchemy.orm import Message, StringField
from .test_grpcalchemy import TestGrpcalchemy


class TestBlueprint(TestGrpcalchemy):
    def test_init_without_set_file_name(self):
        test = Blueprint("test")
        self.assertEqual("test", test.file_name)

    def test_register_invalid_rpc_method(self):
        test = Blueprint("test")

        with self.assertRaises(InvalidRPCMethod):

            @test.register
            def test_without_typing(request, context):
                pass

        with self.assertRaises(InvalidRPCMethod):

            @test.register
            def test_one_args(request):
                pass

        with self.assertRaises(InvalidRPCMethod):

            @test.register
            def test_more_than_two_args(request, context, test):
                pass

        class TestMessage(Message):
            test_name = StringField()

        with self.assertRaises(InvalidRPCMethod):

            @test.register
            def test_message_one(request: TestMessage, context):
                pass

        with self.assertRaises(InvalidRPCMethod):

            @test.register
            def test_message_two(request, context) -> TestMessage:
                pass

    def test_register_duplicated_rpc_method(self):
        test = Blueprint("test")

        class TestMessage(Message):
            test_name = StringField()

        @test.register
        def test_message(request: TestMessage, context) -> TestMessage:
            return TestMessage(test_name=request.test_name)

        with self.assertRaises(DuplicatedRPCMethod):

            @test.register
            def test_message(request: TestMessage, context) -> TestMessage:
                return TestMessage(test_name=request.test_name)
