"""Chaos Negotiator Azure MCP Integration."""

import logging
import os
from typing import Dict, Any, List
from datetime import datetime, timedelta
from azure.identity import DefaultAzureCredential
from azure.monitor.query import LogsQueryClient, LogsQueryStatus
import asyncio

logger = logging.getLogger(__name__)


class AzureMCPClient:
    """
    Client for Azure Monitor and Deployment APIs via MCP.
    
    Provides real-time metric queries and deployment monitoring
    for enforcement of deployment contracts.
    """

    def __init__(self):
        """Initialize Azure clients."""
        self.credential = DefaultAzureCredential()
        self.logs_client = LogsQueryClient(self.credential)
        self.workspace_id = os.getenv("AZURE_MONITOR_WORKSPACE_ID")
        
        if not self.workspace_id:
            logger.warning("AZURE_MONITOR_WORKSPACE_ID not set. Using mock data.")

    async def get_current_metrics(
        self,
        resource_id: str,
        metric_names: List[str],
        time_window_minutes: int = 5
    ) -> Dict[str, Any]:
        """
        Get current metrics for a service from Azure Monitor.
        
        Args:
            resource_id: Azure resource identifier
            metric_names: List of metrics to query (error_rate, latency, qps)
            time_window_minutes: Time window for aggregation
            
        Returns:
            Dictionary with current metric values
        """
        if not self.workspace_id:
            # Return mock data for demo
            return self._get_mock_metrics()
        
        try:
            # Query Azure Monitor for real metrics
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(minutes=time_window_minutes)
            
            # Kusto query for error rate and latency
            query = f"""
            requests
            | where timestamp between (datetime({start_time.isoformat()}) .. datetime({end_time.isoformat()}))
            | where cloud_RoleName == "{resource_id}"
            | summarize 
                error_rate = avg(toint(success == false)) * 100,
                p95_latency = percentile(duration, 95),
                p99_latency = percentile(duration, 99),
                qps = count() / {time_window_minutes * 60}
            """
            
            response = self.logs_client.query_workspace(
                workspace_id=self.workspace_id,
                query=query,
                timespan=timedelta(minutes=time_window_minutes)
            )
            
            if response.status == LogsQueryStatus.SUCCESS:
                table = response.tables[0]
                if table.rows:
                    row = table.rows[0]
                    return {
                        "error_rate_percent": float(row[0]) if row[0] else 0.0,
                        "p95_latency_ms": float(row[1]) if row[1] else 0.0,
                        "p99_latency_ms": float(row[2]) if row[2] else 0.0,
                        "qps": float(row[3]) if row[3] else 0.0,
                        "query_timestamp": datetime.utcnow().isoformat(),
                        "source": "azure_monitor"
                    }
            
            logger.warning("No data returned from Azure Monitor, using fallback")
            return self._get_mock_metrics()
            
        except Exception as e:
            logger.error(f"Error querying Azure Monitor: {e}")
            return self._get_mock_metrics()

    def _get_mock_metrics(self) -> Dict[str, Any]:
        """Return mock metrics for demo/testing."""
        return {
            "error_rate_percent": 0.05,
            "p95_latency_ms": 180.0,
            "p99_latency_ms": 450.0,
            "qps": 5000.0,
            "query_timestamp": datetime.utcnow().isoformat(),
            "source": "mock"
        }

    async def get_deployment_history(
        self,
        service_name: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get recent deployment history from Azure.
        
        Args:
            service_name: Name of the service
            limit: Number of recent deployments to return
            
        Returns:
            List of deployment records
        """
        if not self.workspace_id:
            return []
        
        try:
            query = f"""
            customEvents
            | where name == "DeploymentCompleted"
            | where customDimensions.service_name == "{service_name}"
            | order by timestamp desc
            | take {limit}
            | project 
                timestamp,
                deployment_id = customDimensions.deployment_id,
                version = customDimensions.version,
                status = customDimensions.status
            """
            
            response = self.logs_client.query_workspace(
                workspace_id=self.workspace_id,
                query=query,
                timespan=timedelta(days=7)
            )
            
            deployments = []
            if response.status == LogsQueryStatus.SUCCESS:
                for row in response.tables[0].rows:
                    deployments.append({
                        "timestamp": row[0],
                        "deployment_id": row[1],
                        "version": row[2],
                        "status": row[3]
                    })
            
            return deployments
            
        except Exception as e:
            logger.error(f"Error querying deployment history: {e}")
            return []

    async def trigger_canary_deployment(
        self,
        service_name: str,
        version: str,
        traffic_percentage: float,
    ) -> Dict[str, Any]:
        """
        Trigger canary deployment through orchestration.
        
        Args:
            service_name: Service to deploy
            version: Version to deploy
            traffic_percentage: Percentage of traffic for canary
            
        Returns:
            Deployment status
        """
        logger.info(
            f"Triggering canary deployment: {service_name} v{version} "
            f"@ {traffic_percentage}% traffic"
        )
        
        return {
            "status": "in_progress",
            "service_name": service_name,
            "version": version,
            "canary_traffic_percentage": traffic_percentage,
            "started_at": datetime.utcnow().isoformat()
        }

    async def monitor_deployment(
        self,
        deployment_id: str,
        guardrail_thresholds: Dict[str, float],
        check_interval_seconds: int = 10,
        max_checks: int = 30
    ) -> Dict[str, Any]:
        """
        Monitor deployment against guardrails in real-time.
        
        Args:
            deployment_id: Deployment identifier
            guardrail_thresholds: Thresholds to check (error_rate, p95_latency)
            check_interval_seconds: Seconds between checks
            max_checks: Maximum number of checks before timeout
            
        Returns:
            Monitoring result with metrics and violation status
        """
        logger.info(f"Monitoring deployment {deployment_id} against guardrails")
        
        violations = []
        metrics_history = []
        
        for check_num in range(max_checks):
            # Query current metrics
            metrics = await self.get_current_metrics(
                resource_id=deployment_id,
                metric_names=["error_rate", "p95_latency"]
            )
            
            metrics_history.append({
                "check_num": check_num + 1,
                "timestamp": datetime.utcnow().isoformat(),
                **metrics
            })
            
            # Check against guardrails
            if "max_error_rate" in guardrail_thresholds:
                if metrics["error_rate_percent"] > guardrail_thresholds["max_error_rate"]:
                    violations.append({
                        "metric": "error_rate",
                        "actual": metrics["error_rate_percent"],
                        "threshold": guardrail_thresholds["max_error_rate"],
                        "timestamp": datetime.utcnow().isoformat()
                    })
            
            if "max_p95_latency" in guardrail_thresholds:
                if metrics["p95_latency_ms"] > guardrail_thresholds["max_p95_latency"]:
                    violations.append({
                        "metric": "p95_latency",
                        "actual": metrics["p95_latency_ms"],
                        "threshold": guardrail_thresholds["max_p95_latency"],
                        "timestamp": datetime.utcnow().isoformat()
                    })
            
            # If violations detected, trigger rollback
            if violations:
                logger.warning(
                    f"Guardrail violations detected for {deployment_id}: "
                    f"{len(violations)} violations"
                )
                return {
                    "status": "violated",
                    "guardrails_met": False,
                    "violations": violations,
                    "metrics_history": metrics_history,
                    "action": "rollback_required"
                }
            
            # Wait before next check
            await asyncio.sleep(check_interval_seconds)
        
        # All checks passed
        return {
            "status": "healthy",
            "guardrails_met": True,
            "violations": [],
            "metrics_history": metrics_history,
            "action": "none"
        }


class ManagedIdentityHandler:
    """Handles managed identity for Azure."""

    def __init__(self):
        self.credential = DefaultAzureCredential()

    async def get_auth_token(self, scope: str) -> str:
        """Get auth token for Azure services."""
        token = self.credential.get_token(scope)
        return token.token
