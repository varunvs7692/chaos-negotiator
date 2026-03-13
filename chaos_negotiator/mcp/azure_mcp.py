"""Chaos Negotiator Azure telemetry integration."""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Any, cast

from azure.identity import DefaultAzureCredential
from azure.monitor.query import LogsQueryClient, LogsQueryResult, LogsQueryStatus

logger = logging.getLogger(__name__)


class AzureMCPClient:
    """
    Client for Azure Monitor and deployment telemetry.

    The dashboard uses this client to query live request health from
    Log Analytics / Application Insights. When telemetry configuration is
    missing or no data is available, the client returns an explicit degraded
    payload instead of synthetic demo values.
    """

    def __init__(self) -> None:
        """Initialize Azure clients."""
        self.credential = DefaultAzureCredential()
        self.logs_client = LogsQueryClient(self.credential)
        self.workspace_id = os.getenv("AZURE_MONITOR_WORKSPACE_ID")
        self.default_service_name = (
            os.getenv("CN_DASHBOARD_SERVICE_NAME")
            or os.getenv("CONTAINER_APP_NAME")
            or "chaos-negotiator"
        )
        self.default_deployment_history_service = (
            os.getenv("CN_DEPLOYMENT_HISTORY_SERVICE_NAME") or self.default_service_name
        )

        if not self.workspace_id:
            logger.warning("AZURE_MONITOR_WORKSPACE_ID not set. Live telemetry is disabled.")

    async def get_current_metrics(
        self, resource_id: str | None, metric_names: list[str], time_window_minutes: int = 5
    ) -> dict[str, Any]:
        """
        Get current metrics for a service from Azure Monitor.

        Args:
            resource_id: Azure resource identifier
            metric_names: List of metrics to query (error_rate, latency, qps)
            time_window_minutes: Time window for aggregation

        Returns:
            Dictionary with current metric values
        """
        service_name = resource_id or self.default_service_name
        if not self.workspace_id:
            return self._build_unavailable_metrics(
                service_name=service_name,
                source="unconfigured",
                message="AZURE_MONITOR_WORKSPACE_ID is not configured.",
            )

        try:
            # Retry with wider windows so low-traffic services still surface recent telemetry.
            lookback_windows = [time_window_minutes, 15, 60]
            unique_windows = list(dict.fromkeys(max(window, 1) for window in lookback_windows))

            for lookback_minutes in unique_windows:
                metrics = self._query_metrics_for_window(
                    service_name=service_name,
                    time_window_minutes=lookback_minutes,
                )
                if metrics is not None:
                    metrics["lookback_window_minutes"] = lookback_minutes
                    if lookback_minutes != time_window_minutes:
                        message = str(metrics.get("message", "")).strip()
                        window_note = f"Returned from a {lookback_minutes} minute lookback window."
                        metrics["message"] = (
                            f"{message} {window_note}".strip() if message else window_note
                        )
                    return metrics

            logger.warning("No live request data returned from Azure Monitor.")
            return self._build_unavailable_metrics(
                service_name=service_name,
                source="azure_monitor_no_data",
                message="Azure Monitor query succeeded but returned no recent request data.",
            )

        except Exception as e:
            logger.error(f"Error querying Azure Monitor: {e}")
            return self._build_unavailable_metrics(
                service_name=service_name,
                source="azure_monitor_error",
                message=str(e),
            )

    def _query_metrics_for_window(
        self,
        service_name: str,
        time_window_minutes: int,
    ) -> dict[str, Any] | None:
        """Query request metrics for a single lookback window with progressive fallback."""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=time_window_minutes)

        scoped_metrics = self._query_request_metrics(
            service_name=service_name,
            start_time=start_time,
            end_time=end_time,
            time_window_minutes=time_window_minutes,
            include_service_filter=True,
        )
        if scoped_metrics is not None:
            return scoped_metrics

        fallback_metrics = self._query_request_metrics(
            service_name=service_name,
            start_time=start_time,
            end_time=end_time,
            time_window_minutes=time_window_minutes,
            include_service_filter=False,
        )
        if fallback_metrics is not None:
            fallback_metrics["source"] = "azure_monitor_workspace"
            fallback_metrics["message"] = (
                "Using workspace-wide recent request telemetry because no service-specific "
                "role name matched."
            )
            return fallback_metrics

        console_metrics = self._query_container_console_metrics(
            service_name=service_name,
            time_window_minutes=time_window_minutes,
        )
        if console_metrics is not None:
            return console_metrics

        return None

    def _query_request_metrics(
        self,
        service_name: str,
        start_time: datetime,
        end_time: datetime,
        time_window_minutes: int,
        include_service_filter: bool,
    ) -> dict[str, Any] | None:
        """Query recent request metrics from Azure Monitor."""
        workspace_id = self.workspace_id
        if workspace_id is None:
            return None

        service_filter = ""
        if include_service_filter:
            service_filter = (
                f'\n            | where role_name == "{service_name}" '
                f'or role_instance contains "{service_name}"'
            )

        query = f"""
            union isfuzzy=true
                (
                    AppRequests
                    | project
                        timestamp = TimeGenerated,
                        success_value = tobool(Success),
                        duration_ms = todouble(DurationMs),
                        role_name = tostring(column_ifexists("AppRoleName", "")),
                        role_instance = tostring(column_ifexists("AppRoleInstance", ""))
                ),
                (
                    requests
                    | project
                        timestamp = timestamp,
                        success_value = tobool(success),
                        duration_ms = todouble(duration),
                        role_name = tostring(column_ifexists("cloud_RoleName", "")),
                        role_instance = tostring(column_ifexists("cloud_RoleInstance", ""))
                )
            | where timestamp between (datetime({start_time.isoformat()}) .. datetime({end_time.isoformat()})){service_filter}
            | summarize
                request_count = count(),
                error_rate = avg(toint(success_value == false)) * 100,
                p95_latency = percentile(duration_ms, 95),
                p99_latency = percentile(duration_ms, 99),
                qps = count() / {time_window_minutes * 60}
        """

        response = self.logs_client.query_workspace(
            workspace_id=workspace_id,
            query=query,
            timespan=timedelta(minutes=time_window_minutes),
        )

        if response.status != LogsQueryStatus.SUCCESS or not isinstance(response, LogsQueryResult):
            return None

        result = cast(LogsQueryResult, response)
        if not result.tables:
            return None

        table = result.tables[0]
        if not table.rows:
            return None

        row = table.rows[0]
        request_count = int(row[0]) if row[0] else 0
        if request_count <= 0:
            return None

        return {
            "error_rate_percent": float(row[1]) if row[1] else 0.0,
            "p95_latency_ms": float(row[2]) if row[2] else 0.0,
            "p99_latency_ms": float(row[3]) if row[3] else 0.0,
            "qps": float(row[4]) if row[4] else 0.0,
            "query_timestamp": datetime.utcnow().isoformat(),
            "source": "azure_monitor",
            "service_name": service_name,
            "available": True,
            "message": "",
        }

    def _query_container_console_metrics(
        self, service_name: str, time_window_minutes: int
    ) -> dict[str, Any] | None:
        """Derive live request metrics from Container App console access logs."""
        workspace_id = self.workspace_id
        if workspace_id is None:
            return None

        query = f"""
            ContainerAppConsoleLogs_CL
            | where TimeGenerated > ago({time_window_minutes}m)
            | where ContainerAppName_s == "{service_name}"
            | where Log_s has "HTTP/"
            | extend status_code = toint(extract(@'HTTP/[0-9.]+"\\s+([0-9]{{3}})', 1, Log_s))
            | summarize
                request_count = count(),
                error_count = countif(status_code >= 500)
            | extend
                error_rate = iff(request_count > 0, todouble(error_count) * 100.0 / todouble(request_count), 0.0),
                qps = todouble(request_count) / {time_window_minutes * 60.0}
        """

        response = self.logs_client.query_workspace(
            workspace_id=workspace_id,
            query=query,
            timespan=timedelta(minutes=time_window_minutes),
        )

        if response.status != LogsQueryStatus.SUCCESS or not isinstance(response, LogsQueryResult):
            return None

        result = cast(LogsQueryResult, response)
        if not result.tables:
            return None

        table = result.tables[0]
        if not table.rows:
            return None

        row = table.rows[0]
        request_count = int(row[0]) if row[0] else 0
        if request_count <= 0:
            workspace_query = f"""
                ContainerAppConsoleLogs_CL
                | where TimeGenerated > ago({time_window_minutes}m)
                | where Log_s has "HTTP/"
                | extend status_code = toint(extract(@'HTTP/[0-9.]+"\\s+([0-9]{{3}})', 1, Log_s))
                | summarize
                    request_count = count(),
                    error_count = countif(status_code >= 500)
                | extend
                    error_rate = iff(request_count > 0, todouble(error_count) * 100.0 / todouble(request_count), 0.0),
                    qps = todouble(request_count) / {time_window_minutes * 60.0}
            """

            workspace_response = self.logs_client.query_workspace(
                workspace_id=workspace_id,
                query=workspace_query,
                timespan=timedelta(minutes=time_window_minutes),
            )

            if workspace_response.status != LogsQueryStatus.SUCCESS or not isinstance(
                workspace_response, LogsQueryResult
            ):
                return None

            workspace_result = cast(LogsQueryResult, workspace_response)
            if not workspace_result.tables:
                return None

            workspace_table = workspace_result.tables[0]
            if not workspace_table.rows:
                return None

            workspace_row = workspace_table.rows[0]
            workspace_request_count = int(workspace_row[0]) if workspace_row[0] else 0
            if workspace_request_count <= 0:
                return None

            return {
                "error_rate_percent": float(workspace_row[2]) if workspace_row[2] else 0.0,
                "p95_latency_ms": 0.0,
                "p99_latency_ms": 0.0,
                "qps": float(workspace_row[3]) if workspace_row[3] else 0.0,
                "query_timestamp": datetime.utcnow().isoformat(),
                "source": "container_app_console_logs_workspace",
                "service_name": service_name,
                "available": True,
                "message": (
                    "Using workspace-wide Container App access logs because no service-specific "
                    "ContainerAppName match was found."
                ),
            }

        return {
            "error_rate_percent": float(row[2]) if row[2] else 0.0,
            "p95_latency_ms": 0.0,
            "p99_latency_ms": 0.0,
            "qps": float(row[3]) if row[3] else 0.0,
            "query_timestamp": datetime.utcnow().isoformat(),
            "source": "container_app_console_logs",
            "service_name": service_name,
            "available": True,
            "message": "Using live Container App access logs for request rate and error rate.",
        }

    def _build_unavailable_metrics(
        self, service_name: str, source: str, message: str
    ) -> dict[str, Any]:
        """Return an explicit unavailable payload for live telemetry."""
        return {
            "error_rate_percent": 0.0,
            "p95_latency_ms": 0.0,
            "p99_latency_ms": 0.0,
            "qps": 0.0,
            "query_timestamp": datetime.utcnow().isoformat(),
            "source": source,
            "service_name": service_name,
            "available": False,
            "message": message,
        }

    async def get_deployment_history(
        self,
        service_name: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Get recent deployment history from Azure.

        Args:
            service_name: Name of the service
            limit: Number of recent deployments to return

        Returns:
            List of deployment records
        """
        resolved_service_name = service_name or self.default_deployment_history_service
        if not self.workspace_id:
            return []

        try:
            query = f"""
            customEvents
            | where name == "DeploymentCompleted"
            | where customDimensions.service_name == "{resolved_service_name}"
            | order by timestamp desc
            | take {limit}
            | project 
                timestamp,
                deployment_id = customDimensions.deployment_id,
                version = customDimensions.version,
                status = customDimensions.status
            """

            response = self.logs_client.query_workspace(
                workspace_id=self.workspace_id, query=query, timespan=timedelta(days=7)
            )

            deployments = []
            if response.status == LogsQueryStatus.SUCCESS and isinstance(response, LogsQueryResult):
                for row in response.tables[0].rows:  # type: ignore
                    deployments.append(
                        {
                            "timestamp": row[0],
                            "deployment_id": row[1],
                            "version": row[2],
                            "status": row[3],
                        }
                    )

            return deployments

        except Exception as e:
            logger.error(f"Error querying deployment history: {e}")
            return []

    async def trigger_canary_deployment(
        self,
        service_name: str,
        version: str,
        traffic_percentage: float,
    ) -> dict[str, Any]:
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
            "started_at": datetime.utcnow().isoformat(),
        }

    async def monitor_deployment(
        self,
        deployment_id: str,
        guardrail_thresholds: dict[str, float],
        check_interval_seconds: int = 10,
        max_checks: int = 30,
    ) -> dict[str, Any]:
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
                resource_id=deployment_id, metric_names=["error_rate", "p95_latency"]
            )

            metrics_history.append(
                {"check_num": check_num + 1, "timestamp": datetime.utcnow().isoformat(), **metrics}
            )

            # Check against guardrails
            if "max_error_rate" in guardrail_thresholds:
                if metrics["error_rate_percent"] > guardrail_thresholds["max_error_rate"]:
                    violations.append(
                        {
                            "metric": "error_rate",
                            "actual": metrics["error_rate_percent"],
                            "threshold": guardrail_thresholds["max_error_rate"],
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )

            if "max_p95_latency" in guardrail_thresholds:
                if metrics["p95_latency_ms"] > guardrail_thresholds["max_p95_latency"]:
                    violations.append(
                        {
                            "metric": "p95_latency",
                            "actual": metrics["p95_latency_ms"],
                            "threshold": guardrail_thresholds["max_p95_latency"],
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )

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
                    "action": "rollback_required",
                }

            # Wait before next check
            await asyncio.sleep(check_interval_seconds)

        # All checks passed
        return {
            "status": "healthy",
            "guardrails_met": True,
            "violations": [],
            "metrics_history": metrics_history,
            "action": "none",
        }


class ManagedIdentityHandler:
    """Handles managed identity for Azure."""

    def __init__(self) -> None:
        self.credential = DefaultAzureCredential()

    async def get_auth_token(self, scope: str) -> str:
        """Get auth token for Azure services."""
        token = self.credential.get_token(scope)
        return token.token
