"""Tests for `grpcalchemy` package."""
import os
import unittest
from shutil import rmtree

from grpcalchemy.meta import __meta__


class TestGrpcalchemy(unittest.TestCase):
    """Tests for `grpcalchemy` package."""

    def setUp(self):
        """Set up test fixtures, if any."""
        __meta__.clear()
        if os.path.exists("protos"):
            rmtree("protos")

    def tearDown(self):
        """Tear down test fixtures, if any."""
