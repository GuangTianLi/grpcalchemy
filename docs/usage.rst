=====
Usage
=====

To use gRPCAlchemy in a project:

.. code-block:: python

    from grpcalchemy.blueprint import Blueprint, Context
    from grpcalchemy.orm import Message, StringField
    from grpcalchemy.server import Server

    class HelloMessage(Message):
        __filename__ = 'hello'
        name = StringField()

    hello = Blueprint("hello")

    @hello.register
    def test(request: HelloMessage, context: Context) -> HelloMessage:
        return HelloMessage(name=f"Hello {request.name}")

    if __name__ == '__main__':
        app = Server()
        app.register(hello_world)
        app.run()
