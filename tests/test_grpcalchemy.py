"""Tests for `grpcalchemy` package."""
import unittest

from grpcalchemy import DefaultConfig
from grpcalchemy.meta import __meta__
from grpcalchemy.utils import generate_proto_file


class TestConfig(DefaultConfig):
    GRPC_SEVER_REFLECTION_ENABLE = True


class TestGRPCAlchemy(unittest.TestCase):
    """Tests for `grpcalchemy` package."""

    config = TestConfig()

    def setUp(self):
        """Set up test fixtures, if any."""
        __meta__.clear()

    def tearDown(self):
        """Tear down test fixtures, if any."""
        __meta__.clear()

    @classmethod
    def generate_proto_file(cls):
        generate_proto_file(
            template_path_root=cls.config.PROTO_TEMPLATE_ROOT,
            template_path=cls.config.PROTO_TEMPLATE_PATH,
        )
