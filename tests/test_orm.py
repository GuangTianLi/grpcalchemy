import json
from typing import List, Dict

from grpcalchemy.orm import (
    BooleanField,
    BytesField,
    Int32Field,
    Int64Field,
    ListField,
    MapField,
    Message,
    ReferenceField,
    StringField,
)
from grpcalchemy.utils import generate_proto_file
from tests.test_grpcalchemy import TestGrpcalchemy


class ORMTestCase(TestGrpcalchemy):
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

        class Test(Message):
            name = StringField()
            number = Int32Field()
            big_number = Int64Field()
            active = BooleanField()
            deleted = BooleanField()
            raw_data = BytesField()

        self.assertEqual("int64 big_number", str(Test.big_number))

        class TestWithTyping(Message):
            name: str
            number: int
            active: bool
            deleted: bool
            raw_data: bytes

        for object in [TestWithTyping]:
            self.assertEqual("string name", str(object.name))
            self.assertEqual("int32 number", str(object.number))
            self.assertEqual("bool active", str(object.active))
            self.assertEqual("bool deleted", str(object.deleted))
            self.assertEqual("bytes raw_data", str(object.raw_data))

    def test_ReferenceField(self):
        """Test normal and list reference field"""

        class Test(Message):
            name = StringField()

        class TestRef(Message):
            ref_field = ReferenceField(Test())
            list_test_field = ListField(ReferenceField(Test()))
            list_int_field = ListField(Int64Field())

        class TestWithTyping(Message):
            name: str

        class TestRefWithTyping(Message):
            ref_field: TestWithTyping
            list_test_field: List[TestWithTyping]
            list_int_field: List[int]

        for object in [TestRef, TestRefWithTyping]:
            self.assertEqual([], object().list_test_field)
            self.assertEqual([], object().list_int_field)

            test = object(
                ref_field=Test(name="Test"),
                list_test_field=[Test(name="Test")],
                list_int_field=[1],
            )
            self.assertEqual("Test", test.ref_field.name)
            test.ref_field.name = "Changed_name"
            self.assertEqual("Changed_name", test.ref_field.name)
            self.assertListEqual([1], list(test.list_int_field))
            self.assertEqual("Test", test.list_test_field[0].name)

            self.assertEqual("Test ref_field", str(TestRef.ref_field))
            self.assertEqual(
                "repeated Test list_test_field", str(TestRef.list_test_field)
            )
            self.assertEqual(
                "repeated int64 list_int_field", str(TestRef.list_int_field)
            )

    def test_MapField(self):
        class Test(Message):
            name = StringField()

        class TestMapRef(Message):
            map_field = MapField(StringField(), ReferenceField(Test()))

        class TestWithTyping(Message):
            name: str

        class TestMapRefWithTyping(Message):
            map_field: Dict[str, TestWithTyping]

        for object in [TestMapRef, TestMapRefWithTyping]:
            test = object(map_field={"test": Test(name="test")})
            self.assertEqual("test", test.map_field["test"].name)
            self.assertEqual("test", test.__message__.map_field["test"].name)
            self.assertEqual("map<string, Test> map_field", str(TestMapRef.map_field))

    def test_inheritance(self):
        class Post(Message):
            title = StringField()

        class TextPost(Post):
            content = StringField()

        test = TextPost(content="test", title="test_title")
        self.assertEqual("test", test.content)
        self.assertEqual("test_title", test.title)

    def test_json_format(self):
        class Test(Message):
            name: str

        class TestJsonFormat(Message):
            ref_field: Test
            list_test_field: List[Test]
            list_int32_field: List[int]
            map_field: Dict[str, Test]

        generate_proto_file()

        test = TestJsonFormat(
            ref_field=Test(name="Test"),
            list_test_field=[Test(name="Test")],
            list_int32_field=range(10),
            map_field={"test": Test(name="Test")},
        )
        dict_test = {
            "ref_field": {"name": "Test"},
            "list_test_field": [{"name": "Test"}],
            "list_int32_field": list(range(10)),
            "map_field": {"test": {"name": "Test"}},
        }
        self.assertDictEqual(dict_test, test.message_to_dict())
        self.assertDictEqual(dict_test, json.loads(test.message_to_json()))

    def test_field_default_value(self):
        class Test(Message):
            name: str
            number: int
            big_number = Int64Field()
            active: bool
            raw_data: bytes

        test = Test()
        self.assertEqual("", test.name)
        self.assertEqual(0, test.number)
        self.assertEqual(0, test.big_number)
        self.assertEqual(False, test.active)
        self.assertEqual(b"", test.raw_data)

        test.name = "changed"
        self.assertEqual("changed", test.name)
        test.name = None
        self.assertEqual("", test.name)
