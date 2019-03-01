import json

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

from .test_grpcalchemy import TestGrpcalchemy


class ORMTestCase(TestGrpcalchemy):
    def setUp(self):
        super().setUp()

    def test_message_with_default_filename(self):
        class Test(Message):
            pass

        self.assertEqual("test", Test.__filename__)
        self.assertEqual("Test", Test.__name__)

    def test_message_with_specific_filename(self):
        class Test(Message):
            __filename__ = "specified"

        self.assertEqual("specified", Test.__filename__)

    def test_field_str(self):
        """Test field to str."""

        class Test(Message):
            name = StringField()
            number = Int32Field()
            big_number = Int64Field()
            sex = BooleanField()
            raw_data = BytesField()

        generate_proto_file()

        test = Test(name="Test")
        self.assertEqual("Test", test.name)
        test = Test()
        test.name = "Changed_name"
        self.assertEqual("Changed_name", test.name)
        self.assertEqual("Changed_name", test._message.name)

        self.assertEqual("string name", str(Test.name))
        self.assertEqual("int32 number", str(Test.number))
        self.assertEqual("int64 big_number", str(Test.big_number))
        self.assertEqual("bool sex", str(Test.sex))
        self.assertEqual("bytes raw_data", str(Test.raw_data))

    def test_ReferenceField(self):
        """Test normal and list reference field"""

        class Test(Message):
            name = StringField()

        class TestRef(Message):
            ref_field = ReferenceField(Test)
            list_test_field = ListField(Test)
            list_int32_field = ListField(Int32Field)

        generate_proto_file()

        test = TestRef(
            ref_field=Test(name="Test"),
            list_test_field=[Test(name="Test")],
            list_int32_field=[1])
        self.assertEqual("Test", test.ref_field.name)
        test.ref_field.name = "Changed_name"
        self.assertEqual("Changed_name", test.ref_field.name)
        self.assertListEqual([1], list(test.list_int32_field))
        self.assertEqual("Test", test.list_test_field[0].name)

        self.assertEqual("Test ref_field", str(TestRef.ref_field))
        self.assertEqual("repeated Test list_test_field",
                         str(TestRef.list_test_field))
        self.assertEqual("repeated int32 list_int32_field",
                         str(TestRef.list_int32_field))

    def test_MapField(self):
        class Test(Message):
            name = StringField()

        class TestMapRef(Message):
            map_field = MapField(StringField, Test)

        generate_proto_file()

        test = TestMapRef(map_field={"test": Test(name="test")})
        self.assertEqual("test", test.map_field["test"].name)
        self.assertEqual("test", test._message.map_field["test"].name)
        self.assertEqual("map<string, Test> map_field",
                         str(TestMapRef.map_field))

    def test_inheritance(self):
        class Post(Message):
            title = StringField()

        class TextPost(Post):
            content = StringField()

        generate_proto_file()

        test = TextPost(content="test", title="test_title")
        self.assertEqual("test", test.content)
        self.assertEqual("test_title", test.title)

    def test_json_format(self):
        class Test(Message):
            name = StringField()

        class TestJsonFormat(Message):
            ref_field = ReferenceField(Test)
            list_test_field = ListField(Test)
            list_int32_field = ListField(Int32Field)
            map_field = MapField(StringField, Test)

        generate_proto_file()
        test = TestJsonFormat(
            ref_field=Test(name="Test"),
            list_test_field=[Test(name="Test")],
            list_int32_field=[1],
            map_field={"test": Test(name="Test")})

        dict_test = {
            "ref_field": {
                "name": "Test"
            },
            "list_test_field": [{
                "name": "Test"
            }],
            "list_int32_field": [1],
            "map_field": {
                "test": {
                    "name": "Test"
                }
            },
        }
        self.assertDictEqual(
            dict_test, test.message_to_dict(preserving_proto_field_name=True))
        self.assertDictEqual(
            dict_test,
            json.loads(test.message_to_json(preserving_proto_field_name=True)))
