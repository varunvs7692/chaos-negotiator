# Verification Checklist - Deployment History Fix

## Prerequisites ✓

- [ ] Python environment activated: `.\.venv\Scripts\Activate.ps1`
- [ ] Dependencies installed: `pip install -e .[dev]`
- [ ] Database clean: `rm deployment_history.db` (optional, for fresh start)

---

## Phase 1: Code Verification

### Syntax Check
```bash
python -m py_compile chaos_negotiator/server.py chaos_negotiator/agent/agent.py
```
- [ ] No syntax errors reported

### Linting Check  
```bash
python -m ruff check chaos_negotiator/server.py chaos_negotiator/agent/agent.py --select=F
```
- [ ] No undefined name (F) errors
- [ ] No unused variable errors (the earlier F841 should be gone)

### Import Check
```bash
python -c "from chaos_negotiator.agent.agent import ChaosNegotiatorAgent; print('✅ Imports OK')"
```
- [ ] `✅ Imports OK` appears

---

## Phase 2: Unit Tests

### Run Test Suite
```bash
python -m pytest tests/ -q
```
- [ ] All tests pass (or expected failures only)

### Run Custom Test Script
```bash
python test_deployment_history_flow.py
```
- [ ] Test 1: Record Single Result - PASS
- [ ] Test 2: Get History - PASS  
- [ ] Test 3: Record Multiple - PASS

---

## Phase 3: Manual Integration Test

### Start Server
```bash
python -m chaos_negotiator.server
```

Watch for:
- [ ] `✅ ChaosNegotiatorAgent initialized on API startup` in logs
- [ ] Server starts on port 8000
- [ ] No shutdown errors when closing

### In Another Terminal: Test Endpoint

#### Test 1: Health Check
```bash
curl http://localhost:8000/health
```
- [ ] Status: 200
- [ ] Response: `{"status":"healthy","agent_ready":true}`

#### Test 2: Record Result
```bash
curl -X POST http://localhost:8000/api/deployments/record-result \
  -H "Content-Type: application/json" \
  -d '{
    "deployment_id": "verify-001",
    "actual_error_rate_percent": 0.08,
    "actual_latency_change_percent": 2.5,
    "rollback_triggered": false
  }'
```

Expected Response (200):
```json
{
  "status": "success",
  "deployment_id": "verify-001",
  "final_score": <number>,
  "timestamp": "<ISO timestamp>"
}
```

- [ ] Status: 200
- [ ] Response contains all required fields
- [ ] final_score is a number between 0-100

**Server Logs Should Show:**
```
📝 Recording deployment result: verify-001
  Actual Error Rate: 0.08%
  Actual Latency Change: 2.5%
  Rollback Triggered: False
✅ Saving outcome to history store...
  Heuristic Score: XX.X
  ML Score: YY.Y
  Final Score: ZZ.Z
✏️ Outcome saved successfully
```

- [ ] All logging appears in server output

#### Test 3: Get History
```bash
curl http://localhost:8000/api/dashboard/history?limit=5
```

Expected Response (200):
```json
{
  "total": 1,
  "outcomes": [
    {
      "deployment_id": "verify-001",
      "heuristic_score": <number>,
      "ml_score": <number>,
      "final_score": <number>,
      "actual_error_rate": 0.08,
      "actual_latency_change": 2.5,
      "rollback_triggered": false,
      "timestamp": "<ISO timestamp>"
    }
  ]
}
```

- [ ] Status: 200
- [ ] total: 1 (at least)
- [ ] outcomes array contains our deployment
- [ ] All fields present with correct values

#### Test 4: Multiple Records
```bash
for i in {1..3}; do
  curl -X POST http://localhost:8000/api/deployments/record-result \
    -H "Content-Type: application/json" \
    -d "{\"deployment_id\": \"bulk-$i\", \"actual_error_rate_percent\": 0.$i, \"actual_latency_change_percent\": $i, \"rollback_triggered\": false}"
  sleep 0.5
done
```

Then check history:
```bash
curl http://localhost:8000/api/dashboard/history?limit=10 | grep -c "bulk-"
```

- [ ] Should show `3` (or 4 if Previous test record still there)

---

## Phase 4: Dashboard Verification

### Open Dashboard
```
http://localhost:8000
```

Watch the browser console (F12 → Console):

- [ ] You see periodic polling logs:
  ```
  [Dashboard] 🔄 Poll tick at HH:MM:SS
  [Dashboard] ✅ Data received: {...}
  ```

### Check Dashboard Sections

1. **Risk Assessment Card**
   - [ ] Shows a risk score (e.g., 64.27%)
   - [ ] Shows confidence (e.g., 87.59%)
   - [ ] Shows risk level (low/medium/high/critical)

2. **Canary Strategy Card**
   - [ ] Shows deployment stages (smoke, canary, full)
   - [ ] Shows traffic percentages for each stage
   - [ ] Shows durations

3. **Recent Deployment History**
   - [ ] **Section is visible** (most important!)
   - [ ] Shows table of deployments
   - [ ] Shows: Deployment ID, Score, Error Rate, Latency, Rollback, Time
   - [ ] Records from your tests appear (verify-001, bulk-1, bulk-2, bulk-3)
   - [ ] **NOT EMPTY** ✅

---

## Phase 5: Demo Script Test

### Run Interactive Demo
```bash
python demo_deployment_history.py
```

Expected output shows:
- [ ] Test 1: Record Successful Canary (3 stages)
  - [ ] Each stage records successfully
  - [ ] Final scores calculated
  
- [ ] Test 2: Record Failed Deployment  
  - [ ] Records with rollback_triggered=true
  - [ ] Higher error rate shown
  
- [ ] Test 3: Record Medium-Risk Deployment
  - [ ] Records with normal metrics
  
- [ ] **RECENT DEPLOYMENT HISTORY table appears**
  - [ ] Shows 5+ deployments
  - [ ] All data populated correctly
  - [ ] Timestamps are recent

---

## Phase 6: Error Handling

### Test Invalid Request
```bash
curl -X POST http://localhost:8000/api/deployments/record-result \
  -H "Content-Type: application/json" \
  -d '{"invalid": "data"}'
```

- [ ] Status: 400
- [ ] Returns error message

### Test Missing Field
```bash
curl -X POST http://localhost:8000/api/deployments/record-result \
  -H "Content-Type: application/json" \
  -d '{"deployment_id": "test"}'
```

- [ ] Status: 400
- [ ] Returns validation error

### Test Invalid Data Type
```bash
curl -X POST http://localhost:8000/api/deployments/record-result \
  -H "Content-Type: application/json" \
  -d '{"deployment_id": "test", "actual_error_rate_percent": "not_a_number", "actual_latency_change_percent": 1.0, "rollback_triggered": false}'
```

- [ ] Status: 400
- [ ] Returns type error

---

## Phase 7: Database Verification

### Check Database File
```bash
ls -la deployment_history.db
```
- [ ] File exists
- [ ] File size > 0 (has data)
- [ ] Recently modified (timestamp is recent)

### Optional: Query Database Directly
```bash
python -c "
from chaos_negotiator.predictors.history_store import DeploymentHistoryStore
store = DeploymentHistoryStore()
outcomes = store.recent(10)
print(f'Total outcomes: {len(outcomes)}')
for o in outcomes[:3]:
    print(f'  {o.deployment_id}: score={o.final_score:.1f}')
"
```

- [ ] Shows multiple outcomes
- [ ] Deployment IDs match what we recorded
- [ ] Scores are reasonable (0-100)

---

## Phase 8: Logging Verification

### Check Server Console Output

Verify these patterns appear:
- [ ] `📝 Recording deployment result: <id>`
- [ ] `✅ Saving outcome to history store...`
- [ ] `Heuristic Score: XX.X`
- [ ] `ML Score: YY.Y`
- [ ] `Final Score: ZZ.Z`
- [ ] `✏️ Outcome saved successfully`

### Check for No Errors
- [ ] No `ERROR` entries in logs
- [ ] No `exception` or `traceback`
- [ ] No `context is not defined` (old bug, now fixed)

---

## Phase 9: Complete Flow Test

### Full End-to-End

1. **Initial State**
   - [ ] Dashboard open
   - [ ] Recent History is empty (new database)

2. **Record 5 Results**
   ```bash
   python demo_deployment_history.py
   ```
   - [ ] Script completes without errors

3. **Refresh Dashboard**
   - [ ] F5 or wait for next poll (10s)
   - [ ] Recent History now shows 5 entries
   - [ ] All fields populated
   - [ ] Latest timestamp at top

4. **Verify Learning Loop**
   - [ ] Check server logs for weight updates
   - [ ] Auto-tuning scheduler running
   - [ ] ML model being refined

---

## Phase 10: Production Readiness Check

- [ ] Code syntax valid ✓
- [ ] All tests pass ✓
- [ ] Endpoint returns 200 on success ✓
- [ ] Endpoint returns 400 on error ✓
- [ ] Data saved to database ✓
- [ ] History endpoint returns data ✓
- [ ] Dashboard displays results ✓
- [ ] Logging is comprehensive ✓
- [ ] No memory leaks (process stable) ✓
- [ ] Clean shutdown without errors ✓

---

## Sign-Off Checklist

When all phases are complete:

```
Name: _________________
Date: _________________

Phase 1: Code Verification ........... ☐ PASS
Phase 2: Unit Tests .................. ☐ PASS
Phase 3: Manual Integration .......... ☐ PASS
Phase 4: Dashboard Verification ...... ☐ PASS
Phase 5: Demo Script Test ............ ☐ PASS
Phase 6: Error Handling .............. ☐ PASS
Phase 7: Database Verification ....... ☐ PASS
Phase 8: Logging Verification ........ ☐ PASS
Phase 9: Complete Flow Test .......... ☐ PASS
Phase 10: Production Readiness ....... ☐ PASS

Overall Status: ☐ READY FOR PRODUCTION
```

---

## Rollback Plan (if needed)

If something breaks:

1. Stop the server
2. Restore from git:
   ```bash
   git checkout HEAD -- chaos_negotiator/server.py chaos_negotiator/agent/agent.py
   ```
3. Delete database:
   ```bash
   rm deployment_history.db
   ```
4. Restart server

---

## Support

If tests fail:

1. **Check syntax:** `python -m py_compile`
2. **Check logs:** Full server output
3. **Check database:** Verify `deployment_history.db` exists
4. **Check imports:** Run import test
5. **Review changes:** See `CODE_CHANGES_SUMMARY.md`
6. **Consult docs:** See `DEPLOYMENT_HISTORY_FIXED.md`

✅ All systems ready for verification!
