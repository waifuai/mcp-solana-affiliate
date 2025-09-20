"""Tests for configuration management."""

import os
import pytest
from unittest.mock import patch
from mcp_solana_affiliate.config import load_config, AppConfig, ServerConfig, AffiliateConfig

def test_load_config_defaults():
    """Test loading configuration with default values."""
    config = load_config()

    assert isinstance(config, AppConfig)
    assert isinstance(config.server, ServerConfig)
    assert isinstance(config.affiliate, AffiliateConfig)

    # Test default values
    assert config.server.mcp_port == 5001
    assert config.server.flask_port == 5002
    assert config.server.debug is False

    assert config.affiliate.default_commission_rate == 0.01
    assert config.affiliate.default_ico_id == "main_ico"

    assert config.logging.level == "INFO"

@patch.dict(os.environ, {
    "MAIN_SERVER_URL": "http://test-server.com",
    "MCP_PORT": "6001",
    "COMMISSION_RATE": "0.02",
    "DEBUG": "true",
    "LOG_LEVEL": "DEBUG"
}, clear=True)
def test_load_config_from_environment():
    """Test loading configuration from environment variables."""
    config = load_config()

    assert config.server.mcp_port == 6001
    assert config.server.debug is True
    assert config.affiliate.default_commission_rate == 0.02
    assert config.logging.level == "DEBUG"
    assert config.external_service is not None
    assert str(config.external_service.main_server_url) == "http://test-server.com"

@patch.dict(os.environ, {
    "MAIN_SERVER_URL": "invalid-url",
}, clear=True)
def test_load_config_invalid_url():
    """Test loading configuration with invalid URL."""
    config = load_config()
    # Should not raise an exception, but external_service should be None
    assert config.external_service is None

def test_server_config_validation():
    """Test ServerConfig validation."""
    # Valid config
    config = ServerConfig(mcp_port=5001, flask_port=5002, debug=False)
    assert config.mcp_port == 5001
    assert config.flask_port == 5002

    # Invalid port (too low)
    with pytest.raises(ValueError):
        ServerConfig(mcp_port=80, flask_port=5002)

    # Invalid port (too high)
    with pytest.raises(ValueError):
        ServerConfig(mcp_port=70000, flask_port=5002)

def test_affiliate_config_validation():
    """Test AffiliateConfig validation."""
    # Valid config
    config = AffiliateConfig(
        default_commission_rate=0.05,
        default_ico_id="test-ico",
        max_requests_per_minute=100
    )
    assert config.default_commission_rate == 0.05
    assert config.default_ico_id == "test-ico"

    # Invalid commission rate (negative)
    with pytest.raises(ValueError):
        AffiliateConfig(default_commission_rate=-0.01)

    # Invalid commission rate (too high)
    with pytest.raises(ValueError):
        AffiliateConfig(default_commission_rate=1.5)

    # Invalid max_requests_per_minute (zero)
    with pytest.raises(ValueError):
        AffiliateConfig(max_requests_per_minute=0)

def test_affiliate_config_data_file_validation():
    """Test AffiliateConfig data file path validation."""
    # Valid path
    config = AffiliateConfig(data_file_path="test.json")
    assert str(config.data_file_path) == "test.json"

    # Invalid extension
    with pytest.raises(ValueError, match="Data file must have .json extension"):
        AffiliateConfig(data_file_path="test.txt")

@patch.dict(os.environ, {"MAIN_SERVER_URL": "http://test-server.com"}, clear=True)
def test_external_service_config():
    """Test ExternalServiceConfig creation."""
    config = load_config()

    assert config.external_service is not None
    assert str(config.external_service.main_server_url) == "http://test-server.com"
    assert config.external_service.request_timeout == 10.0
    assert config.external_service.max_retries == 3
    assert config.external_service.retry_delay == 1.0

def test_logging_config_validation():
    """Test LoggingConfig validation."""
    from mcp_solana_affiliate.config import LoggingConfig

    # Valid config
    config = LoggingConfig(level="DEBUG", file_path="test.log")
    assert config.level == "DEBUG"
    assert str(config.file_path) == "test.log"

    # Invalid level
    with pytest.raises(ValueError, match="Log level must be one of"):
        LoggingConfig(level="INVALID")

    # Case insensitive level
    config = LoggingConfig(level="debug")
    assert config.level == "debug"

    # No file path
    config = LoggingConfig(level="INFO")
    assert config.file_path is None

def test_app_config_validation():
    """Test AppConfig validation and assignment."""
    config = AppConfig()

    # Test that validation assignment works
    config.server.debug = True
    assert config.server.debug is True

    config.affiliate.default_commission_rate = 0.1
    assert config.affiliate.default_commission_rate == 0.1

def test_config_immutability():
    """Test that configuration is properly structured."""
    config = load_config()

    # Ensure nested configs are properly typed
    assert hasattr(config.server, 'mcp_port')
    assert hasattr(config.server, 'flask_port')
    assert hasattr(config.server, 'debug')

    assert hasattr(config.affiliate, 'default_commission_rate')
    assert hasattr(config.affiliate, 'default_ico_id')
    assert hasattr(config.affiliate, 'data_file_path')

    assert hasattr(config.logging, 'level')
    assert hasattr(config.logging, 'format')
    assert hasattr(config.logging, 'file_path')