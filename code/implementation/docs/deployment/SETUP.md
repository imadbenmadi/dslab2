# Complete Setup Guide

Install and configure the Smart City Vehicular Task Offloading System.

## System Requirements

- **Python**: 3.8+
- **Node.js**: 14+
- **PostgreSQL**: 12+
- **Memory**: 4GB RAM
- **Storage**: 2GB free disk space

## Step 1: Clone / Setup (5 min)

```bash
# Navigate to project
cd dslab2/implementation

# Check Python
python --version  # Should be 3.8+
```

## Step 2: Install Dependencies (3 min)

```bash
# Python packages
pip install -r requirements.txt

# Frontend
cd frontend
npm install
cd ..
```

Check for errors. If you get package conflicts, try:

```bash
pip install --upgrade pip
pip install -r requirements.txt --no-cache-dir
```

## Step 3: Database Setup (2 min)

**Automatic (Recommended):**

```bash
python setup_postgresql.py
```

**Manual (if automatic fails):**

```bash
# Ensure PostgreSQL service is running
# Windows: Services → postgresql-x64-XX → Start
# Linux: sudo service postgresql start

# Create database
psql -U postgres -c "CREATE DATABASE smart_city;"

# Create tables
psql -U postgres -d smart_city << EOF
CREATE TABLE metrics_history (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    payload JSONB NOT NULL
);
CREATE TABLE task_events (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    payload JSONB NOT NULL
);
CREATE TABLE runtime_logs (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    payload JSONB NOT NULL
);
CREATE INDEX idx_metrics_created_at ON metrics_history (created_at DESC);
CREATE INDEX idx_tasks_created_at ON task_events (created_at DESC);
CREATE INDEX idx_logs_created_at ON runtime_logs (created_at DESC);
EOF
```

## Step 4: Verify Setup (1 min)

```bash
python complete_system_setup.py
```

Expected output:

```
[OK]  Python packages installed
[OK]  PostgreSQL connected
[OK]  Redis available (optional)
[OK]  CARLA trajectory data loaded
[OK]  Baselines implemented
```

## Step 5: Start System (2 min)

**Terminal 1: Backend**

```bash
python app.py proposed
```

Wait for:

```
[INFO] Flask API running on http://0.0.0.0:5000
[INFO] WebSocket ready on ws://0.0.0.0:8765
```

**Terminal 2: Frontend**

```bash
cd frontend
npm start
```

Wait for:

```
Compiled successfully!
Local: http://localhost:3000
```

**Terminal 3: Browser**

```
http://localhost:3000
```

You should see:

- Dashboard with 4 metric cards
- Control buttons (Start/Stop/Reset)
- System type selector
- Istanbul live map

## Step 6: Run First Simulation (2 min)

1. Click **"▶ Start"** button
2. Watch metrics update in real-time
3. Click **"Open Full Istanbul Live Map"** to see vehicles moving
4. After 30 seconds, click **"⏹ Stop"**

**Congratulations!** System is running.

---

## Optional: Advanced Configuration

### Redis Setup (Optional - for faster state caching)

**Windows (WSL):**

```bash
wsl ubuntu -u root bash -c "apt-get update && apt-get install redis-server -y && redis-server --daemonize yes"
```

**Linux:**

```bash
sudo apt-get install redis-server
sudo systemctl start redis-server
```

Then enable in `.env`:

```ini
ENABLE_REDIS_STATE=true
```

### Tune System Parameters

Edit `.env`:

```ini
# Vehicles & Tasks
N_VEHICLES=50            # Increase for more congestion
TASK_RATE_HZ=10         # Tasks per second per vehicle
SIM_DURATION_S=600      # Simulation length

# Network
BANDWIDTH_MBPS=100
FOG_COVERAGE_RADIUS=250 # Coverage zone size (meters)

# Performance
FOG_MIPS=2000          # Fog processing power
CLOUD_MIPS=8000        # Cloud processing power
TOTAL_DEADLINE_MS=200  # Task deadline
```

### Enable Logging

Default: `results/logs/smart_city.log`

Change in `app_runtime/api_routes.py`:

```python
LOG_LEVEL = "DEBUG"  # More verbose
```

---

## Troubleshooting

### Port Already in Use

```bash
# Find what's using port 5000
netstat -ano | findstr :5000

# Kill process (replace PID)
taskkill /PID 1234 /F

# Or use different port
python app.py proposed --port 5001
```

### PostgreSQL Connection Failed

```bash
# Check service
pg_isready -h localhost

# Restart service
# Windows: Services → postgresql-x64-XX → Restart
# Linux: sudo systemctl restart postgresql

# Then rerun setup
python setup_postgresql.py
```

### Frontend Won't Start

```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm start
```

### High Memory Usage

- Reduce N_VEHICLES to 20
- Reduce SIM_DURATION_S to 300
- Clear results: `rm results/*.jsonl`

---

## Performance Targets

After setup, you should see:

| Metric                   | Target | Status |
| ------------------------ | ------ | ------ |
| Dashboard Load Time      | <2s    | [OK]   |
| WebSocket Connection     | <1s    | [OK]   |
| Metrics Update Frequency | 1/sec  | [OK]   |
| Map Render               | 60 FPS | [OK]   |
| Database Insert Latency  | <100ms | [OK]   |

---

## Next Steps

1. **Run Quick Start:** [docs/guides/QUICKSTART.md](../guides/QUICKSTART.md)
2. **Understand Architecture:** [docs/architecture/ARCHITECTURE.md](../architecture/ARCHITECTURE.md)
3. **Compare Baselines:** [docs/architecture/BASELINES.md](../architecture/BASELINES.md)
4. **Deploy to Production:** [DEPLOYMENT.md](./DEPLOYMENT.md)

---

**Setup Complete!** Proceed to [QUICKSTART.md](../guides/QUICKSTART.md).
