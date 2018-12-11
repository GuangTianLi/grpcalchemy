from grpcalchemy.blueprint import Blueprint
from grpcalchemy.fields import StringField
from grpcalchemy.meta import __meta__
from grpcalchemy.orm import Message
from .test_grpcalchemy import TestGrpcalchemy


class TestMeta(TestGrpcalchemy):
    def setUp(self):
        __meta__.clear()

    def test_single_message(self):
        class TestMessage(Message):
            name = StringField()

        self.assertEqual(1, len(__meta__.keys()))
        self.assertEqual(
            0, len(__meta__[TestMessage.__filename__]["import_files"]))
        self.assertEqual(1,
                         len(__meta__[TestMessage.__filename__]["messages"]))
        self.assertEqual(0,
                         len(__meta__[TestMessage.__filename__]["services"]))

        messages = __meta__[TestMessage.__filename__]["messages"]

        self.assertEqual("TestMessage", messages[0].name)
        self.assertEqual(1, len(messages[0].fields))

        del __meta__[TestMessage.__filename__]

    def test_single_service(self):
        test_blueprint = Blueprint("test")

        class TestMessage(Message):
            name = StringField()

        @test_blueprint.register
        def test_message(request: TestMessage, context) -> TestMessage:
            return TestMessage(test_name=request.name)

        self.assertEqual(2, len(__meta__.keys()))
        self.assertEqual(
            1, len(__meta__[test_blueprint.file_name]["import_files"]))
        self.assertEqual(0,
                         len(__meta__[test_blueprint.file_name]["messages"]))
        self.assertEqual(1,
                         len(__meta__[test_blueprint.file_name]["services"]))

        import_files = __meta__[test_blueprint.file_name]["import_files"]
        services = __meta__[test_blueprint.file_name]["services"]

        self.assertSetEqual({TestMessage.__filename__}, import_files)
        self.assertEqual(test_blueprint.name, services[0].name)
        self.assertEqual(1, len(services[0].rpcs))

        self.assertEqual("test_message", services[0].rpcs[0].name)
        self.assertEqual("TestMessage", services[0].rpcs[0].request)
        self.assertEqual("TestMessage", services[0].rpcs[0].response)

        del __meta__[TestMessage.__filename__]
        del __meta__[test_blueprint.file_name]
