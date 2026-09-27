# QUICK START - UNIFIED SYSTEM

## What Changed?

✅ **ONE unified entry point:** `app.py` - No more main.py + main_server.py confusion!

✅ **Automatic pre-training:** Starts when you run the app

✅ **Automatic server launch:** WebSocket + REST API + SimPy all coordinated

✅ **Real-time dashboard:** React UI with live metrics

✅ **Retrain button:** Improve AI based on new simulation data

✅ **City visualization:** See Istanbul network with vehicles and fog nodes

---

## 🎯 RUN IT NOW - 3 STEPS

### Option A: Windows Batch File (Easiest)

```bash
# Double-click:
START.bat
```

### Option B: Manual (Works on Mac/Linux/Windows)

**Terminal 1 - Backend (pre-training + servers):**

```bash
cd c:\Users\imadb\OneDrive\Bureau\dslab2\implementation
python app.py proposed
```

Wait for output:

```
 API Server:       http://localhost:5000
🔌 WebSocket:        ws://localhost:8765
💻 Dashboard:        http://localhost:3000
```

**Terminal 2 - Frontend (React):**

```bash
cd frontend
npm install  # (first time only)
npm start
```

Dashboard opens automatically at **http://localhost:3000** ✨

---

## 📊 What Happens When Running

### Phase 1: Pre-Training (1-2 minutes)

- Generates 50 NSGA-II optimization batches
- Uses real data:
    - CARLA trajectories
    - YOLOv5 benchmarks
    - CRAWDAD network traces
- Trains Agent 1 (DQN for task placement)
- Saves trained agents to `results/checkpoints/`

### Phase 2: Server Startup (instant)

- WebSocket server starts (ws://127.0.0.1:8765)
- Flask REST API starts (http://127.0.0.1:5000)
- SimPy simulation begins in background
- Real-time metrics sent every 1 second

### Phase 3: Dashboard (live)

- React UI shows:
    - Success rate (target: 85%+)
    - Latency trend
    - Device utilization
    - Network congestion
    - Agent performance
    - **Istanbul city map** with vehicles
    - **Retrain button** for continuous learning

---

## 🎮 Using the Dashboard

### Real-Time Monitoring

- **Success Rate**: Target 85%+ (watch it improve!)
- **Latency**: Should decrease as system learns
- **Device Load**: Balanced across Fog 1-4 and Cloud
- **Agent Latency**: Decision time per agent

### System Controls

- **Select System Type**: baseline1 → baseline2 → baseline3 → proposed (best)
- **Start/Stop/Reset**: Control simulation
- **Progress Bar**: Shows % complete and time elapsed

### Retrain AI

1. Let simulation run for a while (150+ tasks)
2. Click **🔄 Retrain AI** button
3. Watch orange indicator pulse (retraining running)
4. Performance should improve on next tasks!

### Istanbul City Map

- 🔴 Red = Fog Nodes (4 edge servers)
- 🔵 Blue = Cloud Server (central)
- 🟡 Yellow = Active Vehicles (50)
- Lines = Network connections

---

## 📈 Expected Performance

### Baseline 1 (NSGA-II only)

- Success Rate: 47%
- Avg Latency: 167ms

### Baseline 2 (TOF + NSGA-II)

- Success Rate: 68%
- Avg Latency: 205ms

### Baseline 3 (TOF + MMDE)

- Success Rate: 80%
- Avg Latency: 163ms

### Proposed (Full DQN system)

- Success Rate: **>85%** ✨
- Avg Latency: **150ms**
- Improves more with retrain! ↗️

---

## 🔧 Troubleshooting

### "Port 5000 already in use"

```bash
# Find and kill process using port 5000
lsof -i :5000              # Mac/Linux
Get-Process -Name python   # Windows
```

### "WebSocket connection failed"

- Make sure backend terminal shows "WebSocket: ws://127.0.0.1:8765"
- Wait 10 seconds for servers to fully start
- Refresh browser page

### "npm: command not found"

- Install Node.js from https://nodejs.org/
- Or: `brew install node` (Mac)

### Pre-training takes too long

- It's normal! Uses real data (50 NSGA-II batches)
- Wait 1-2 minutes
- Then enjoy real-time dashboard!

---

## 📁 What Each File Does

| File             | Purpose                                               |
| ---------------- | ----------------------------------------------------- |
| **app.py**       | ⭐ NEW - Unified entry point (pre-training + servers) |
| **START.bat**    | Windows shortcut to run everything                    |
| **frontend/**    | React dashboard (npm start)                           |
| **agents/**      | DQN neural networks                                   |
| **simulation/**  | SimPy engine                                          |
| **environment/** | Vehicles, fog, cloud, tasks                           |
| **broker/**      | TOF task classification                               |
| **results/**     | Metrics and checkpoints                               |

---

## 💡 Next Steps (Optional)

### Want to customize?

Edit `config.py` to change:

- Number of vehicles
- Simulation duration
- Fog/Cloud MIPS
- Task frequency

### Want to deploy?

See `frontend/README.md` for deployment to Vercel/Netlify

### Want to export results?

Click "Export Results" or check `results/` folder for CSV files

---

## 🎓 Understanding the System

- **Proposed System** = Most advanced (agents constantly learning)
- **Baselines** = Reference implementations (no learning)
- **Success Rate** = % of tasks meeting deadline
- **Latency** = Time from task generation to completion
- **Handoff** = Vehicle moving between fog coverage areas

---

**That's it!** Run `app.py` (or START.bat) and watch your system learn in real-time!

Questions? Check `explanation.md` for technical details.
