===========
gRPCAlchemy
===========


.. image:: https://img.shields.io/pypi/v/grpcalchemy.svg
        :target: https://pypi.python.org/pypi/grpcalchemy

.. image:: https://github.com/GuangTianLi/grpcalchemy/workflows/test/badge.svg
        :target: https://github.com/GuangTianLi/grpcalchemy/actions

.. image:: https://readthedocs.org/projects/grpcalchemy/badge/?version=latest
        :target: https://grpcalchemy.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status

.. image:: https://img.shields.io/pypi/pyversions/grpcalchemy.svg
        :target: https://pypi.org/project/grpcalchemy/

.. image:: https://codecov.io/gh/GuangTianLi/grpcalchemy/branch/master/graph/badge.svg
  :target: https://codecov.io/gh/GuangTianLi/grpcalchemy



The Python micro framework for building gPRC application based on official `gRPC <https://github.com/grpc/grpc>`_ project.


* Free software: MIT license
* Documentation: https://grpcalchemy.readthedocs.io.

Installation
----------------

.. code-block:: shell

    $ pipenv install grpcalchemy
    ✨🍰✨

Only **Python 3.6+** is supported.

Example
--------

Server
========

.. code-block:: python

    from grpcalchemy.orm import Message, StringField
    from grpcalchemy import Server, Context, grpcmethod

    class HelloMessage(Message):
        text: str

    class HelloService(Server):
        @grpcmethod
        def Hello(self, request: HelloMessage, context: Context) -> HelloMessage:
            return HelloMessage(text=f'Hello {request.text}')

    if __name__ == '__main__':
        HelloService.run()


Then Using gRPC channel to connect the server:

.. code-block:: python

    from grpc import insecure_channel

    from protos.helloservice_pb2_grpc import HelloServiceStub
    from protos.hellomessage_pb2 import HelloMessage

    with insecure_channel("localhost:50051") as channel:
        response = HelloServiceStub(channel).Hello(
            HelloMessage(text="world")
        )

Features
----------

- gPRC Service Support
- gRPC Message Support
    - Scalar Value Types
    - Message Types
    - Repeated Field
    - Maps
- Define Message With Type Hint
- Middleware
- App Context Manger
- Error Handler Support
- Streaming Method Support
- gRPC-Health Checking and Reflection Support (Alpha)
- Multiple Processor Support

TODO
-------

- Test Client Support
- Async Server Support
