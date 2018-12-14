"""Tests for `grpcalchemy` package."""

import unittest

from grpcalchemy.meta import __meta__


class TestGrpcalchemy(unittest.TestCase):
    """Tests for `grpcalchemy` package."""

    def setUp(self):
        """Set up test fixtures, if any."""
        __meta__.clear()

    def tearDown(self):
        """Tear down test fixtures, if any."""
