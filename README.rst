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




The Python micro framework for building gPRC application.


* Free software: MIT license
* Documentation: https://grpcalchemy.readthedocs.io.

Installation
--------

 | Disclaimer: Still at an early stage of development. Rapidly evolving APIs.

.. code-block:: shell

    $ pipenv install -e git+https://github.com/GuangTianLi/grpcalchemy#egg=grpcalchemy
    ✨🍰✨

Only **Python 3.6+** is supported.

Example
--------

Server
========

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

Client
========

.. code-block:: python

    from grpcalchemy.blueprint import Blueprint, Context
    from grpcalchemy.client import Client
    from grpcalchemy.orm import Message, StringField


    class HelloMessage(Message):
        __filename__ = 'hello'
        name = StringField()


    hello = Blueprint("hello")


    @hello.register
    def test(request: HelloMessage, context: Context) -> HelloMessage:
        return HelloMessage(name=f"Hello {request.name}")


    if __name__ == '__main__':
        with Client("localhost:50051") as client:
            client.register(hello)
            response = client.hello.test(HelloMessage(name="world"))
            print(response.name)  # Hello world

Features
--------

* gPRC Service Support
* gRPC Client Support
* gRPC Message Support
    * Scalar Value Types
    * Message Types
    * Repeated Field

TODO
-------

* All Types Support

Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
