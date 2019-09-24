from typing import Callable, ContextManager, List, Type
from unittest.mock import Mock

from grpcalchemy import Blueprint, Context, Server, grpcservice, DefaultConfig
from grpcalchemy.orm import Message, StringField
from .test_grpcalchemy import TestGrpcalchemy


class ServerTestCase(TestGrpcalchemy):
    def setUp(unittest_self):
        super().setUp()
        server_start = Mock()
        server_stop = Mock()
        app_process_request = Mock()
        app_process_response = Mock()
        blueprint_before_request = Mock()
        blueprint_after_request = Mock()
        enter_context = Mock()

        class TestConfig(DefaultConfig):
            GRPC_SERVER_TEST = True

        class TestMessage(Message):
            name = StringField()

        class AppService(Server):
            @grpcservice
            def GetName(self, request: TestMessage, context: Context) -> TestMessage:
                return TestMessage(name=request.name)

            def before_server_start(self):
                server_start()

            def after_server_stop(self):
                server_stop()

            def process_request(
                self, request: TestMessage, context: Context
            ) -> TestMessage:
                unittest_self.assertEqual("test", request.name)
                app_process_request()
                return request

            def process_response(
                self, response: TestMessage, context: Context
            ) -> TestMessage:
                unittest_self.assertEqual("test", response.name)
                app_process_response()
                return response

            def app_context(
                self,
                current_service: Blueprint,
                current_method: Callable,
                current_request: Message,
            ) -> ContextManager:
                enter_context()
                return super().app_context(
                    current_service, current_method, current_request
                )

            def get_blueprints(self) -> List[Type[Blueprint]]:
                return [BlueprintService]

        class BlueprintService(Blueprint):
            @grpcservice
            def GetName(self, request: TestMessage, context: Context) -> TestMessage:
                return TestMessage(name=request.name)

            def before_request(
                self, request: TestMessage, context: Context
            ) -> TestMessage:
                blueprint_before_request()
                unittest_self.assertEqual("test", request.name)
                return request

            def after_request(
                self, response: TestMessage, context: Context
            ) -> TestMessage:
                blueprint_after_request()
                unittest_self.assertEqual("test", response.name)
                return response

        unittest_self.app = AppService(config=TestConfig())
        unittest_self.app.run()
        unittest_self.assertEqual(1, server_start.call_count)
        unittest_self.server_stop = server_stop

        unittest_self.app_process_request = app_process_request
        unittest_self.app_process_response = app_process_response
        unittest_self.blueprint_after_request = blueprint_after_request
        unittest_self.blueprint_before_request = blueprint_before_request
        unittest_self.enter_context = enter_context

    def tearDown(self):
        self.app.stop(0)
        self.assertEqual(1, self.server_stop.call_count)

    def test_server(self):
        from grpc import insecure_channel
        from protos.appservice_pb2_grpc import AppServiceStub
        from protos.blueprintservice_pb2_grpc import BlueprintServiceStub
        from protos.testmessage_pb2 import TestMessage

        with insecure_channel("0.0.0.0:50051") as channel:
            response = AppServiceStub(channel).GetName(TestMessage(name="test"))
            self.assertEqual("test", response.name)
            self.assertEqual(1, self.app_process_request.call_count)
            self.assertEqual(1, self.app_process_response.call_count)
            response = BlueprintServiceStub(channel).GetName(TestMessage(name="test"))
            self.assertEqual("test", response.name)
            self.assertEqual(2, self.app_process_request.call_count)
            self.assertEqual(2, self.app_process_response.call_count)
            self.assertEqual(1, self.blueprint_after_request.call_count)
            self.assertEqual(1, self.blueprint_before_request.call_count)
        self.assertEqual(2, self.enter_context.call_count)
