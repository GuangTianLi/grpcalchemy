if __name__ == '__main__':
    import timeit
    from concurrent import futures
    from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
    from typing import Type, Union

    import grpc

    from protos import test_concurrent_blueprint_pb2_grpc, testservermessage_pb2

    def fib(n: int) -> int:
        if n <= 1:
            return 1
        else:
            return fib(n - 1) + fib(n - 2)

    def grpc_call(_):
        with grpc.insecure_channel("localhost:50051") as channel:
            stub = test_concurrent_blueprint_pb2_grpc.test_concurrent_blueprintStub(
                channel)
            request = testservermessage_pb2.TestServerMessage(num=33)
            num = stub.test_message(request).num
            return num

    def main():
        with futures.ThreadPoolExecutor(max_workers=5) as executor:
            for result in executor.map(grpc_call, range(3)):
                print(result)

    def test_concurrent(Executor: Union[Type[ProcessPoolExecutor],
                                        Type[ThreadPoolExecutor]]):
        with Executor(max_workers=5) as executor:
            for result in executor.map(fib, range(33)):
                pass

        # print(timeit.timeit('main()', globals=globals(), number=1))
        print(
            timeit.timeit(
                'test_concurrent(ProcessPoolExecutor)',
                globals=globals(),
                number=1))
        print(
            timeit.timeit(
                'test_concurrent(ThreadPoolExecutor)',
                globals=globals(),
                number=1))
