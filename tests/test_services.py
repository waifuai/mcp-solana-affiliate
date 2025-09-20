"""Tests for service layer."""

import pytest
import uuid
from unittest.mock import patch, MagicMock
from mcp_solana_affiliate.services import (
    AffiliateService, TransactionService, HealthService, MetricsService
)
from mcp_solana_affiliate.models import (
    BuyTokensRequest, CommissionRequest, TransactionResponse
)

# Test AffiliateService

@patch("mcp_solana_affiliate.affiliates.generate_affiliate_id")
@patch.dict("os.environ", {"MAIN_SERVER_URL": "http://mock-server.test"}, clear=True)
def test_affiliate_service_register_affiliate(mock_generate_id):
    """Test AffiliateService.register_affiliate."""
    mock_affiliate_id = str(uuid.uuid4())
    mock_generate_id.return_value = mock_affiliate_id

    result = AffiliateService.register_affiliate()
    expected_url = f"http://mock-server.test/affiliate_buy_tokens?affiliate_id={mock_affiliate_id}"
    from urllib.parse import quote
    expected_blink = f"solana-action:{quote(expected_url)}"
    assert expected_blink in result
    assert "Affiliate registered successfully" in result

@patch("mcp_solana_affiliate.affiliates.generate_affiliate_id")
def test_affiliate_service_register_affiliate_no_config(mock_generate_id):
    """Test AffiliateService.register_affiliate without config."""
    mock_affiliate_id = str(uuid.uuid4())
    mock_generate_id.return_value = mock_affiliate_id

    with patch("mcp_solana_affiliate.services.app_config") as mock_config:
        mock_config.external_service = None

        with pytest.raises(ValueError, match="External service configuration is not set"):
            AffiliateService.register_affiliate()

@patch("mcp_solana_affiliate.affiliates.get_affiliate_data")
def test_affiliate_service_get_affiliate_data(mock_get_data):
    """Test AffiliateService.get_affiliate_data."""
    mock_data = {"commissions": [{"amount": 100, "commission": 10}]}
    mock_get_data.return_value = mock_data

    result = AffiliateService.get_affiliate_data("test-id")
    assert result is not None
    assert result.affiliate_id == "test-id"
    assert result.commissions[0]["amount"] == 100

@patch("mcp_solana_affiliate.affiliates.get_affiliate_data")
def test_affiliate_service_get_affiliate_data_not_found(mock_get_data):
    """Test AffiliateService.get_affiliate_data when affiliate not found."""
    mock_get_data.return_value = None

    result = AffiliateService.get_affiliate_data("non-existent-id")
    assert result is None

@patch("mcp_solana_affiliate.affiliates.record_commission")
def test_affiliate_service_record_commission_success(mock_record_commission):
    """Test AffiliateService.record_commission success."""
    mock_record_commission.return_value = True
    request = CommissionRequest(
        affiliate_id="test-id",
        ico_id="test-ico",
        amount=1000.0,
        commission=50.0,
        client_ip="1.2.3.4"
    )

    result = AffiliateService.record_commission(request)
    assert result is True
    mock_record_commission.assert_called_once_with(
        "test-id", "test-ico", 1000.0, 50.0, "1.2.3.4"
    )

@patch("mcp_solana_affiliate.affiliates.record_commission")
def test_affiliate_service_record_commission_failure(mock_record_commission):
    """Test AffiliateService.record_commission failure."""
    mock_record_commission.return_value = False
    request = CommissionRequest(
        affiliate_id="test-id",
        ico_id="test-ico",
        amount=1000.0,
        commission=50.0,
        client_ip="1.2.3.4"
    )

    result = AffiliateService.record_commission(request)
    assert result is False

# Test TransactionService

@patch("mcp_solana_affiliate.services.app_config")
@patch("httpx.Client")
@patch("mcp_solana_affiliate.affiliates.record_commission")
def test_transaction_service_process_buy_tokens_success(mock_record_commission, mock_client, mock_config):
    """Test TransactionService.process_buy_tokens success."""
    # Setup mocks
    mock_config.external_service.main_server_url = "http://mock-server.test"
    mock_config.external_service.request_timeout = 10.0
    mock_config.affiliate.default_ico_id = "test-ico"
    mock_config.affiliate.default_commission_rate = 0.01

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"transaction": "test-transaction"}
    mock_response.raise_for_status.return_value = None

    mock_client_instance = MagicMock()
    mock_client_instance.post.return_value = mock_response
    mock_client.return_value.__enter__.return_value = mock_client_instance

    mock_record_commission.return_value = True

    # Execute
    request = BuyTokensRequest(amount=1000.0, affiliate_id="test-id")
    result = TransactionService.process_buy_tokens(request, "1.2.3.4")

    # Assert
    assert isinstance(result, TransactionResponse)
    assert result.transaction == "test-transaction"

    # Verify HTTP call
    mock_client_instance.post.assert_called_once_with(
        "http://mock-server.test/buy_tokens_action",
        json={"amount": 1000.0},
        timeout=10.0
    )

    # Verify commission recording
    mock_record_commission.assert_called_once()

@patch("mcp_solana_affiliate.services.app_config")
@patch("httpx.Client")
def test_transaction_service_process_buy_tokens_no_config(mock_client, mock_config):
    """Test TransactionService.process_buy_tokens without config."""
    mock_config.external_service = None

    request = BuyTokensRequest(amount=1000.0, affiliate_id="test-id")

    with pytest.raises(ValueError, match="External service configuration is not set"):
        TransactionService.process_buy_tokens(request, "1.2.3.4")

@patch("mcp_solana_affiliate.services.app_config")
@patch("httpx.Client")
def test_transaction_service_process_buy_tokens_httpx_error(mock_client, mock_config):
    """Test TransactionService.process_buy_tokens with HTTP error."""
    mock_config.external_service.main_server_url = "http://mock-server.test"
    mock_config.external_service.request_timeout = 10.0

    mock_client_instance = MagicMock()
    mock_client_instance.post.side_effect = httpx.TimeoutException("Timeout")
    mock_client.return_value.__enter__.return_value = mock_client_instance

    request = BuyTokensRequest(amount=1000.0, affiliate_id="test-id")

    with pytest.raises(httpx.TimeoutException):
        TransactionService.process_buy_tokens(request, "1.2.3.4")

@patch("mcp_solana_affiliate.services.app_config")
@patch("httpx.Client")
def test_transaction_service_process_buy_tokens_no_transaction(mock_client, mock_config):
    """Test TransactionService.process_buy_tokens when main server returns no transaction."""
    mock_config.external_service.main_server_url = "http://mock-server.test"
    mock_config.external_service.request_timeout = 10.0

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"message": "No transaction available"}
    mock_response.raise_for_status.return_value = None

    mock_client_instance = MagicMock()
    mock_client_instance.post.return_value = mock_response
    mock_client.return_value.__enter__.return_value = mock_client_instance

    request = BuyTokensRequest(amount=1000.0, affiliate_id="test-id")

    with pytest.raises(ValueError, match="Failed to get transaction from main server"):
        TransactionService.process_buy_tokens(request, "1.2.3.4")

# Test HealthService

@patch("mcp_solana_affiliate.affiliates.load_affiliate_data")
@patch("mcp_solana_affiliate.services.app_config")
def test_health_service_check_health_healthy(mock_config, mock_load_data):
    """Test HealthService.check_health when everything is healthy."""
    mock_load_data.return_value = {"test": "data"}
    mock_config.external_service.main_server_url = "http://mock-server.test"

    with patch("httpx.Client") as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client_instance = MagicMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance

        result = HealthService.check_health()

        assert result["status"] == "healthy"
        assert result["checks"]["affiliate_data"] == "healthy"
        assert result["checks"]["main_server"] == "healthy"
        assert result["checks"]["database"] == "healthy"

@patch("mcp_solana_affiliate.affiliates.load_affiliate_data")
@patch("mcp_solana_affiliate.services.app_config")
def test_health_service_check_health_unhealthy(mock_config, mock_load_data):
    """Test HealthService.check_health when some services are unhealthy."""
    mock_load_data.return_value = {}  # Empty data
    mock_config.external_service.main_server_url = "http://mock-server.test"

    with patch("httpx.Client") as mock_client:
        mock_client_instance = MagicMock()
        mock_client_instance.get.side_effect = Exception("Connection failed")
        mock_client.return_value.__enter__.return_value = mock_client_instance

        result = HealthService.check_health()

        assert result["status"] == "unhealthy"
        assert result["checks"]["affiliate_data"] == "healthy"  # Empty dict is still valid
        assert result["checks"]["main_server"] == "unreachable"
        assert result["checks"]["database"] == "healthy"

@patch("mcp_solana_affiliate.affiliates.load_affiliate_data")
def test_health_service_check_health_exception(mock_load_data):
    """Test HealthService.check_health when exception occurs."""
    mock_load_data.side_effect = Exception("Database error")

    result = HealthService.check_health()

    assert result["status"] == "unhealthy"
    assert "Database error" in result["error"]

# Test MetricsService

@patch("mcp_solana_affiliate.affiliates.load_affiliate_data")
def test_metrics_service_get_metrics(mock_load_data):
    """Test MetricsService.get_metrics."""
    mock_data = {
        "affiliate1": {
            "commissions": [
                {"amount": 1000, "commission": 50},
                {"amount": 2000, "commission": 100}
            ]
        },
        "affiliate2": {
            "commissions": [
                {"amount": 1500, "commission": 75}
            ]
        }
    }
    mock_load_data.return_value = mock_data

    result = MetricsService.get_metrics()

    assert result["total_affiliates"] == 2
    assert result["total_commissions"] == 3
    assert result["total_commission_amount"] == 225.0  # 50 + 100 + 75
    assert isinstance(result["timestamp"], int)

@patch("mcp_solana_affiliate.affiliates.load_affiliate_data")
def test_metrics_service_get_metrics_empty(mock_load_data):
    """Test MetricsService.get_metrics with empty data."""
    mock_load_data.return_value = {}

    result = MetricsService.get_metrics()

    assert result["total_affiliates"] == 0
    assert result["total_commissions"] == 0
    assert result["total_commission_amount"] == 0.0

@patch("mcp_solana_affiliate.affiliates.load_affiliate_data")
def test_metrics_service_get_metrics_exception(mock_load_data):
    """Test MetricsService.get_metrics with exception."""
    mock_load_data.side_effect = Exception("Database error")

    with pytest.raises(Exception, match="Database error"):
        MetricsService.get_metrics()