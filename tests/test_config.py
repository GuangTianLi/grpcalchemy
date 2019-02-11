import json
import os

from grpcalchemy.config import Config

from .test_grpcalchemy import TestGrpcalchemy


class TestStrObject:
    TEMPLATE_PATH = "test"
    TEST = "test"


class TestConfig(TestGrpcalchemy):
    json_file = "test.json"

    @classmethod
    def setUpClass(cls):
        with open(cls.json_file, "w") as fp:
            json.dump({"JSON_TEST": "JSON_TEST"}, fp)

    @classmethod
    def tearDownClass(cls):
        os.remove(cls.json_file)

    def test_default_config_update_from_object(self):
        class TestObject:
            TEMPLATE_PATH = "test"
            TEST = "test"

        config = Config()
        config.from_object(TestObject)

        self.assertEqual("test", config["TEMPLATE_PATH"])
        self.assertEqual("test", config["TEST"])

    def test_default_config_update_from_json_file(self):
        class TestObject:
            __json_file__ = self.json_file

        config = Config()
        config.from_object(TestObject)

        self.assertEqual("JSON_TEST", config["JSON_TEST"])

    def test_default_config_update_from_str(self):
        config = Config()
        config.from_object("tests.test_config.TestStrObject")

        self.assertEqual("test", config["TEMPLATE_PATH"])
        self.assertEqual("test", config["TEST"])
