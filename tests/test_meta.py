from grpcalchemy.blueprint import Blueprint, grpcmethod
from grpcalchemy.meta import __meta__
from grpcalchemy.orm import Message, ReferenceField, StringField

from tests.test_grpcalchemy import TestGRPCAlchemy


class MetaTestCase(TestGRPCAlchemy):
    def test_single_message(self):
        class TestMessage(Message):
            name = StringField()

        self.assertEqual(1, len(__meta__.keys()))
        self.assertEqual(0, len(__meta__[TestMessage.__filename__].import_files))
        self.assertEqual(1, len(__meta__[TestMessage.__filename__].messages))
        self.assertEqual(0, len(__meta__[TestMessage.__filename__].services))

        messages = __meta__[TestMessage.__filename__].messages

        self.assertEqual("TestMessage", messages[0].__name__)
        self.assertEqual(1, len(messages[0].__meta__))

    def test_single_service(self):
        class TestMessage(Message):
            name = StringField()

        class TestService(Blueprint):
            @grpcmethod
            def test_message(self, request: TestMessage, context) -> TestMessage:
                ...

        TestService.as_view()

        self.assertListEqual(
            [TestMessage.__filename__, TestService.access_file_name()],
            list(__meta__.keys()),
        )
        self.assertEqual(1, len(__meta__[TestService.access_file_name()].import_files))
        self.assertEqual(0, len(__meta__[TestService.access_file_name()].messages))
        self.assertEqual(1, len(__meta__[TestService.access_file_name()].services))

        import_files = __meta__[TestService.access_file_name()].import_files
        services = __meta__[TestService.access_file_name()].services

        self.assertSetEqual({TestMessage.__filename__}, import_files)
        self.assertEqual(TestService.access_service_name(), services[0].name)
        self.assertEqual(1, len(services[0].rpcs))

        self.assertEqual("test_message", services[0].rpcs[0].name)
        self.assertEqual("TestMessage", services[0].rpcs[0].request_cls.__name__)
        self.assertEqual("TestMessage", services[0].rpcs[0].response_cls.__name__)

    def test_multiple_messages(self):
        class TestMessageOne(Message):
            __filename__ = "test"
            name = StringField()

        class TestMessageTwo(Message):
            __filename__ = "test"
            name = StringField()

        class TestMessageThree(Message):
            name = StringField()
            ref = ReferenceField(TestMessageOne())

        self.assertEqual(2, len(__meta__.keys()))
        self.assertEqual(1, len(__meta__[TestMessageThree.__filename__].import_files))

        self.assertEqual(2, len(__meta__[TestMessageOne.__filename__].messages))
        self.assertEqual(1, len(__meta__[TestMessageThree.__filename__].messages))

    def test_multiple_services(self):
        class TestMessage(Message):
            name = StringField()

        class TestService(Blueprint):
            @classmethod
            def access_service_name(cls) -> str:
                return "test"

            @grpcmethod
            def test_message_one(self, request: TestMessage, context) -> TestMessage:
                return TestMessage(test_name=request.name)

            @grpcmethod
            def test_message_two(self, request: TestMessage, context) -> TestMessage:
                return TestMessage(test_name=request.name)

        TestService.as_view()
        services = __meta__[TestService.access_file_name()].services

        self.assertEqual(1, len(services))
        self.assertEqual(2, len(services[0].rpcs))

        class TestServiceTmp(Blueprint):
            @classmethod
            def access_service_name(cls) -> str:
                return "test"

            @grpcmethod
            def test_message_three(self, request: TestMessage, context) -> TestMessage:
                return TestMessage(test_name=request.name)

        TestServiceTmp.as_view()

        services = __meta__[TestServiceTmp.access_file_name()].services

        self.assertEqual(2, len(services))
        self.assertEqual(2, len(services[0].rpcs))
        self.assertEqual(1, len(services[1].rpcs))
