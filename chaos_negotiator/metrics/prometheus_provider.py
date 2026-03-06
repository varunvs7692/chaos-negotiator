"""Prometheus metrics provider for fetching real-time observability data."""

import logging
import os
from typing import Optional
import httpx

logger = logging.getLogger(__name__)


class PrometheusMetricsProvider:
    """Fetches live metrics from Prometheus for risk analysis.
    
    Supports querying Prometheus HTTP API for:
    - Error rates
    - Latency (p50, p95, p99)
    - Traffic percentage
    - Request volume
    """

    def __init__(self, prometheus_url: Optional[str] = None):
        """Initialize the Prometheus metrics provider.
        
        Args:
            prometheus_url: Base URL for Prometheus (defaults to env var PROMETHEUS_URL)
        """
        self.prometheus_url = prometheus_url or os.getenv("PROMETHEUS_URL", "http://localhost:9090")
        self.timeout = float(os.getenv("PROMETHEUS_TIMEOUT", "5.0"))
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _query(self, query: str) -> Optional[float]:
        """Execute a Prometheus query and return the result.
        
        Args:
            query: Prometheus query string
            
        Returns:
            Query result as float, or None if query fails
        """
        try:
            client = await self._get_client()
            response = await client.get(
                f"{self.prometheus_url}/api/v1/query",
                params={"query": query}
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") == "success" and data.get("data", {}).get("result"):
                results = data["data"]["result"]
                if results:
                    # Return the first result's value
                    return float(results[0]["value"][1])
            return None
        except Exception as e:
            logger.debug(f"Prometheus query failed: {query} - {e}")
            return None

    async def get_error_rate(self, service_name: str) -> Optional[float]:
        """Get current error rate percentage for a service.
        
        Args:
            service_name: Name of the service to query
            
        Returns:
            Error rate as percentage (0-100), or None if unavailable
        """
        # Query for 5xx errors as a percentage of total requests
        query = f'''
            sum(rate(http_requests_total{{service="{service_name}",status=~"5.."}}[5m])) 
            / 
            sum(rate(http_requests_total{{service="{service_name}"}}[5m])) * 100
        '''
        result = await self._query(query)
        if result is not None:
            return round(result, 3)
        
        # Fallback: try alternative metric names
        query_alt = f'''
            sum(rate(http_server_requests_seconds_count{{service="{service_name}",status=~"5.."}}[5m])) 
            / 
            sum(rate(http_server_requests_seconds_count{{service="{service_name}"}}[5m])) * 100
        '''
        result = await self._query(query_alt)
        if result is not None:
            return round(result, 3)
        
        return None

    async def get_latency_p50(self, service_name: str) -> Optional[float]:
        """Get P50 latency in milliseconds for a service.
        
        Args:
            service_name: Name of the service to query
            
        Returns:
            P50 latency in ms, or None if unavailable
        """
        query = f'''
            histogram_quantile(0.50, sum(rate(http_requests_duration_seconds_bucket{{service="{service_name}"}}[5m])) by (le))
        ''' * 1000  # Convert seconds to ms
        result = await self._query(query)
        if result is not None:
            return round(result, 2)
        
        # Fallback for Micrometer-style metrics
        query_alt = f'''
            histogram_quantile(0.50, sum(rate(http_server_requests_seconds_bucket{{service="{service_name}"}}[5m])) by (le))
        ''' * 1000
        result = await self._query(query_alt)
        if result is not None:
            return round(result, 2)
        
        return None

    async def get_latency_p95(self, service_name: str) -> Optional[float]:
        """Get P95 latency in milliseconds for a service.
        
        Args:
            service_name: Name of the service to query
            
        Returns:
            P95 latency in ms, or None if unavailable
        """
        query = f'''
            histogram_quantile(0.95, sum(rate(http_requests_duration_seconds_bucket{{service="{service_name}"}}[5m])) by (le))
        ''' * 1000
        result = await self._query(query)
        if result is not None:
            return round(result, 2)
        
        # Fallback for Micrometer-style metrics
        query_alt = f'''
            histogram_quantile(0.95, sum(rate(http_server_requests_seconds_bucket{{service="{service_name}"}}[5m])) by (le))
        ''' * 1000
        result = await self._query(query_alt)
        if result is not None:
            return round(result, 2)
        
        return None

    async def get_latency_p99(self, service_name: str) -> Optional[float]:
        """Get P99 latency in milliseconds for a service.
        
        Args:
            service_name: Name of the service to query
            
        Returns:
            P99 latency in ms, or None if unavailable
        """
        query = f'''
            histogram_quantile(0.99, sum(rate(http_requests_duration_seconds_bucket{{service="{service_name}"}}[5m])) by (le))
        ''' * 1000
        result = await self._query(query)
        if result is not None:
            return round(result, 2)
        
        # Fallback for Micrometer-style metrics
        query_alt = f'''
            histogram_quantile(0.99, sum(rate(http_server_requests_seconds_bucket{{service="{service_name}"}}[5m])) by (le))
        ''' * 1000
        result = await self._query(query_alt)
        if result is not None:
            return round(result, 2)
        
        return None

    async def get_traffic_percentage(self, service_name: str) -> Optional[float]:
        """Get traffic percentage for canary/rolling deployments.
        
        Args:
            service_name: Name of the service to query
            
        Returns:
            Traffic percentage (0-100), or None if unavailable
        """
        # Query for canary traffic percentage
        query = f'''
            sum(rate(http_requests_total{{service="{service_name}",canary="true"}}[5m])) 
            / 
            sum(rate(http_requests_total{{service="{service_name}"}}[5m])) * 100
        '''
        result = await self._query(query)
        if result is not None:
            return round(result, 2)
        
        return None

    async def get_request_volume(self, service_name: str) -> Optional[float]:
        """Get current QPS (queries per second) for a service.
        
        Args:
            service_name: Name of the service to query
            
        Returns:
            Current QPS, or None if unavailable
        """
        query = f'''
            sum(rate(http_requests_total{{service="{service_name}"}}[1m]))
        '''
        result = await self._query(query)
        if result is not None:
            return round(result, 2)
        
        # Fallback for Micrometer-style metrics
        query_alt = f'''
            sum(rate(http_server_requests_seconds_count{{service="{service_name}"}}[1m]))
        '''
        result = await self._query(query_alt)
        if result is not None:
            return round(result, 2)
        
        return None

    async def get_all_metrics(self, service_name: str) -> dict:
        """Get all available metrics for a service.
        
        Args:
            service_name: Name of the service to query
            
        Returns:
            Dictionary with all available metrics
        """
        metrics = {
            "service_name": service_name,
            "error_rate_percent": None,
            "latency_p50_ms": None,
            "latency_p95_ms": None,
            "latency_p99_ms": None,
            "traffic_percentage": None,
            "request_volume_qps": None,
        }
        
        # Fetch all metrics in parallel
        error_rate = await self.get_error_rate(service_name)
        latency_p50 = await self.get_latency_p50(service_name)
        latency_p95 = await self.get_latency_p95(service_name)
        latency_p99 = await self.get_latency_p99(service_name)
        traffic = await self.get_traffic_percentage(service_name)
        volume = await self.get_request_volume(service_name)
        
        metrics["error_rate_percent"] = error_rate
        metrics["latency_p50_ms"] = latency_p50
        metrics["latency_p95_ms"] = latency_p95
        metrics["latency_p99_ms"] = latency_p99
        metrics["traffic_percentage"] = traffic
        metrics["request_volume_qps"] = volume
        
        return metrics


class MockMetricsProvider:
    """Mock metrics provider for testing and development without Prometheus.
    
    Returns simulated realistic metrics for demo purposes.
    """

    def __init__(self):
        """Initialize mock provider."""
        import random
        self._random = random

    async def get_error_rate(self, service_name: str) -> float:
        """Get simulated error rate."""
        return round(self._random.uniform(0.01, 2.5), 3)

    async def get_latency_p50(self, service_name: str) -> float:
        """Get simulated P50 latency."""
        return round(self._random.uniform(20, 80), 2)

    async def get_latency_p95(self, service_name: str) -> float:
        """Get simulated P95 latency."""
        return round(self._random.uniform(80, 250), 2)

    async def get_latency_p99(self, service_name: str) -> float:
        """Get simulated P99 latency."""
        return round(self._random.uniform(150, 500), 2)

    async def get_traffic_percentage(self, service_name: str) -> float:
        """Get simulated traffic percentage."""
        return round(self._random.uniform(5, 100), 2)

    async def get_request_volume(self, service_name: str) -> float:
        """Get simulated QPS."""
        return round(self._random.uniform(100, 5000), 2)

    async def get_all_metrics(self, service_name: str) -> dict:
        """Get all simulated metrics."""
        return {
            "service_name": service_name,
            "error_rate_percent": await self.get_error_rate(service_name),
            "latency_p50_ms": await self.get_latency_p50(service_name),
            "latency_p95_ms": await self.get_latency_p95(service_name),
            "latency_p99_ms": await self.get_latency_p99(service_name),
            "traffic_percentage": await self.get_traffic_percentage(service_name),
            "request_volume_qps": await self.get_request_volume(service_name),
        }

    async def close(self):
        """Close the provider (no-op for mock)."""
        pass


def get_metrics_provider() -> PrometheusMetricsProvider | MockMetricsProvider:
    """Factory function to get the appropriate metrics provider.
    
    Returns:
        PrometheusMetricsProvider if PROMETHEUS_URL is configured, 
        otherwise MockMetricsProvider for development/testing
    """
    prometheus_url = os.getenv("PROMETHEUS_URL", "").strip()
    
    if prometheus_url:
        logger.info(f"Using Prometheus metrics provider: {prometheus_url}")
        return PrometheusMetricsProvider(prometheus_url)
    else:
        logger.info("PROMETHEUS_URL not configured, using mock metrics provider")
        return MockMetricsProvider()

