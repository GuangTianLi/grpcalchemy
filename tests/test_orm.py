from grpcalchemy.orm import Message, StringField, Int32Field, Int64Field, \
    BooleanField, BytesField, ReferenceField, ListField, MapField
from .test_grpcalchemy import TestGrpcalchemy


class TestORM(TestGrpcalchemy):
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

        self.assertEqual("string name", Test.name)
        self.assertEqual("int32 number", Test.number)
        self.assertEqual("int64 big_number", Test.big_number)
        self.assertEqual("bool sex", Test.sex)
        self.assertEqual("bytes raw_data", Test.raw_data)

    def test_ReferenceField(self):
        """Test normal and list reference field"""

        class Test(Message):
            name = StringField()

        class TestRef(Message):
            ref_field = ReferenceField(Test)
            list_test_field = ListField(Test)
            list_int32_field = ListField(Int32Field)

        self.assertEqual("Test ref_field", TestRef.ref_field)
        self.assertEqual("repeated Test list_test_field",
                         TestRef.list_test_field)
        self.assertEqual("repeated int32 list_int32_field",
                         TestRef.list_int32_field)

    def test_MapField(self):
        class Test(Message):
            name = StringField()

        class TestRef(Message):
            map_field = MapField(StringField, Test)

        self.assertEqual("map<string, Test> map_field", TestRef.map_field)
