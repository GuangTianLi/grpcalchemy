from grpcalchemy.fields import StringField, Int32Field, Int64Field, \
    BoolField, BytesField, ReferenceField, ListField, MapField
from grpcalchemy.orm import Message
from .test_grpcalchemy import TestGrpcalchemy


class TestORM(TestGrpcalchemy):
    def test_message_with_default_filename(self):
        """Test default filename."""

        class Test(Message):
            pass

        self.assertEqual("test", Test.__filename__)
        self.assertEqual("Test", Test.__name__)

    def test_message_with_specific_filename(self):
        """Test specific filename."""

        class Test(Message):
            __filename__ = "specified"

        self.assertEqual("specified", Test.__filename__)

    def test_field_str(self):
        """Test field to str."""

        class Test(Message):
            name = StringField()
            number = Int32Field()
            big_number = Int64Field()
            sex = BoolField()
            raw_data = BytesField()

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

        self.assertEqual("Test ref_field", str(TestRef.ref_field))
        self.assertEqual("repeated Test list_test_field",
                         str(TestRef.list_test_field))
        self.assertEqual("repeated int32 list_int32_field",
                         str(TestRef.list_int32_field))

    def test_MapField(self):
        class Test(Message):
            name = StringField()

        class TestRef(Message):
            map_field = MapField(StringField, Test)

        self.assertEqual("map<string, Test> map_field", str(TestRef.map_field))
