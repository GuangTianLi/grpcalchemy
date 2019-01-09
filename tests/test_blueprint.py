from grpcalchemy.blueprint import Blueprint
from grpcalchemy.blueprint import InvalidRPCMethod, DuplicatedRPCMethod
from grpcalchemy.orm import Message, StringField

from .test_grpcalchemy import TestGrpcalchemy


class TestMessage(Message):
    test_name = StringField()


class TestBlueprint(TestGrpcalchemy):
    def test_init_without_set_file_name(self):
        test = Blueprint("test")
        self.assertEqual("test", test.file_name)

    def test_register_invalid_rpc_process(self):
        def test_without_typing(request, context):
            pass

        with self.assertRaises(InvalidRPCMethod):
            Blueprint("test", pre_processes=[test_without_typing])

        with self.assertRaises(InvalidRPCMethod):
            Blueprint("test", post_processes=[test_without_typing])

        test = Blueprint("test")

        with self.assertRaises(InvalidRPCMethod):

            @test.register(pre_processes=[test_without_typing])
            def test_message(request: TestMessage, context) -> TestMessage:
                return TestMessage(test_name=request.test_name)

        with self.assertRaises(InvalidRPCMethod):

            @test.register(post_processes=[test_without_typing])
            def test_message(request: TestMessage, context) -> TestMessage:
                return TestMessage(test_name=request.test_name)

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

        @test.register
        def test_message(request: TestMessage, context) -> TestMessage:
            return TestMessage(test_name=request.test_name)

        with self.assertRaises(DuplicatedRPCMethod):

            @test.register
            def test_message(request: TestMessage, context) -> TestMessage:
                return TestMessage(test_name=request.test_name)

    def test_register_process(self):
        def test_process(request: TestMessage, context) -> TestMessage:
            return TestMessage(test_name=request.test_name)

        test = Blueprint(
            "test",
            pre_processes=[test_process],
            post_processes=[test_process])

        @test.register(pre_processes=[test_process])
        def test_message(request: TestMessage, context) -> TestMessage:
            return TestMessage(test_name=request.test_name)

        self.assertListEqual(test_message.pre_processes,
                             [test_process, test_process])
        self.assertListEqual(test_message.post_processes, [test_process])
