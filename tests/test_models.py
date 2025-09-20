"""Tests for Pydantic models."""

import pytest
from datetime import datetime
from mcp_solana_affiliate.models import (
    CommissionRecord, AffiliateData, BuyTokensRequest,
    CommissionRequest, TransactionResponse, ErrorResponse,
    HealthCheckResponse, MetricsResponse, AffiliateRegistrationResponse,
    CommissionRecordResponse
)

def test_commission_record_creation():
    """Test CommissionRecord model creation."""
    record = CommissionRecord(
        ico_id="test-ico",
        amount=1000.0,
        commission=50.0,
        client_ip="1.2.3.4"
    )

    assert record.ico_id == "test-ico"
    assert record.amount == 1000.0
    assert record.commission == 50.0
    assert record.client_ip == "1.2.3.4"
    assert isinstance(record.timestamp, int)

def test_commission_record_validation():
    """Test CommissionRecord validation."""
    # Negative amount
    with pytest.raises(ValueError):
        CommissionRecord(
            ico_id="test-ico",
            amount=-100,
            commission=50.0,
            client_ip="1.2.3.4"
        )

    # Negative commission
    with pytest.raises(ValueError):
        CommissionRecord(
            ico_id="test-ico",
            amount=1000.0,
            commission=-10.0,
            client_ip="1.2.3.4"
        )

def test_affiliate_data_creation():
    """Test AffiliateData model creation."""
    import uuid
    affiliate_id = str(uuid.uuid4())

    data = AffiliateData(affiliate_id=affiliate_id)
    assert data.affiliate_id == affiliate_id
    assert data.commissions == []
    assert isinstance(data.created_at, int)
    assert isinstance(data.last_updated, int)

def test_buy_tokens_request_validation():
    """Test BuyTokensRequest validation."""
    # Valid request
    request = BuyTokensRequest(amount=1000.0, affiliate_id="test-id")
    assert request.amount == 1000.0
    assert request.affiliate_id == "test-id"

    # Invalid amount (negative)
    with pytest.raises(ValueError):
        BuyTokensRequest(amount=-100, affiliate_id="test-id")

    # Invalid amount (zero)
    with pytest.raises(ValueError):
        BuyTokensRequest(amount=0, affiliate_id="test-id")

    # Missing amount
    with pytest.raises(ValueError):
        BuyTokensRequest(affiliate_id="test-id")

    # Missing affiliate_id
    with pytest.raises(ValueError):
        BuyTokensRequest(amount=1000)

    # Empty affiliate_id
    with pytest.raises(ValueError):
        BuyTokensRequest(amount=1000, affiliate_id="")

def test_commission_request_validation():
    """Test CommissionRequest validation."""
    # Valid request
    request = CommissionRequest(
        affiliate_id="test-id",
        ico_id="test-ico",
        amount=1000.0,
        commission=50.0,
        client_ip="1.2.3.4"
    )
    assert request.commission == 50.0

    # Invalid commission (negative)
    with pytest.raises(ValueError):
        CommissionRequest(
            affiliate_id="test-id",
            ico_id="test-ico",
            amount=1000.0,
            commission=-10.0,
            client_ip="1.2.3.4"
        )

    # Invalid amount (negative)
    with pytest.raises(ValueError):
        CommissionRequest(
            affiliate_id="test-id",
            ico_id="test-ico",
            amount=-1000.0,
            commission=50.0,
            client_ip="1.2.3.4"
        )

    # Missing required fields
    with pytest.raises(ValueError):
        CommissionRequest(
            affiliate_id="test-id",
            # missing ico_id
            amount=1000.0,
            commission=50.0,
            client_ip="1.2.3.4"
        )

def test_transaction_response():
    """Test TransactionResponse model."""
    response = TransactionResponse(transaction="test-transaction")
    assert response.transaction == "test-transaction"

    # Test serialization
    data = response.dict()
    assert data == {"transaction": "test-transaction"}

def test_error_response():
    """Test ErrorResponse model."""
    response = ErrorResponse(error="Test error message")
    assert response.error == "Test error message"

    # Test serialization
    data = response.dict()
    assert data == {"error": "Test error message"}

def test_health_check_response():
    """Test HealthCheckResponse model."""
    response = HealthCheckResponse(
        status="healthy",
        timestamp=1234567890,
        service="test-service",
        version="1.0.0",
        checks={"database": "healthy", "api": "healthy"}
    )

    assert response.status == "healthy"
    assert response.service == "test-service"
    assert response.checks["database"] == "healthy"

def test_metrics_response():
    """Test MetricsResponse model."""
    response = MetricsResponse(
        total_affiliates=10,
        total_commissions=25,
        total_commission_amount=1250.0,
        timestamp=1234567890
    )

    assert response.total_affiliates == 10
    assert response.total_commissions == 25
    assert response.total_commission_amount == 1250.0

    # Test serialization
    data = response.dict()
    assert data["total_affiliates"] == 10

def test_affiliate_registration_response():
    """Test AffiliateRegistrationResponse model."""
    response = AffiliateRegistrationResponse(
        message="Affiliate registered successfully",
        affiliate_id="test-id",
        blink_url="solana-action:test-url"
    )

    assert response.message == "Affiliate registered successfully"
    assert response.affiliate_id == "test-id"
    assert "solana-action" in response.blink_url

def test_commission_record_response():
    """Test CommissionRecordResponse model."""
    response = CommissionRecordResponse(
        message="Commission recorded successfully",
        commission_id="comm-123"
    )

    assert response.message == "Commission recorded successfully"
    assert response.commission_id == "comm-123"

    # Test without optional field
    response_no_id = CommissionRecordResponse(message="Success")
    assert response_no_id.commission_id is None