from grpcalchemy.orm import default_config
from .test_grpcalchemy import TestGrpcalchemy


class TestStrObject:
    TEMPLATE_PATH = "test"
    TEST = "test"


class TestMeta(TestGrpcalchemy):
    def test_default_config_update_from_object(self):
        class TestObject:
            TEMPLATE_PATH = "test"
            TEST = "test"

        default_config.from_object(TestObject)

        self.assertEqual("test", default_config["TEMPLATE_PATH"])
        self.assertEqual("test", default_config["TEST"])

    def test_default_config_update_from_str(self):

        default_config.from_object("tests.test_config.TestStrObject")

        self.assertEqual("test", default_config["TEMPLATE_PATH"])
        self.assertEqual("test", default_config["TEST"])
