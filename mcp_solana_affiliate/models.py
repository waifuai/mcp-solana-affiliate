"""Data models for the affiliate system using Pydantic."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, validator
import uuid

class CommissionRecord(BaseModel):
    """Model for a single commission record."""

    ico_id: str = Field(..., description="ICO identifier")
    amount: float = Field(..., gt=0, description="Transaction amount")
    commission: float = Field(..., ge=0, description="Commission earned")
    client_ip: str = Field(..., description="Client IP address")
    timestamp: int = Field(default_factory=lambda: int(datetime.now().timestamp()),
                          description="Unix timestamp")

    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be positive')
        return v

    @validator('commission')
    def validate_commission(cls, v):
        if v < 0:
            raise ValueError('Commission cannot be negative')
        return v

class AffiliateData(BaseModel):
    """Model for affiliate data."""

    affiliate_id: str = Field(default_factory=lambda: str(uuid.uuid4()),
                             description="Unique affiliate identifier")
    commissions: List[CommissionRecord] = Field(default_factory=list,
                                               description="List of commission records")
    created_at: int = Field(default_factory=lambda: int(datetime.now().timestamp()),
                           description="Creation timestamp")
    last_updated: int = Field(default_factory=lambda: int(datetime.now().timestamp()),
                             description="Last update timestamp")

    class Config:
        """Pydantic config."""
        validate_assignment = True

    @validator('affiliate_id')
    def validate_affiliate_id(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError('Invalid affiliate ID')
        return v.strip()

class BuyTokensRequest(BaseModel):
    """Model for buy tokens request."""

    amount: float = Field(..., gt=0, description="Amount to purchase")
    affiliate_id: str = Field(..., description="Affiliate identifier")

    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be positive')
        if v > 1000000:  # Arbitrary large limit
            raise ValueError('Amount exceeds maximum allowed')
        return v

    @validator('affiliate_id')
    def validate_affiliate_id(cls, v):
        if not v or not v.strip():
            raise ValueError('Affiliate ID is required')
        return v.strip()

class CommissionRequest(BaseModel):
    """Model for commission recording request."""

    affiliate_id: str = Field(..., description="Affiliate identifier")
    ico_id: str = Field(..., description="ICO identifier")
    amount: float = Field(..., gt=0, description="Transaction amount")
    commission: float = Field(..., ge=0, description="Commission amount")
    client_ip: str = Field(..., description="Client IP address")

    @validator('amount', 'commission')
    def validate_positive_values(cls, v):
        if v <= 0:
            raise ValueError('Value must be positive')
        return v

class TransactionResponse(BaseModel):
    """Model for transaction response."""

    transaction: str = Field(..., description="Serialized transaction")

class ErrorResponse(BaseModel):
    """Model for error responses."""

    error: str = Field(..., description="Error message")

class HealthCheckResponse(BaseModel):
    """Model for health check responses."""

    status: str = Field(..., description="Health status")
    timestamp: int = Field(..., description="Unix timestamp")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    checks: dict = Field(..., description="Individual health checks")

class MetricsResponse(BaseModel):
    """Model for metrics responses."""

    total_affiliates: int = Field(..., ge=0, description="Total number of affiliates")
    total_commissions: int = Field(..., ge=0, description="Total number of commissions")
    total_commission_amount: float = Field(..., ge=0, description="Total commission amount")
    timestamp: int = Field(..., description="Unix timestamp")

class AffiliateRegistrationResponse(BaseModel):
    """Model for affiliate registration responses."""

    message: str = Field(..., description="Registration message")
    affiliate_id: str = Field(..., description="Generated affiliate ID")
    blink_url: str = Field(..., description="Generated Blink URL")

class CommissionRecordResponse(BaseModel):
    """Model for commission recording responses."""

    message: str = Field(..., description="Response message")
    commission_id: Optional[str] = Field(None, description="Commission identifier")