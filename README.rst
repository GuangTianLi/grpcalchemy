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
----------------

 | Disclaimer: Still at an early stage of development. Rapidly evolving APIs.

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
    from grpcalchemy import Server, Context

    app = Server('server')

    class HelloMessage(Message):
        __filename__ = 'hello'
        text = StringField()

    @app.register
    def test(request: HelloMessage, context: Context) -> HelloMessage:
        return HelloMessage(text=f'Hello {request.text}')

    if __name__ == '__main__':
        app.run()

Features
----------

* gPRC Service Support
* gRPC Client Support
* gRPC Message Support
    * Scalar Value Types
    * Message Types
    * Repeated Field
    * Maps
* Middleware And Listeners


TODO
-------

* All Types Support

Credits
---------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
