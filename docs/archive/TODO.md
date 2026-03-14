# TODO: Real-time WebSocket Updates Implementation

## Tasks
- [x] Analyze codebase and understand current implementation
- [x] Fix server.py - Move background task from deprecated @app.on_event to lifespan
- [x] Update dashboard.html - Replace REST polling with WebSocket connection
- [x] Add CSS styles for connection status indicator
- [x] Test the implementation

## Changes Made

### 1. server.py
- Integrated background risk monitoring into the `lifespan` context manager (not in deprecated @app.on_event)
- The background task starts automatically when FastAPI starts and stops gracefully on shutdown
- Risk is recalculated every 5 seconds and stored in GLOBAL_STATE
- WebSocket endpoint `/ws/risk` streams risk data to clients

### 2. dashboard.html  
- Replaced REST polling with WebSocket connection to `/ws/risk`
- Risk data updates in real-time when WebSocket messages arrive
- Added connection status indicator showing real-time connection state
- Auto-reconnect logic when WebSocket disconnects
- History and canary data still fetched via REST but with longer interval (30s)

### 3. dashboard.css
- Added CSS styles for connection status indicator
- Green pulsing indicator when connected
- Red indicator when disconnected

