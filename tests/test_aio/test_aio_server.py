import unittest
from typing import Callable, ContextManager, List, Type
from unittest.mock import Mock

from google.protobuf.json_format import MessageToDict
from grpc import insecure_channel
from grpc_health.v1.health_pb2 import HealthCheckRequest
from grpc_health.v1.health_pb2_grpc import HealthStub
from grpc_reflection.v1alpha.reflection_pb2 import ServerReflectionRequest
from grpc_reflection.v1alpha.reflection_pb2_grpc import ServerReflectionStub

from grpcalchemy import Blueprint, Context, grpcmethod, DefaultConfig, Streaming
from grpcalchemy.aio import Server
from grpcalchemy.orm import Message
from grpcalchemy.types import Map, Repeated
from tests.test_grpcalchemy import TestGRPCAlchemy


class AioServerTestCase(TestGRPCAlchemy):
    def setUp(unittest_self):
        super().setUp()

        server_start = Mock()
        server_stop = Mock()
        app_process_request = Mock()
        app_process_response = Mock()
        blueprint_before_request = Mock()
        blueprint_after_request = Mock()
        enter_context = Mock()

        class ServerTestMessage(Message):
            __filename__ = "test_server"

        class User(ServerTestMessage):
            name: str

        class Post(ServerTestMessage):
            content: str

        class TestServerMessage(ServerTestMessage):
            user: User
            posts: Repeated[Post]
            tag: Map[str, Post]

        class AppService(Server):
            def before_server_start(self):
                server_start()

            def after_server_stop(self):
                server_stop()

            def process_request(
                self, request: TestServerMessage, context: Context
            ) -> TestServerMessage:
                unittest_self.assertIn(
                    request.user.name, {"unary_unary", "unary_stream"}
                )
                app_process_request()
                return request

            def process_response(
                self, response: TestServerMessage, context: Context
            ) -> TestServerMessage:
                unittest_self.assertIn(
                    response.user.name, {"unary_unary", "stream_unary"}
                )
                app_process_response()
                return response

            def app_context(
                self,
                current_service: Blueprint,
                current_method: Callable,
                context: Context,
            ) -> ContextManager:
                enter_context()
                return super().app_context(current_service, current_method, context)

            @classmethod
            def get_blueprints(cls) -> List[Type[Blueprint]]:
                return [BlueprintService]

        class BlueprintService(Blueprint):
            @grpcmethod
            def UnaryUnary(
                self, request: TestServerMessage, context: Context
            ) -> TestServerMessage:
                return TestServerMessage(
                    user={"name": "unary_unary"},
                    posts=[dict(content=request.user.name)],
                    tag={"test": Post(content="")},
                )

            @grpcmethod
            def UnaryStream(
                self, request: TestServerMessage, context: Context
            ) -> Streaming[TestServerMessage]:
                yield TestServerMessage(
                    user={"name": "unary_stream"},
                    posts=[dict(content=request.user.name)],
                    tag={"test": Post(content="")},
                )

            @grpcmethod
            def StreamUnary(
                self, request: Streaming[TestServerMessage], context: Context
            ) -> TestServerMessage:
                return TestServerMessage(
                    user={"name": "stream_unary"},
                    posts=[dict(content=r.user.name) for r in request],
                    tag={"test": Post(content="")},
                )

            @grpcmethod
            def StreamStream(
                self, request: Streaming[TestServerMessage], context: Context
            ) -> Streaming[TestServerMessage]:
                yield TestServerMessage(
                    user={"name": "stream_stream"},
                    posts=[dict(content=r.user.name) for r in request],
                    tag={"test": Post(content="")},
                )

            def before_request(
                self, request: TestServerMessage, context: Context
            ) -> TestServerMessage:
                blueprint_before_request()
                unittest_self.assertIn(
                    request.user.name, {"unary_unary", "unary_stream"}
                )
                return request

            def after_request(
                self, response: TestServerMessage, context: Context
            ) -> TestServerMessage:
                blueprint_after_request()
                unittest_self.assertIn(
                    response.user.name, {"unary_unary", "stream_unary"}
                )
                return response

        unittest_self.app = AppService.run(config=unittest_self.config, block=False)
        unittest_self.assertEqual(1, server_start.call_count)
        unittest_self.server_stop = server_stop

        unittest_self.app_process_request = app_process_request
        unittest_self.app_process_response = app_process_response
        unittest_self.blueprint_after_request = blueprint_after_request
        unittest_self.blueprint_before_request = blueprint_before_request
        unittest_self.enter_context = enter_context

    def test_something(self):
        self.assertEqual(True, False)


if __name__ == "__main__":
    unittest.main()
