"""
Test Configuration Module.

This module contains pytest fixtures and configuration for testing the Solana affiliate
server. It provides test utilities, mock objects, and setup/teardown functionality to
ensure tests run in isolation with proper mocking and cleanup.

Key Features:
- Test data file management with automatic cleanup
- Flask application and test client fixtures
- MCP (Model Context Protocol) context and server mocking
- Environment variable management for tests
- Module-level patching for reliable test isolation
- Automatic test data file creation and cleanup
"""
# tests/conftest.py
import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import os
from mcp.server.fastmcp import Context # Import Context for type hinting/mocking
import pytest_asyncio # Import pytest_asyncio
import httpx # Import httpx for the async client

 # Define the path to the test data file relative to the tests directory
# Using a different name to avoid conflict with the actual file
TEST_DATA_FILE = Path(__file__).parent / "test_affiliate_data.json"

@pytest.fixture(autouse=True)
def manage_test_data_file(monkeypatch):
    """
    Fixture to manage the test affiliate data file.
    Patches the file path and ensures clean state for each test.
    Uses monkeypatch for reliable patching of module-level variables.
    """
    # Ensure the file doesn't exist before the test
    if TEST_DATA_FILE.exists():
        TEST_DATA_FILE.unlink()
    # Create an empty *valid* JSON file initially
    with open(TEST_DATA_FILE, "w") as f:
        json.dump({}, f)

    # Patch the file path used by the affiliates module
    monkeypatch.setattr("mcp_solana_affiliate.affiliates.affiliate_data_file", TEST_DATA_FILE)

    # Critical: Reset the in-memory affiliate_data dictionary before each test
    # This forces reload from the (now patched) TEST_DATA_FILE
    from mcp_solana_affiliate import affiliates
    affiliates.affiliate_data = affiliates.load_affiliate_data() # Reload with patched path

    yield # Run the test

    # Clean up the file after the test
    if TEST_DATA_FILE.exists():
        TEST_DATA_FILE.unlink()

@pytest.fixture()
def test_app():
    """Fixture for the Flask app instance configured for testing."""
    # Import server components here to ensure patches are applied
    from mcp_solana_affiliate.server import app
    app.config.update({
        "TESTING": True,
    })
    # Set a default MAIN_SERVER_URL for testing if not set
    os.environ.setdefault("MAIN_SERVER_URL", "http://mock-main-server.test")
    yield app
    # Clean up environment variable if it was set by the fixture
    if "MAIN_SERVER_URL" in os.environ and os.environ["MAIN_SERVER_URL"] == "http://mock-main-server.test":
         del os.environ["MAIN_SERVER_URL"]


# Use Flask's built-in TestClient
@pytest.fixture()
def client(test_app):
    """Fixture for the Flask test client."""
    return test_app.test_client()

@pytest.fixture()
def mcp_context_mock():
    """Fixture to create a mock MCP Context."""
    return MagicMock(spec=Context)

# Fixture for the MCP server itself (useful for direct tool calls)
@pytest.fixture()
def mcp_server_instance():
     from mcp_solana_affiliate.server import mcp
     return mcp