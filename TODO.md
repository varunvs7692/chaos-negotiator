# TODO: Real-time WebSocket Updates Implementation

## Tasks
- [x] Analyze codebase and understand current implementation
- [x] Fix server.py - Move background task from deprecated @app.on_event to lifespan
- [x] Update dashboard.html - Replace REST polling with WebSocket connection
- [x] Add CSS styles for connection status indicator
- [x] Create Prometheus metrics provider module
- [x] Integrate metrics provider into background monitoring loop
- [x] Update WebSocket to include live metrics data
- [x] Update dashboard to display live metrics

## Changes Made

### 1. server.py
- Integrated background risk monitoring into the `lifespan` context manager
- Added metrics provider initialization in lifespan
- Updated `update_risk_state()` to fetch live metrics from Prometheus (or mock)
- WebSocket endpoint `/ws/risk` now streams both risk assessment AND live metrics

### 2. chaos_negotiator/metrics/prometheus_provider.py (NEW)
- Created PrometheusMetricsProvider class for querying Prometheus HTTP API
- Functions: `get_error_rate()`, `get_latency_p95()`, `get_traffic_percentage()`, `get_request_volume()`, `get_all_metrics()`
- Created MockMetricsProvider for development/testing without Prometheus

### 3. dashboard.html  
- Replaced REST polling with WebSocket connection to `/ws/risk`
- Risk data and live metrics update in real-time
- Added connection status indicator showing real-time connection state
- Auto-reconnect logic when WebSocket disconnects

### 4. dashboard.css
- Added CSS styles for connection status indicator
- Green pulsing indicator when connected
- Red indicator when disconnected

## Configuration
- Set `PROMETHEUS_URL` environment variable to connect to a real Prometheus instance
- Set `MONITORED_SERVICE` to specify which service to monitor (default: "user-service")
- Without PROMETHEUS_URL, the system uses MockMetricsProvider with simulated data

