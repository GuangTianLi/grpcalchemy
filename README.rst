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




The Python micro framework for building gPRC application.


* Free software: MIT license
* Documentation: https://grpcalchemy.readthedocs.io.

Example
--------

.. code-block:: python

    from grpcalchemy.blueprint import Blueprint, Context
    from grpcalchemy.fields import StringField
    from grpcalchemy.orm import Message
    from grpcalchemy.server import Server

    class HelloRequest(Message):
        __filename__ = 'helloworld'
        name = StringField()

    hello_world = Blueprint("helloworld")

    @hello_world.register
    def test(request: HelloRequest, context: Context) -> HelloRequest:
        return HelloRequest(name=request.name)

    if __name__ == '__main__':
        app = Server()
        app.register(hello_world)
        app.run()

Features
--------

* TODO

Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
