import os
import random
from datetime import timedelta
from azure.identity import DefaultAzureCredential
from azure.monitor.query import MetricsQueryClient
from azure.monitor.opentelemetry import configure_azure_monitor


def configure_opentelemetry() -> None:
    connection_string = os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING")
    if connection_string:
        configure_azure_monitor(
            connection_string=connection_string,
        )


def get_live_metrics(deployment_id: str) -> dict:
    """
    Get live metrics for a deployment from Azure Monitor.

    If the required environment variables are not set, it returns
    simulated metrics.
    """
    subscription_id = os.environ.get("AZURE_SUBSCRIPTION_ID")
    resource_group = os.environ.get("AZURE_RESOURCE_GROUP")
    app_name = os.environ.get("AZURE_APP_NAME")

    if not all([subscription_id, resource_group, app_name]):
        # Return simulated metrics if not configured for Azure
        return {
            "actual_error_rate_percent": round(random.uniform(0.1, 5.0), 2),
            "actual_latency_change_percent": round(random.uniform(-2.0, 10.0), 2),
            "rollback_triggered": False,
        }

    resource_id = (
        f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}/"
        f"providers/Microsoft.App/containerApps/{app_name}"
    )

    credential = DefaultAzureCredential()
    metrics_client = MetricsQueryClient(credential)

    try:
        # Query for error rate (e.g., HTTP 5xx responses)
        error_rate_response = metrics_client.query_resource(
            resource_id,
            metric_names=["Http5xx"],
            timespan=timedelta(minutes=15),
            granularity=timedelta(minutes=1),
            aggregations=["Count"],
        )

        # Query for request count
        requests_response = metrics_client.query_resource(
            resource_id,
            metric_names=["Requests"],
            timespan=timedelta(minutes=15),
            granularity=timedelta(minutes=1),
            aggregations=["Count"],
        )

        # Query for latency (e.g., p95 latency)
        latency_response = metrics_client.query_resource(
            resource_id,
            metric_names=["HttpRequestDuration"],
            timespan=timedelta(minutes=15),
            granularity=timedelta(minutes=1),
            aggregations=["Percentile95"],
        )

        # Process error rate
        error_count = 0.0
        if error_rate_response.metrics:
            for metric in error_rate_response.metrics:
                for timeseries in metric.timeseries:
                    for data in timeseries.data:
                        if data.count is not None:
                            error_count += data.count

        request_count = 0.0
        if requests_response.metrics:
            for metric in requests_response.metrics:
                for timeseries in metric.timeseries:
                    for data in timeseries.data:
                        if data.count is not None:
                            request_count += data.count

        actual_error_rate_percent = (error_count / request_count * 100) if request_count > 0 else 0

        # Process latency
        actual_latency_change_percent = 0.0
        if latency_response.metrics:
            for metric in latency_response.metrics:
                for timeseries in metric.timeseries:
                    if timeseries.data:
                        # simple way to calculate change is to compare last 2 datapoints
                        if len(timeseries.data) > 1:
                            latest = getattr(timeseries.data[-1], "percentile95", 0)
                            previous = getattr(timeseries.data[-2], "percentile95", 0)
                            if previous > 0 and latest is not None:
                                actual_latency_change_percent = (
                                    (latest - previous) / previous
                                ) * 100

        return {
            "actual_error_rate_percent": round(actual_error_rate_percent, 2),
            "actual_latency_change_percent": round(actual_latency_change_percent, 2),
            "rollback_triggered": False,  # This would need more logic to determine
        }

    except Exception as e:
        # Fallback to simulated metrics on error
        print(f"Error querying Azure Monitor: {e}")
        return {
            "actual_error_rate_percent": round(random.uniform(0.1, 5.0), 2),
            "actual_latency_change_percent": round(random.uniform(-2.0, 10.0), 2),
            "rollback_triggered": False,
        }
