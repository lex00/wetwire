"""Pytest configuration for wetwire tests."""

import pytest

from wetwire import registry


@pytest.fixture(autouse=True)
def clear_registry():
    """Clear the registry before each test."""
    registry.clear()
    yield
    registry.clear()
