import multiprocessing
import sys
import time
import unittest

from grpc import insecure_channel

from grpcalchemy import grpcmethod, Server, DefaultConfig, Context
from grpcalchemy.orm import Message
from tests.test_grpcalchemy import TestGRPCAlchemy


@unittest.skipIf(bool(sys.platform == "darwin"), "Need recompile grcpio in MacOS")
class MultipleProcessServerTestCase(TestGRPCAlchemy):
    def setUp(unittest_self):
        super().setUp()

        class EmptyMessage(Message):
            ...

        class TestService(Server):
            @grpcmethod
            def Sleep(self, request: EmptyMessage, context: Context) -> EmptyMessage:
                self.logger.info("test")
                time.sleep(1)
                return EmptyMessage()

        class TestConfig(DefaultConfig):
            GRPC_SERVER_MAX_WORKERS = 1
            GRPC_SERVER_PROCESS_COUNT = 2

            GRPC_SERVER_PORT = 50000

        TestService.run(config=TestConfig(), block=False)
        unittest_self.app = TestService

    def tearDown(self) -> None:
        for work in self.app.workers:
            work.terminate()

    def _send_request(self):
        from protos.testservice_pb2_grpc import TestServiceStub
        from protos.emptymessage_pb2 import EmptyMessage

        with insecure_channel(
            "localhost:50000", options=[("grpc.so_reuseport", 1)]
        ) as channel:
            TestServiceStub(channel).Sleep(EmptyMessage())

    def test_multiple_processor(self):
        workers = []
        # magic sleep for test multiple processor
        time.sleep(2)
        start = time.perf_counter()
        for _ in range(4):
            worker = multiprocessing.Process(target=self._send_request)
            worker.start()
            workers.append(worker)
        for worker in workers:
            worker.join()
        end = time.perf_counter()
        self.assertLess(end - start, 4)


if __name__ == "__main__":
    unittest.main()
