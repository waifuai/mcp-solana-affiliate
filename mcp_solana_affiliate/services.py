"""
Service Layer Module.

This module contains the core business logic for the Solana affiliate system, organized
into service classes that handle different aspects of the application. Services interact
with the data layer, external APIs, and provide high-level operations for the API endpoints
and MCP tools.

Key Features:
- Separation of business logic from API endpoints
- Service classes for affiliates, transactions, health checks, and metrics
- Integration with external main server for transaction processing
- Caching integration for performance optimization
- Comprehensive error handling and logging
- Commission calculation and recording logic
- Health monitoring and metrics collection
"""
"""Service layer for business logic."""

import logging
from typing import Dict, Any, Optional, List
from urllib.parse import quote

from mcp_solana_affiliate.config import app_config
from mcp_solana_affiliate.models import (
    AffiliateData, CommissionRecord, BuyTokensRequest,
    CommissionRequest, TransactionResponse
)
from mcp_solana_affiliate import affiliates
from mcp_solana_affiliate.cache import (
    affiliate_cache, metrics_cache, health_cache,
    get_affiliate_cache_key, get_metrics_cache_key, get_health_cache_key
)
import httpx

logger = logging.getLogger(__name__)

class AffiliateService:
    """Service for affiliate-related operations."""

    @staticmethod
    def register_affiliate() -> str:
        """Register a new affiliate and return a Blink URL."""
        try:
            if not app_config.external_service:
                raise ValueError("External service configuration is not set")

            affiliate_id = affiliates.generate_affiliate_id()
            main_server_url = str(app_config.external_service.main_server_url)

            # Point the Blink URL to the affiliate server's endpoint
            action_api_url = f"{main_server_url}/affiliate_buy_tokens?affiliate_id={affiliate_id}"
            blink_url = "solana-action:" + quote(action_api_url)

            logger.info(f"Registered new affiliate: {affiliate_id}")
            return f"Affiliate registered successfully! Your Solana Blink URL is: {blink_url}"

        except Exception as e:
            logger.error(f"Error registering affiliate: {e}")
            raise

    @staticmethod
    def get_affiliate_data(affiliate_id: str) -> Optional[AffiliateData]:
        """Get affiliate data by ID with caching."""
        cache_key = get_affiliate_cache_key(affiliate_id)

        # Try to get from cache first
        cached_data = affiliate_cache.get(cache_key)
        if cached_data:
            return cached_data

        # Cache miss, get from data source
        data = affiliates.get_affiliate_data(affiliate_id)
        if data:
            affiliate_data = AffiliateData(affiliate_id=affiliate_id, **data)
            # Cache the result
            affiliate_cache.set(cache_key, affiliate_data)
            return affiliate_data

        return None

    @staticmethod
    def record_commission(request: CommissionRequest) -> bool:
        """Record a commission for an affiliate."""
        success = affiliates.record_commission(
            request.affiliate_id,
            request.ico_id,
            request.amount,
            request.commission,
            request.client_ip
        )

        # Invalidate cache if commission was recorded successfully
        if success:
            cache_key = get_affiliate_cache_key(request.affiliate_id)
            affiliate_cache.delete(cache_key)
            logger.debug(f"Invalidated cache for affiliate: {request.affiliate_id}")

            # Also invalidate metrics cache since totals have changed
            metrics_cache.delete(get_metrics_cache_key())

        return success

class TransactionService:
    """Service for transaction-related operations."""

    @staticmethod
    def process_buy_tokens(request: BuyTokensRequest, client_ip: str) -> TransactionResponse:
        """Process a token purchase through affiliate link."""
        if not app_config.external_service:
            raise ValueError("External service configuration is not set")

        main_server_url = str(app_config.external_service.main_server_url)

        # Make request to main server's Action API
        with httpx.Client() as client:
            try:
                response = client.post(
                    f"{main_server_url}/buy_tokens_action",
                    json={"amount": request.amount},
                    timeout=app_config.external_service.request_timeout
                )
                response.raise_for_status()
                main_server_response = response.json()

            except httpx.TimeoutException:
                logger.error("Timeout connecting to main server")
                raise httpx.TimeoutException("Service temporarily unavailable")
            except httpx.RequestError as e:
                logger.error(f"Request error to main server: {e}")
                raise httpx.RequestError(f"Unable to connect to main server: {str(e)}")
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error from main server: {e.response.status_code}")
                raise httpx.HTTPStatusError(f"Main server error: {e.response.status_code}")

        # Get the serialized transaction from the main server's response
        serialized_transaction = main_server_response.get("transaction")
        if not serialized_transaction:
            raise ValueError("Failed to get transaction from main server")

        # Record the commission
        commission_request = CommissionRequest(
            affiliate_id=request.affiliate_id,
            ico_id=app_config.affiliate.default_ico_id,
            amount=request.amount,
            commission=request.amount * app_config.affiliate.default_commission_rate,
            client_ip=client_ip
        )

        commission_success = AffiliateService.record_commission(commission_request)
        if not commission_success:
            logger.warning(f"Failed to record commission for affiliate {request.affiliate_id}")
            # Don't fail the transaction if commission recording fails

        logger.info(f"Token purchase processed for affiliate {request.affiliate_id}: amount={request.amount}")
        return TransactionResponse(transaction=serialized_transaction)

class HealthService:
    """Service for health checks and monitoring."""

    @staticmethod
    def check_health() -> Dict[str, Any]:
        """Perform comprehensive health check with caching."""
        cache_key = get_health_cache_key()

        # Try to get from cache first
        cached_health = health_cache.get(cache_key)
        if cached_health:
            return cached_health

        try:
            # Check if we can read affiliate data
            data = affiliates.load_affiliate_data()

            # Check main server connectivity
            main_server_status = "not_configured"
            if app_config.external_service:
                try:
                    with httpx.Client() as client:
                        response = client.get(
                            f"{app_config.external_service.main_server_url}/health",
                            timeout=5
                        )
                        main_server_status = "healthy" if response.status_code == 200 else "unhealthy"
                except Exception:
                    main_server_status = "unreachable"

            health_status = {
                "status": "healthy",
                "timestamp": int(__import__('time').time()),
                "service": "mcp-solana-affiliate",
                "version": "1.0.0",
                "checks": {
                    "affiliate_data": "healthy" if isinstance(data, dict) else "unhealthy",
                    "main_server": main_server_status,
                    "database": "healthy"  # Could add actual DB checks here
                }
            }

            is_healthy = all(status in ["healthy", "not_configured"]
                            for status in health_status["checks"].values())
            health_status["status"] = "healthy" if is_healthy else "unhealthy"

            # Cache the result
            health_cache.set(cache_key, health_status)
            return health_status

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            error_status = {
                "status": "unhealthy",
                "timestamp": int(__import__('time').time()),
                "error": str(e)
            }
            # Don't cache error states
            return error_status

class MetricsService:
    """Service for collecting metrics."""

    @staticmethod
    def get_metrics() -> Dict[str, Any]:
        """Collect and return service metrics with caching."""
        cache_key = get_metrics_cache_key()

        # Try to get from cache first
        cached_metrics = metrics_cache.get(cache_key)
        if cached_metrics:
            return cached_metrics

        try:
            data = affiliates.load_affiliate_data()
            total_affiliates = len(data)
            total_commissions = sum(
                len(affiliate.get("commissions", []))
                for affiliate in data.values()
            )

            total_commission_amount = sum(
                commission.get("commission", 0)
                for affiliate in data.values()
                for commission in affiliate.get("commissions", [])
            )

            metrics_data = {
                "total_affiliates": total_affiliates,
                "total_commissions": total_commissions,
                "total_commission_amount": total_commission_amount,
                "timestamp": int(__import__('time').time())
            }

            # Cache the result
            metrics_cache.set(cache_key, metrics_data)
            return metrics_data

        except Exception as e:
            logger.error(f"Metrics collection failed: {e}")
            raise