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
    from grpcalchemy.fields import StringField
    from grpcalchemy.orm import Message
    from grpcalchemy.server import Server

    class HelloRequest(Message):
        __filename__ = 'hello_world'
        name = StringField()

    hello_world = Blueprint("hello_world")

    @hello_world.register
    def test(request: HelloRequest, context: Context) -> HelloRequest:
        return HelloRequest(name=request.name)

    if __name__ == '__main__':
        app = Server()
        app.register(hello_world)
        app.run()

Client
========

.. code-block:: python

    from grpcalchemy.blueprint import Blueprint, Context
    from grpcalchemy.fields import StringField
    from grpcalchemy.orm import Message
    from grpcalchemy.server import Client

    class HelloRequest(Message):
        __filename__ = 'hello_world'
        name = StringField()

    hello_world = Blueprint("hello_world")

    @hello_world.register
    def test(request: HelloRequest, context: Context) -> HelloRequest:
        return HelloRequest(name=request.name)

    if __name__ == '__main__':
        with Client("localhost:50051") as client:
            client.register(hello_world)
            response = client.hello_world.test(
                HelloRequest(name="test"))

Features
--------

* TODO

Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
