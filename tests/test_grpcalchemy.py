"""Tests for `grpcalchemy` package."""
import unittest

from grpcalchemy import DefaultConfig
from grpcalchemy.meta import __meta__


class TestConfig(DefaultConfig):
    GRPC_SEVER_REFLECTION_ENABLE = True


class TestGrpcalchemy(unittest.TestCase):
    """Tests for `grpcalchemy` package."""

    config = TestConfig()

    def setUp(self):
        """Set up test fixtures, if any."""
        __meta__.clear()

    def tearDown(self):
        """Tear down test fixtures, if any."""
