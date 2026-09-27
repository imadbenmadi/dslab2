# Quick Setup Guide - Smart City Task Offloading System

## 🎯 TL;DR (Just want it running?)

```bash
# Terminal 1: Start backend
cd implementation
pip install -r requirements.txt
python main_server.py proposed

# Terminal 2: Start frontend
cd implementation/frontend
npm install
npm start

# Open http://localhost:3000 in browser
# Watch the dashboard light up!
```

---

## 📋 Detailed Setup Instructions

### Step 1: Install Python Dependencies

```bash
cd implementation

# Create virtual environment (recommended)
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

**Installed packages:**

- `torch` - Deep learning
- `simpy` - Discrete-event simulation
- `pymoo` - Multi-objective optimization
- `pandas`, `numpy` - Data manipulation
- `flask`, `flask-cors` - REST API
- `websockets` - Real-time updates
- `plotly`, `matplotlib` - Visualization

### Step 2: Install Node.js & React

**Install Node.js**

- Download from https://nodejs.org (LTS version recommended)
- Verify: `node --version` and `npm --version`

**Install frontend dependencies**

```bash
cd frontend
npm install
```

This installs:

- React 18
- Zustand (state management)
- Tailwind CSS (styling)
- Axios (HTTP)
- Recharts (charts)

### Step 3: Start Backend Server

```bash
# From implementation/ folder
python main_server.py proposed
```

**Options:**

- `proposed` (default) - Full DQN system (target: >85%)
- `baseline1` - Pure NSGA-II (47%)
- `baseline2` - TOF + NSGA-II (68%)
- `baseline3` - TOF + MMDE (81%)

**Expected output:**

```
====== SMART CITY VEHICULAR TASK OFFLOADING SYSTEM ======

 API Server:       http://localhost:5000
🔌 WebSocket:        ws://localhost:8765
📊 Dashboard:        http://localhost:3000

💻 System Type:      proposed
🏙️ Location:        Istanbul
🚗 Vehicles:         50
⚙️ Fog Nodes:        4

Press Ctrl+C to stop server
```

### Step 4: Start Frontend Dashboard

**In a new terminal:**

```bash
cd implementation/frontend
npm start
```

This will:

1. Compile React app
2. Open http://localhost:3000 in browser
3. Connect to WebSocket (ws://localhost:8765)

**Expected dashboard:**

- Real-time "Deadline Success Rate"
- Device utilization bars
- Network metrics
- Agent performance stats

---

## 🎮 Using the Dashboard

### Main Controls

**Top Right Buttons:**

1. **System Type Selector** - Choose baseline or proposed
2. **▶ Start** - Begin simulation
3. **⏹ Stop** - Pause simulation
4. **↻ Reset** - Clear all data

### Metrics Display

**Key Metrics (Top Row):**

- Deadline Success Rate (Target: >85%)
- Avg Latency (Target: <160ms)
- Tasks Processed (Total count)
- Throughput (tasks/second)

**Device Utilization (Middle Left):**

- Shows 5 devices: Fog1-4 + Cloud
- Green bar = current load
- Lower is better (0% = idle, 100% = max)

**Network Metrics (Middle Right):**

- Bandwidth used (45.3 / 100 Mbps)
- Congestion points (number of bottlenecks)

**Agent Performance (Bottom Left):**

- Agent 1: Task placement latency (ms)
- Agent 2: Network routing latency (ms)

**Handoff Activity (Bottom Right):**

- Total handoff events
- Task migrations (tasks moved during handoff)

---

## 📊 What to Expect

### Baseline 1 (Pure NSGA-II)

- Success Rate: **47%** (poor)
- Latency: **167ms** (high)
- Why: No real-time adaptation

### Baseline 2 (TOF Classification)

- Success Rate: **68%** (good)
- Latency: **205ms** (higher due to cloud routing)
- Why: Smart classification adds +21% improvement

### Baseline 3 (TOF + MMDE)

- Success Rate: **80%** (very good)
- Latency: **163ms** (better than B2)
- Why: Better optimization algorithm

### Proposed System (with DQN)

- Success Rate: **>85%** (excellent!)
- Latency: **150-160ms** (best)
- Device Load: Balanced across all nodes
- Why: Online learning adapts to real-time conditions

---

## 🔍 Monitoring the Simulation

### Real-Time Progress

- **Progress bar** at top shows simulation % complete
- **Simulation time** displays current elapsed time (0-900s)
- **Metrics update every 1 second** via WebSocket

### Success Rate Progression

Watch how success rate improves:

```
Time 0-100s:   ~80% (baseline starting level)
Time 100-300s: ~82% (agents learning)
Time 300-600s: ~84-85% (convergence)
Time 600-900s: ~85%+ (peak performance)
```

### Device Load Balancing

Good system should show:

- No single device at 100% (bottleneck)
- Load distributed across fog nodes
- Cloud load <30%

---

## 🔧 Common Customizations

### Change Simulation Duration

Edit `config.py`:

```python
SIMULATION_TIME = 1800  # 30 minutes instead of 900
```

### Change Vehicle Count

Edit `config.py`:

```python
NUM_VEHICLES = 100  # 100 vehicles instead of 50
```

### Reduce Latency Target

Edit visualization/api_server.py:

```python
'target': 120  # Lower target from 160ms
```

### Change Dashboard Colors

Edit frontend/src/components/Dashboard.jsx:

```javascript
color = 'text-blue-600'; // Change color
```

---

## 🐛 Troubleshooting

### Dashboard shows "No metrics available yet"

**Solution:**

- Wait 5-10 seconds for first metrics
- Check browser console (F12) for errors
- Verify WebSocket status in Console

### "Connection refused" on http://localhost:5000

**Solution:**

```bash
# Make sure backend is running
# Terminal 1 should show:
#  API Server: http://localhost:5000

# If not, run:
python main_server.py proposed
```

### WebSocket connection fails

**Solution:**

```bash
# Check if WebSocket server is running
# Should see:
# 🔌 WebSocket: ws://localhost:8765

# If port 8765 is in use:
lsof -i :8765  # Find process
kill <PID>      # Kill it
```

### npm install fails

**Solution:**

```bash
# Clear npm cache
npm cache clean --force

# Try again
npm install

# Or use yarn
npm install -g yarn
yarn install
```

### Port 5000 or 3000 already in use

**Solution:**

```bash
# Find process on port 5000
lsof -i :5000

# Kill it
kill <PID>

# Or use different port by editing:
# main_server.py: app.run(..., port=5001)
# frontend/.env: REACT_APP_API_URL=http://localhost:5001/api
```

### "ModuleNotFoundError: No module named 'xxx'"

**Solution:**

```bash
pip install -r requirements.txt --upgrade

# Or install specific module:
pip install flask websockets pymoo
```

---

## 📈 Performance Tips

### Faster Simulation

```python
# In config.py
NSGA_GENS = 50           # Reduce from 200
NUM_VEHICLES = 25        # Reduce from 50
```

### Smoother Dashboard

- Close other browser tabs (save RAM)
- Use Chrome (fastest)
- Disable extensions

### Lower CPU Usage

```python
# In config.py
SIMULATION_TIME = 300    # 5 minutes instead of 15
```

---

## 📱 Access from Other Devices

### Same Network

1. **Get your computer's IP:**

```bash
# Windows:
ipconfig

# macOS/Linux:
ifconfig
```

2. **Update frontend/.env:**

```env
REACT_APP_API_URL=http://YOUR_IP:5000/api
REACT_APP_WS_URL=ws://YOUR_IP:8765
```

3. **Visit on phone/tablet:**

```
http://YOUR_IP:3000
```

---

## Production Deployment

### Docker (Recommended)

```bash
# Build container
docker-compose up

# Opens on http://localhost:3000
```

### Cloud Deployment

**Heroku (Backend)**

```bash
heroku login
heroku create smart-city-backend
git push heroku main
```

**Vercel (Frontend)**

```bash
npm install -g vercel
cd frontend
vercel
```

---

## ✅ Verification Checklist

- [ ] `pip install -r requirements.txt` completed
- [ ] `cd frontend && npm install` completed
- [ ] `python main_server.py proposed` running in Terminal 1
- [ ] `npm start` running in Terminal 2
- [ ] Browser opened to http://localhost:3000
- [ ] Dashboard displays metrics
- [ ] WebSocket connected (console shows no errors)
- [ ] Success rate updating in real-time
- [ ] Device load bars showing activity
- [ ] System type can be changed

**All checked? ✅ You're ready to go!**

---

## 📚 Next Steps

1. **Understand the system** - Read [explanation.md](explanation.md)
2. **Explore modules** - See module-specific README.md files
3. **Modify for research** - Adjust config.py and run experiments
4. **Export results** - Click "Export" button to download CSV

---

## 💡 Tips for Researchers

### Create Multiple Experiments

```bash
# Experiment 1: Baseline 1
python main_server.py baseline1 > exp1.log

# Experiment 2: Proposed
python main_server.py proposed > exp2.log

# Experiment 3: Custom config
# Edit config.py, then run:
python main_server.py proposed > exp3.log
```

### Collect Results

Dashboard provides CSV export with all metrics:

- Timestamp
- Success rates
- Latencies
- Device loads
- etc.

### Generate Plots

Use `results/plots.py`:

```python
from results.plots import plot_all, plot_comparison
plot_all()  # Generates matplotlib figures
plot_comparison()  # Baseline comparison
```

---

## 🆘 Still Having Issues?

1. **Check logs** - Look at Terminal 1 output for errors
2. **Browser console** - F12 → Console tab
3. **Review docs** - Check feature-specific README.md files
4. **Restart everything** - Kill terminals, restart all services
5. **Clean rebuild** - Delete node_modules/, pip cache, restart

---

**🎉 Congratulations! Your Smart City Dashboard is running!**

Now watch as the system learns and adapts to reach >85% deadline success rate in real-time!

📊 Check back on the dashboard over the next few minutes to see the improvement.
