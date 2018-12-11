=====
Usage
=====

To use gRPCAlchemy in a project:

.. code-block:: python

    from grpcalchemy.blueprint import Blueprint
    from grpcalchemy.fields import StringField
    from grpcalchemy.orm import Message
    from grpcalchemy.server import Server

    class HelloRequest(Message):
        __filename__ = 'helloworld'
        name = StringField()

    hello_world = Blueprint("helloworld")

    @hello_world.register
    def test(request: HelloRequest, context) -> HelloRequest:
        return HelloRequest(name=request.name)

    if __name__ == '__main__':
        app = Server()
        app.register(hello_world)
        app.run()
