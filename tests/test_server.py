from grpcalchemy import Blueprint, Context, Server, current_app, current_rpc
from grpcalchemy.client import Client
from grpcalchemy.orm import Message, StringField

from .test_grpcalchemy import TestGrpcalchemy


class ServerTestCase(TestGrpcalchemy):
    def setUp(self):
        super().setUp()
        self.app = Server('test_server')

        class TestMessage(Message):
            test_name = StringField()

        self.test_blueprint = Blueprint("test_blueprint")

        @self.test_blueprint.register
        def test_blueprint_rpc(request: TestMessage,
                               context: Context) -> TestMessage:
            return TestMessage(test_name=request.test_name)

        @self.app.register
        def test_app_rpc(request: TestMessage,
                         context: Context) -> TestMessage:
            return TestMessage(test_name=request.test_name)

        @self.app.register
        def test_current_app_rpc(request: TestMessage,
                                 context: Context) -> TestMessage:
            return TestMessage(test_name=current_app.name)

        @self.app.register
        def test_current_rpc_rpc(request: TestMessage,
                                 context: Context) -> TestMessage:
            return TestMessage(test_name=current_rpc.name)

        self.test_blueprint_rpc = test_blueprint_rpc
        self.test_app_rpc = test_app_rpc
        self.test_current_app_rpc = test_current_app_rpc
        self.test_current_rpc_rpc = test_current_rpc_rpc
        self.Message = TestMessage
        self.app.register_blueprint(self.test_blueprint)
        self.app.run(test=True)

    def tearDown(self):
        self.app.stop(0)

    def test_server(self):
        test_name = "Hello World!"
        with Client("localhost:50051") as client:
            client.register(self.test_blueprint)
            client.register(self.app)
            response = client.test_blueprint(
                rpc=self.test_blueprint_rpc,
                message=self.Message(test_name=test_name))
            self.assertEqual(test_name, response.test_name)
            response = client.test_server(
                rpc=self.test_app_rpc,
                message=self.Message(test_name=test_name))
            self.assertEqual(test_name, response.test_name)
            response = client.test_server(
                rpc=self.test_current_app_rpc,
                message=self.Message(test_name=test_name))
            self.assertEqual('test_server', response.test_name)
            response = client.test_server(
                rpc=self.test_current_rpc_rpc,
                message=self.Message(test_name=test_name))
            self.assertEqual('test_current_rpc_rpc', response.test_name)

    def test_server_listener(self):
        test_app = Server('test_server')

        @test_app.listener("before_server_start")
        def before_server_start(app: Server):
            pass

        def after_server_stop(app: Server):
            pass

        test_app.listener("after_server_stop", after_server_stop)

        self.assertListEqual([before_server_start],
                             test_app.listeners["before_server_start"])
        self.assertEqual([after_server_stop],
                         test_app.listeners["after_server_stop"])

    def test_server_config(self):
        test_app = Server('test_server', config={"TEST": "TEST"})

        self.assertEqual("TEST", test_app.config["TEST"])
