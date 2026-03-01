# Chaos Negotiator — Live Data Flow Debugging Guide

## 🔍 Current Status

After recent changes, comprehensive logging has been added to:
- **FastAPI endpoint** — logs every request, agent call, and response
- **React Dashboard** — logs every API call, data received, poll ticks
- **Axios service** — logs all HTTP requests and responses

---

## ✅ Step 1: Verify API is Returning Dynamic Data

### Direct Test (Terminal)

```bash
# Test 1: Call the endpoint multiple times, watch the values
curl http://localhost:8000/api/deployments/latest | jq .

# Wait 5 seconds
sleep 5

# Test 2: Call again - values should be slightly different or same
# (they're dynamic because of ensemble ML, but may appear similar for same context)
curl http://localhost:8000/api/deployments/latest | jq .

# Compare output. Watch for:
# - risk_percent: should be non-zero (typically 40-80 for demo context)
# - confidence_percent: should vary between calls (ML model adds noise)
# - risk_level: should be "moderate", "high", or "critical"
# - canary_stage: should be "smoke", "light", "half", "majority", or "full"
```

### Read Server Logs

While running `uvicorn chaos_negotiator.agent.api:app --reload`, you should see:

```
============================================================
[1709299200000] 🔵 API REQUEST: /api/deployments/latest
[1709299200000] Building demo context...
[1709299200000] ✅ Demo context built: deploy-demo-001
[1709299200000] 🔄 Calling agent.process_deployment()...
[1709299200000] ✅ Contract generated: contract-deploy-demo-001
[1709299200000] ✅ Risk Assessment: score=64.3, confidence=87.6%
[1709299200000] 🔄 Calling agent.generate_canary_policy()...
[1709299200000] ✅ Canary policy generated with 5 stages
[1709299200000] 📤 RESPONSE: risk=64.3%, confidence=87.6%, stage=smoke
[1709299200000] ✅ Request complete
============================================================
```

**✅ If you see this output, the API is working correctly.**

---

## ✅ Step 2: Verify React Dashboard is Polling

### Open Browser Developer Tools

1. Open dashboard at `http://localhost:3000`
2. Press `F12` to open Developer Tools
3. Go to **Console** tab

You should see output like:

```
[Dashboard] ⏰ Setting up 10s polling interval
[Dashboard] 🔵 Fetching latest deployment...
[API] 🔵 REQUEST: GET /api/deployments/latest
[API] ✅ RESPONSE (200):  {risk_percent: 64.27, confidence_percent: 87.59, ...}
[Dashboard] ✅ Data received: {risk_percent: 64.27, ...}

[Dashboard] 🔄 Poll tick at 14:35:20
[Dashboard] 🔵 Fetching latest deployment...
[API] 🔵 REQUEST: GET /api/deployments/latest
[API] ✅ RESPONSE (200):  {risk_percent: 64.27, confidence_percent: 87.59, ...}
[Dashboard] ✅ Data received: {risk_percent: 64.27, ...}
```

**✅ If you see polling happening every ~10 seconds with new API calls, it's working.**

---

## ✅ Step 3: Verify CORS is Working

The browser should NOT show CORS errors like:

```
❌ Access to XMLHttpRequest at 'http://localhost:8000/api/deployments/latest' 
from origin 'http://localhost:3000' has been blocked by CORS policy
```

If you see this error:
- **FastAPI server** must have CORS middleware (it does — already configured)
- **Make sure both servers are running**

Check API server has CORS:
```python
# In chaos_negotiator/agent/api.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## ✅ Step 4: Data Flow Checklist

| Component | Status | How to Verify |
|-----------|--------|---------------|
| **API Endpoint** | ✅ Returns real data | `curl localhost:8000/api/deployments/latest` |
| **React Polling** | ✅ Polls every 10s | Check browser Console for `Poll tick` messages |
| **CORS** | ✅ Enabled | No CORS blocking errors in Console |
| **Axios Config** | ✅ Correct baseURL | Check `frontend/src/services/api.js` baseURL is `http://localhost:8000` |
| **Agent Called** | ✅ Each request | Check server logs show `Calling agent.process_deployment()` |

---

## 🐛 Troubleshooting

### Symptom: Dashboard shows "Loading..." forever

**Possible causes:**
1. **React dev server not running**
   ```bash
   cd frontend
   npm start
   ```

2. **FastAPI server not running**
   ```bash
   uvicorn chaos_negotiator.agent.api:app --reload
   ```

3. **CORS error** (check browser Console)
   - Both servers must be accessible at their respective ports

### Symptom: Console shows "API Error"

Check Network tab in DevTools (F12 → Network):
1. Click the failed request
2. Check Response Status
3. Check Response body for error details

Common errors:
- **500**: API exception (check server logs)
- **404**: Endpoint doesn't exist (check URL)
- **CORS**: See CORS troubleshooting above

### Symptom: Values don't change between polls

This is **expected** if:
- Same demo context is used each time
- Ensemble predictor is stable on same input

To verify it's actually calling the agent:
1. Add a `random_factor` to the demo context
2. Or check server logs — each request should show new timestamp `[1709299200000+]`

---

## 🚀 Full End-to-End Test

Run this sequence to verify everything:

```bash
# Terminal 1: Start FastAPI (watch the logs)
uvicorn chaos_negotiator.agent.api:app --reload

# Terminal 2: Start React (watch for "webpack compiled")
cd frontend && npm start

# Terminal 3: Call API directly
curl http://localhost:8000/api/deployments/latest | jq .

# Browser: Open http://localhost:3000
# DevTools (F12): Watch Console for logs
# Expect: New API call every 10 seconds starting immediately
```

---

## 📊 Expected Data Structure

Each API response should match this shape:

```json
{
  "service": "payments",
  "risk_percent": 64.27,          // 0-100 scale
  "confidence_percent": 87.59,    // 0-100 scale
  "risk_level": "high",           // low, medium, high, critical
  "canary_stage": "smoke",        // smoke, light, half, majority, full
  "traffic_percent": 10.0         // 0-100 scale
}
```

---

## 🎯 Success Indicators

✅ API endpoint provides real data from `ChaosNegotiatorAgent.process_deployment()`
✅ React Dashboard polls every 10 seconds
✅ Browser Console shows no CORS errors
✅ Axios baseURL is correct and requests succeed
✅ Server logs show agent processing for each request
✅ Values are non-static (vary due to ensemble model)

When all these are confirmed, **live data flow is working**! 🚀
