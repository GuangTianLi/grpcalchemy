from concurrent.futures import ProcessPoolExecutor
from os import chdir, getcwd

from grpcalchemy.blueprint import Blueprint, Context
from grpcalchemy.orm import Int32Field, Message
from grpcalchemy.server import Server

cwd = getcwd()
root_path = cwd[:cwd.rfind("grpcalchemy") + len("grpcalchemy")]
chdir(root_path)


class TestMessage(Message):
    num = Int32Field()


test_blueprint = Blueprint("test_blueprint")


def fib(n: int) -> int:
    if n <= 1:
        return 1
    else:
        return fib(n - 1) + fib(n - 2)


@test_blueprint.register
def test_message(request: TestMessage, context: Context) -> TestMessage:
    return TestMessage(num=fib(request.num))


def main(_):
    app = Server()
    app.register(test_blueprint)
    app.run()


if __name__ == '__main__':
    with ProcessPoolExecutor(max_workers=4) as executor:
        for _ in executor.map(main, range(1)):
            pass
