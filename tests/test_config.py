import json
import os
import unittest

import yaml

from grpcalchemy.config import Config


class TestStrObject:
    TEMPLATE_PATH = "default"
    TEST = "test"


default_config = Config(obj=TestStrObject)


class ConfigTestCase(unittest.TestCase):
    json_file = "test.json"
    yaml_file = "test.yaml"

    @classmethod
    def setUpClass(cls):
        with open(cls.json_file, "w") as fp:
            json.dump({"JSON_TEST": "JSON_TEST"}, fp)
        with open(cls.yaml_file, "w") as fp:
            yaml.dump({"YAML_TEST": "YAML_TEST"}, fp)

    @classmethod
    def tearDownClass(cls):
        os.remove(cls.json_file)
        os.remove(cls.yaml_file)

    def test_default_config_init_from_object(self):
        class TestObject:
            TEST = "test"

        config = Config(obj=TestObject)

        self.assertEqual("test", config["TEST"])
        with self.assertRaises(KeyError):
            _ = config['NOT_EXIST']

        self.assertEqual("NOT_EXIST", config.get('NOT_EXIST', 'NOT_EXIST'))
        self.assertTrue('TEST' in config)
        self.assertEqual(1, len(config))
        self.assertListEqual(['TEST'], [_ for _ in config])
        config['TEST'] = 'changed'
        self.assertEqual('changed', config['TEST'])

    def test_default_config_init_from_str(self):
        config = Config(obj='tests.test_config.TestStrObject')

        self.assertEqual("default", config["TEMPLATE_PATH"])

    def test_default_config_update_from_json(self):
        class TestObject:
            CONFIG_FILE = self.json_file

            JSON_TEST = "default"

        config = Config(obj=TestObject)

        self.assertEqual("JSON_TEST", config["JSON_TEST"])

    def test_default_config_update_from_yaml(self):
        class TestObject:
            CONFIG_FILE = self.yaml_file

            YAML_TEST = "default"

        config = Config(obj=TestObject)

        self.assertEqual("YAML_TEST", config["YAML_TEST"])

    def test_config_with_env(self):
        os.environ["test_TEST"] = "changed"

        class TestObject:
            ENV_PREFIX = "test_"
            TEST = "default"

        self.assertEqual("changed", Config(obj=TestObject)["TEST"])
        os.unsetenv("test_TEST")

    def test_update_config_from_remote_center(self):
        def get_config(current_config: dict) -> dict:
            self.assertTrue(current_config['ENABLE_CONFIG_LIST'])
            return {"TEST": "changed"}

        class TestObject:
            ENABLE_CONFIG_LIST = True
            TEST = "default"

        config = Config(obj=TestObject, sync_access_config_list=[get_config])
        self.assertEqual("changed", config["TEST"])

    def test_async_update_config_from_remote_center(self):
        async def get_config_async(current_config: dict) -> dict:
            self.assertTrue(current_config['ENABLE_CONFIG_LIST'])
            return {"TEST": "changed"}

        class TestObject:
            ENABLE_CONFIG_LIST = True
            TEST = "default"

        config = Config(
            obj=TestObject, async_access_config_list=[get_config_async])
        self.assertEqual("changed", config["TEST"])

    def test_config_priority(self):
        os.environ["test_FOURTH"] = "3"
        current_json_file = "test_priority.json"

        def get_config(current_config: dict) -> dict:
            return {
                "SECOND": "1",
                "FOURTH": "1",
            }

        async def get_config_async(current_config: dict) -> dict:
            return {
                "THIRD": 1,
                "FOURTH": 1,
            }

        with open(current_json_file, "w") as fp:
            json.dump({
                "THIRD": "2",
                "FOURTH": "2",
            }, fp)

        class TestPriority:
            ENABLE_CONFIG_LIST = True
            # env
            ENV_PREFIX = "test_"
            # file
            CONFIG_FILE = current_json_file

            FIRST = 0
            SECOND = "0"
            THIRD = "0"
            FOURTH = 0

        config = Config(
            obj=TestPriority,
            sync_access_config_list=[get_config],
            async_access_config_list=[get_config_async])
        self.assertEqual(0, config["FIRST"])
        self.assertEqual("1", config["SECOND"])
        self.assertEqual("2", config["THIRD"])
        self.assertEqual(3, config["FOURTH"])
        config.from_sync_access_config_list()
        self.assertEqual(3, config["FOURTH"])
        os.remove(current_json_file)
        os.unsetenv("test_FOURTH")


if __name__ == '__main__':
    unittest.main()
