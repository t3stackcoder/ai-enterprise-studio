"""
Building Blocks Testing Configuration

Pytest configuration and fixtures for building blocks tests.
Imports from the testing infrastructure to make fixtures available.
"""

# Import specific fixtures from testing infrastructure
# pylint: disable=unused-import
from infrastructure_testing.conftest import test_db_session  # noqa: F401

# This makes test_db_session fixture available to BB tests
