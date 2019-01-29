import timeit
from concurrent import futures

import grpc

from protos import test_server_blueprint_pb2_grpc, testservermessage_pb2


def grpc_call(_):
    with grpc.insecure_channel("localhost:50051") as channel:
        stub = test_server_blueprint_pb2_grpc.test_server_blueprintStub(
            channel)
        request = testservermessage_pb2.TestServerMessage(num=33)
        num = stub.test_message(request).num
        return num


def main():
    with futures.ThreadPoolExecutor(max_workers=5) as executor:
        for result in executor.map(grpc_call, range(3)):
            print(result)


if __name__ == '__main__':
    print(timeit.timeit('main()', globals=globals(), number=1))
