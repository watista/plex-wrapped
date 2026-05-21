"""Static fixtures for local development and UI testing."""

from app.fixtures.test_wrapped import (
    default_fixture_path,
    load_test_payload,
    load_test_user_entries,
)

__all__ = ["default_fixture_path", "load_test_payload", "load_test_user_entries"]
