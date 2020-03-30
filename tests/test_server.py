from typing import Callable, ContextManager, List, Type, Dict
from unittest.mock import Mock

from grpcalchemy import Blueprint, Context, Server, grpcmethod
from grpcalchemy.orm import Message
from tests.test_grpcalchemy import TestGrpcalchemy


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

        class User(Message):
            name: str

        class Post(Message):
            content: str

        class TestMessage(Message):
            user: User
            posts: List[Post]
            tag: Dict[str, Post]

        class AppService(Server):
            @grpcmethod
            def GetName(self, request: TestMessage, context: Context) -> TestMessage:
                return TestMessage(
                    user={"name": request.user.name},
                    posts=[dict(content="")],
                    tag={"test": Post(content="")},
                )

            def before_server_start(self):
                server_start()

            def after_server_stop(self):
                server_stop()

            def process_request(
                self, request: TestMessage, context: Context
            ) -> TestMessage:
                unittest_self.assertEqual("test", request.user.name)
                app_process_request()
                return request

            def process_response(
                self, response: TestMessage, context: Context
            ) -> TestMessage:
                unittest_self.assertEqual("test", response.user.name)
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
            @grpcmethod
            def GetName(self, request: TestMessage, context: Context) -> TestMessage:
                return TestMessage(user={"name": request.user.name})

            def before_request(
                self, request: TestMessage, context: Context
            ) -> TestMessage:
                blueprint_before_request()
                unittest_self.assertEqual("test", request.user.name)
                return request

            def after_request(
                self, response: TestMessage, context: Context
            ) -> TestMessage:
                blueprint_after_request()
                unittest_self.assertEqual("test", response.user.name)
                return response

        unittest_self.app = AppService()
        unittest_self.app.run(block=False)
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
        from protos.user_pb2 import User

        with insecure_channel("0.0.0.0:50051") as channel:
            response = AppServiceStub(channel).GetName(
                TestMessage(user=User(name="test"))
            )
            self.assertEqual("test", response.user.name)
            self.assertEqual(1, self.app_process_request.call_count)
            self.assertEqual(1, self.app_process_response.call_count)
            response = BlueprintServiceStub(channel).GetName(
                TestMessage(user=User(name="test"))
            )
            self.assertEqual("test", response.user.name)
            self.assertEqual(2, self.app_process_request.call_count)
            self.assertEqual(2, self.app_process_response.call_count)
            self.assertEqual(1, self.blueprint_after_request.call_count)
            self.assertEqual(1, self.blueprint_before_request.call_count)
        self.assertEqual(2, self.enter_context.call_count)
