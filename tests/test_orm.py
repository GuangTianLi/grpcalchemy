import json

from grpcalchemy.orm import (
    BooleanField,
    BytesField,
    Int32Field,
    Int64Field,
    RepeatedField,
    MapField,
    Message,
    ReferenceField,
    StringField,
)
from grpcalchemy.types import Map, Repeated
from tests.test_grpcalchemy import TestGRPCAlchemy


class TestORMMessage(Message):
    __filename__ = "test_orm"


class SimpleMessage(TestORMMessage):
    name: str


class ScalarTypeMessage(TestORMMessage):
    name = StringField()
    number = Int32Field()
    big_number = Int64Field()
    active = BooleanField()
    deleted = BooleanField()
    raw_data = BytesField()


class ScalarTypeMessageWithTyping(ScalarTypeMessage):
    name: str
    number: int
    active: bool
    deleted: bool
    raw_data: bytes


class CompositeMessage(TestORMMessage):
    ref_field = ReferenceField(SimpleMessage())
    list_test_field = RepeatedField(ReferenceField(SimpleMessage()))
    list_int_field = RepeatedField(Int32Field())
    map_field = MapField(StringField(), ReferenceField(SimpleMessage()))


class CompositeMessageTyping(TestORMMessage):
    ref_field: SimpleMessage
    list_test_field: Repeated[SimpleMessage]
    list_int_field: Repeated[int]
    map_field: Map[str, SimpleMessage]


TestGRPCAlchemy.generate_proto_file()


class ORMTestCase(TestGRPCAlchemy):
    def test_message_with_default_filename(self):
        class Test(Message):
            pass

        self.assertEqual("test", Test.__filename__)
        self.assertEqual("Test", Test.__name__)

    def test_message_with_specific_filename(self):
        class Test(Message):
            __filename__ = "specified"

        class TempTest(Test):
            ...

        self.assertEqual("specified", Test.__filename__)
        self.assertEqual("specified", TempTest.__filename__)

    def test_field_str(self):
        """Test field to str."""

        for message_cls in [ScalarTypeMessageWithTyping, ScalarTypeMessage]:
            self.assertEqual("string name", str(message_cls.name))
            self.assertEqual("int64 big_number", str(message_cls.big_number))
            self.assertEqual("int32 number", str(message_cls.number))
            self.assertEqual("bool active", str(message_cls.active))
            self.assertEqual("bool deleted", str(message_cls.deleted))
            self.assertEqual("bytes raw_data", str(message_cls.raw_data))

            message = message_cls()
            self.assertEqual("", message.name)
            self.assertEqual(0, message.number)
            self.assertEqual(0, message.big_number)
            self.assertEqual(False, message.active)
            self.assertEqual(b"", message.raw_data)

            message.name = "changed"
            self.assertEqual("changed", message.name)

    def test_composite_message(self):
        for message_cls in [CompositeMessage, CompositeMessageTyping]:
            message = message_cls(
                ref_field=SimpleMessage(name="Test"),
                list_test_field=[SimpleMessage(name="Test")],
                list_int_field=range(1),
                map_field={"test": SimpleMessage(name="Test")},
            )
            self.assertEqual("Test", message.ref_field.name)
            message.ref_field.name = "Changed"
            self.assertEqual("Changed", message.ref_field.name)
            self.assertListEqual([0], list(message.list_int_field))
            self.assertEqual("Test", message.list_test_field[0].name)
            self.assertEqual("Test", message.map_field["test"].name)
            self.assertEqual("Test", message.__message__.map_field["test"].name)

            self.assertEqual("SimpleMessage ref_field", str(message_cls.ref_field))
            self.assertEqual(
                "repeated SimpleMessage list_test_field",
                str(message_cls.list_test_field),
            )
            self.assertEqual(
                "repeated int32 list_int_field", str(message_cls.list_int_field)
            )
            self.assertEqual(
                "map<string, SimpleMessage> map_field", str(message_cls.map_field)
            )

            dict_test = {
                "ref_field": {"name": "Changed"},
                "list_test_field": [{"name": "Test"}],
                "list_int_field": [0],
                "map_field": {"test": {"name": "Test"}},
            }
            self.assertDictEqual(dict_test, message.message_to_dict())
            self.assertDictEqual(dict_test, json.loads(message.message_to_json()))
