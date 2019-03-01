from grpcalchemy.blueprint import Blueprint
from grpcalchemy.meta import __meta__
from grpcalchemy.orm import Message, ReferenceField, StringField

from .test_grpcalchemy import TestGrpcalchemy


class MetaTestCase(TestGrpcalchemy):
    def test_single_message(self):
        class TestMessage(Message):
            name = StringField()

        self.assertEqual(1, len(__meta__.keys()))
        self.assertEqual(0,
                         len(__meta__[TestMessage.__filename__].import_files))
        self.assertEqual(1, len(__meta__[TestMessage.__filename__].messages))
        self.assertEqual(0, len(__meta__[TestMessage.__filename__].services))

        messages = __meta__[TestMessage.__filename__].messages

        self.assertEqual("TestMessage", messages[0].name)
        self.assertEqual(1, len(messages[0].fields))

    def test_single_service(self):
        test_blueprint = Blueprint("test")

        class TestMessage(Message):
            name = StringField()

        @test_blueprint.register
        def test_message(request: TestMessage, context) -> TestMessage:
            return TestMessage(test_name=request.name)

        self.assertListEqual(
            [test_blueprint.file_name, TestMessage.__filename__],
            list(__meta__.keys()))
        self.assertEqual(1,
                         len(__meta__[test_blueprint.file_name].import_files))
        self.assertEqual(0, len(__meta__[test_blueprint.file_name].messages))
        self.assertEqual(1, len(__meta__[test_blueprint.file_name].services))

        import_files = __meta__[test_blueprint.file_name].import_files
        services = __meta__[test_blueprint.file_name].services

        self.assertSetEqual({TestMessage.__filename__}, import_files)
        self.assertEqual(test_blueprint.name, services[0].name)
        self.assertEqual(1, len(services[0].rpcs))

        self.assertEqual("test_message", services[0].rpcs[0].name)
        self.assertEqual("TestMessage",
                         services[0].rpcs[0].request_type.__name__)
        self.assertEqual("TestMessage",
                         services[0].rpcs[0].response_type.__name__)

    def test_multiple_messages(self):
        class TestMessageOne(Message):
            __filename__ = "test"
            name = StringField()

        class TestMessageTwo(Message):
            __filename__ = "test"
            name = StringField()

        class TestMessageThree(Message):
            name = StringField()
            ref = ReferenceField(TestMessageOne)

        self.assertEqual(2, len(__meta__.keys()))
        self.assertEqual(
            1, len(__meta__[TestMessageThree.__filename__].import_files))

        self.assertEqual(2,
                         len(__meta__[TestMessageOne.__filename__].messages))
        self.assertEqual(1,
                         len(__meta__[TestMessageThree.__filename__].messages))

    def test_multiple_services(self):
        test_blueprint = Blueprint("test", file_name="test")

        class TestMessage(Message):
            name = StringField()

        @test_blueprint.register
        def test_message_one(request: TestMessage, context) -> TestMessage:
            return TestMessage(test_name=request.name)

        @test_blueprint.register
        def test_message_two(request: TestMessage, context) -> TestMessage:
            return TestMessage(test_name=request.name)

        services = __meta__[test_blueprint.file_name].services

        self.assertEqual(1, len(services))
        self.assertEqual(2, len(services[0].rpcs))

        test_blueprint_two = Blueprint("test", file_name="test")

        @test_blueprint_two.register
        def test_message_three(request: TestMessage, context) -> TestMessage:
            return TestMessage(test_name=request.name)

        services = __meta__[test_blueprint.file_name].services

        self.assertEqual(2, len(services))
        self.assertEqual(2, len(services[0].rpcs))
        self.assertEqual(1, len(services[1].rpcs))
