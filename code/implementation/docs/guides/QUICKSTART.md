# Quick Start (5 Minutes)

Get the system running in 5 minutes.

## Prerequisites

- Python 3.8+
- Node.js 14+
- PostgreSQL installed (service can start later)

## Installation (2 min)

```bash
# 1. Install Python packages
pip install -r requirements.txt

# 2. Install frontend
cd frontend
npm install
cd ..
```

## Setup (1 min)

```bash
# 1. Configure PostgreSQL database
python setup_postgresql.py

# You'll see:
# [OK]  Connection to PostgreSQL successful
# [OK]  Database 'smart_city' created
# [OK]  Tables initialized
```

**If it fails:** PostgreSQL service not running

```bash
# Windows: Start PostgreSQL in Services (search "Services")
# Linux: sudo service postgresql start
# Mac: brew services start postgresql
```

## Run Simulation (2 min)

**Terminal 1 - Backend:**

```bash
python app.py proposed
```

Expected output:

```
[2026-03-31 14:23:00] Starting Smart City Simulator
[2026-03-31 14:23:01] System Type: proposed
[2026-03-31 14:23:02] Flask API running on http://0.0.0.0:5000
[2026-03-31 14:23:03] WebSocket server ready on ws://0.0.0.0:8765
[2026-03-31 14:23:04] Waiting for connections...
```

**Terminal 2 - Frontend:**

```bash
cd frontend
npm start
```

Expected output:

```
Compiled successfully!

You can now view react-app in the browser.

  Local:            http://localhost:3000
  On Your Network:  http://192.168.1.X:3000

Note that the development build is not optimized.
```

**Terminal 3 - Browser:**

```
http://localhost:3000
```

## Test It (You're done!)

1. **Start Simulation**
    - Click the green "▶ Start" button
    - Watch the metrics update in real-time

2. **View Real-Time Map**
    - Click "Open Full Istanbul Live Map"
    - You should see:
        - 50 blue vehicle icons moving
        - 4 green fog nodes
        - Red coverage circles around each fog
        - Yellow lines for fog-to-fog connections
        - Green lines for device-to-fog connections

3. **Check Metrics**
    - Deadline Success Rate (top left)
    - Avg Latency (top left)
    - Tasks Processed (top left)

4. **Compare Baselines** (Optional)
    - Click "Stop"
    - Select "Baseline 1 (NSGA-II)"
    - Click "Start"
    - Compare metrics across all 4 systems

## Common Tasks

### Stop Simulation

Click red "⏹ Stop" button

### Reset System

Click gray "↻ Reset" button

### Retrain Agents

Click orange "🔄 Retrain AI" button
(Runs offline bootstrap with NSGA-II)

### View System Health

Click "Open Full Logic Explorer" → System Explorer tab
Shows:

- Storage health (Redis/PostgreSQL status)
- Agent rewards & training progress
- Network statistics

### Check Fog-to-Fog Handoffs

1. Go to full map ("/map")
2. Expand "Connections & Handoffs" panel
3. Look for "Fog→Fog" count > 0
4. Click on individual handoff events in timeline

## What's Happening Behind the Scenes

1. **Simulation** (Python/SimPy)
    - 50 vehicles generate tasks at 10 Hz
    - Tasks routed to fog/cloud based on Agent1 decision
    - Network optimized by Agent2 SDN controller
    - Measurements recorded

2. **Storage** (PostgreSQL/Redis)
    - Real-time metrics cached in Redis
    - Historical data persisted in PostgreSQL
    - API reads from both for REST/WebSocket

3. **Frontend** (React)
    - Fetches metrics every 1 second
    - Fetches map state every 500ms
    - Renders with Leaflet.js map library
    - WebSocket for live updates

## Troubleshooting

### Port Already in Use

```bash
# Port 5000 used? Try:
python app.py proposed --port 5001

# Port 3000 used? Try:
PORT=3001 npm start
```

### PostgreSQL Connection Failed

```bash
# Check if service running:
psql -U postgres -d smart_city -c "SELECT 1"

# If not, start service:
# Windows: Services → PostgreSQL → Start
# Linux: sudo service postgresql start
```

### No Metrics Appearing

1. Click "Start" button (simulation must be running)
2. Wait 10 seconds for data to accumulate
3. Check browser console (F12) for errors
4. Check backend logs in `results/logs/`

### Frontend Won't Compile

```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm start
```

## Next Steps

- **Read** [docs/guides/FOG_HANDOFF.md](../guides/FOG_HANDOFF.md) for handoff mechanics
- **Understand** [docs/architecture/BASELINES.md](../architecture/BASELINES.md) for algorithms
- **Deploy** [docs/deployment/DEPLOYMENT.md](../deployment/DEPLOYMENT.md) for production
- **Configure** [docs/deployment/CONFIG.md](../deployment/CONFIG.md) for tuning

---

**That's it!** You now have a running smart city simulation with real-time dashboard.
