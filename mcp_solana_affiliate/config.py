"""
Configuration Management Module.

This module handles all configuration for the Solana affiliate server using Pydantic models
for validation and type safety. It loads configuration from environment variables with
sensible defaults, providing a centralized way to manage server settings, affiliate
parameters, external service connections, and logging configuration.

Key Features:
- Pydantic models for type-safe configuration validation
- Environment variable loading with fallback defaults
- Structured configuration sections for different components
- Comprehensive validation with custom validators
- Centralized configuration instance for easy access
"""
"""Configuration management using Pydantic models."""

import os
import logging
from typing import Optional
from pydantic import BaseModel, Field, validator, HttpUrl
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

class ServerConfig(BaseModel):
    """Configuration for server settings."""

    # Server ports
    mcp_port: int = Field(default=5001, ge=1024, le=65535)
    flask_port: int = Field(default=5002, ge=1024, le=65535)

    # Debug mode
    debug: bool = Field(default=False)

    # CORS settings
    cors_origins: list[str] = Field(default=["*"])
    cors_methods: list[str] = Field(default=["GET", "POST", "OPTIONS"])
    cors_headers: list[str] = Field(default=["Content-Type"])

class AffiliateConfig(BaseModel):
    """Configuration for affiliate-specific settings."""

    # Commission rates
    default_commission_rate: float = Field(default=0.01, ge=0.0, le=1.0)  # 1%

    # ICO settings
    default_ico_id: str = Field(default="main_ico")

    # File paths
    data_file_path: Path = Field(default=Path("affiliate_data.json"))

    # Rate limiting
    max_requests_per_minute: int = Field(default=60, gt=0)
    max_affiliates_per_ip: int = Field(default=10, gt=0)

    @validator('data_file_path')
    def validate_data_file_path(cls, v):
        """Ensure data file path is valid."""
        if v.suffix != '.json':
            raise ValueError('Data file must have .json extension')
        return v

class ExternalServiceConfig(BaseModel):
    """Configuration for external service dependencies."""

    main_server_url: HttpUrl = Field(..., description="URL of the main ICO server")
    request_timeout: float = Field(default=10.0, gt=0)

    # Retry settings
    max_retries: int = Field(default=3, ge=0)
    retry_delay: float = Field(default=1.0, gt=0)

class LoggingConfig(BaseModel):
    """Configuration for logging settings."""

    level: str = Field(default="INFO", to_upper=True)
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_path: Optional[Path] = Field(default=None)

    @validator('level')
    def validate_level(cls, v):
        """Validate logging level."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v not in valid_levels:
            raise ValueError(f'Log level must be one of {valid_levels}')
        return v

class AppConfig(BaseModel):
    """Main application configuration."""

    server: ServerConfig = Field(default_factory=ServerConfig)
    affiliate: AffiliateConfig = Field(default_factory=AffiliateConfig)
    external_service: Optional[ExternalServiceConfig] = Field(default=None)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    class Config:
        """Pydantic config."""
        validate_assignment = True

def load_config() -> AppConfig:
    """Load configuration from environment variables and defaults."""

    # Load external service configuration
    main_server_url = os.getenv("MAIN_SERVER_URL")
    external_service_config = None

    if main_server_url:
        try:
            external_service_config = ExternalServiceConfig(
                main_server_url=main_server_url,
                request_timeout=float(os.getenv("REQUEST_TIMEOUT", "10.0")),
                max_retries=int(os.getenv("MAX_RETRIES", "3")),
                retry_delay=float(os.getenv("RETRY_DELAY", "1.0"))
            )
        except Exception as e:
            logger.warning(f"Failed to load external service config: {e}")

    # Load server configuration
    server_config = ServerConfig(
        mcp_port=int(os.getenv("MCP_PORT", "5001")),
        flask_port=int(os.getenv("FLASK_PORT", "5002")),
        debug=os.getenv("DEBUG", "false").lower() == "true"
    )

    # Load affiliate configuration
    affiliate_config = AffiliateConfig(
        default_commission_rate=float(os.getenv("COMMISSION_RATE", "0.01")),
        default_ico_id=os.getenv("DEFAULT_ICO_ID", "main_ico"),
        data_file_path=Path(os.getenv("AFFILIATE_DATA_FILE", "affiliate_data.json")),
        max_requests_per_minute=int(os.getenv("MAX_REQUESTS_PER_MINUTE", "60")),
        max_affiliates_per_ip=int(os.getenv("MAX_AFFILIATES_PER_IP", "10"))
    )

    # Load logging configuration
    logging_config = LoggingConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        file_path=Path(os.getenv("LOG_FILE")) if os.getenv("LOG_FILE") else None
    )

    config = AppConfig(
        server=server_config,
        affiliate=affiliate_config,
        external_service=external_service_config,
        logging=logging_config
    )

    logger.info("Configuration loaded successfully")
    return config

# Global configuration instance
app_config = load_config()