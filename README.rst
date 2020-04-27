===========
gRPCAlchemy
===========


.. image:: https://img.shields.io/pypi/v/grpcalchemy.svg
        :target: https://pypi.python.org/pypi/grpcalchemy

.. image:: https://img.shields.io/travis/GuangTianLi/grpcalchemy.svg
        :target: https://travis-ci.org/GuangTianLi/grpcalchemy

.. image:: https://readthedocs.org/projects/grpcalchemy/badge/?version=latest
        :target: https://grpcalchemy.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status

.. image:: https://img.shields.io/pypi/pyversions/grpcalchemy.svg
        :target: https://pypi.org/project/grpcalchemy/

.. image:: https://codecov.io/gh/GuangTianLi/grpcalchemy/branch/master/graph/badge.svg
  :target: https://codecov.io/gh/GuangTianLi/grpcalchemy



The Python micro framework for building gPRC application.


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
        HelloService().run()

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

TODO
-------

- Test Client Support
- gRPC Client Support
    - Thoroughly Deprecate **pb2** and **pb2_grpc** file
- Multiple Processor Support
- Async Server Support
