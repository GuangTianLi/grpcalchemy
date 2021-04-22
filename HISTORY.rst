=======
History
=======

0.7.*(2021-03-20)
--------------------

* Remove Default Feature in Message
* Refactor Composite Message Type
* Support gRPC with xDS
* Add `PROTO_AUTO_GENERATED` setting to make runtime proto generation optional

0.6.*(2020-10-27)
--------------------

* fix [#36] compatibility in windows
* fix [#34] compatibility in windows
* gRPC-Health Checking and Reflection Support (Alpha)
* Multiple Processor Support

0.5.0(2020-04-27)
--------------------

* Support Streaming Method
* Deprecate request parameter in app context and handle exception

0.4.0(2019-09-24)
--------------------

* Support related directory path to generate protocol buffer files
* Enable use type hint to define message
* Add error handle to handle Exception
* Add ``get_blueprints`` to get blueprints need to register

0.3.0(2019-08-19)
--------------------

https://github.com/GuangTianLi/grpcalchemy/projects/1

0.2.7-10(2019-04-16)
----------------------

* Support SSL
* Improve Implement of Server with grpc.server
* Support YAML file in Config Module
* Improve Config Module
* Add context in current rpc

0.2.5-6(2019-03-06)
---------------------

* Implement Rpc Context
* Improve Config Module

0.2.4(2019-03-01)
---------------------

* Implement Globals Variable
* Implement APP Context

0.2.2-3 (2019-02-26)
---------------------

* Improve Config module
* Improve rpc_call_wrap

0.2.1 (2019-02-14)
---------------------

* Implement Own gRPC Server
* Implement gRPC Server Test Client

0.2.0 (2019-01-30)
---------------------

* Change gRPCAlchemy Server register to register_blueprint
* Make gRPCAlchemy Server inherit from Blueprint
* Support Json Format
* Support Inheritance Message

0.1.6 (2019-01-21)
------------------

* Various bug-fixes
* Improve tests
* Change Client API
* Add PreProcess And PostProcess
* Import Config Object
* Add Event Listener
* Change Field Object Into Descriptor

0.1.5 (2018-12-14)
------------------

* Various bug-fixes
* Improve tests
* Add client

0.1.4 (2018-12-11)
------------------

* First release on PyPI.
