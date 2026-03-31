# Documentation Index

Welcome to the Smart City Vehicular Task Offloading System documentation.

## 📚 Quick Navigation

### Getting Started

- **[SETUP.md](./deployment/SETUP.md)** - Install and configure the system
- **[QUICKSTART.md](./guides/QUICKSTART.md)** - Run your first simulation in 5 minutes
- **[TROUBLESHOOTING.md](./guides/TROUBLESHOOTING.md)** - Common issues and solutions

### Understanding the System

- **[ARCHITECTURE.md](./architecture/ARCHITECTURE.md)** - System design and components
- **[BASELINES.md](./architecture/BASELINES.md)** - Comparison algorithms explained
- **[FOG_HANDOFF.md](./guides/FOG_HANDOFF.md)** - Fog-to-Fog task transfer mechanism

### Advanced Topics

- **[DEPLOYMENT.md](./deployment/DEPLOYMENT.md)** - Production deployment
- **[API_REFERENCE.md](./architecture/API_REFERENCE.md)** - REST API endpoints
- **[DATABASE.md](./deployment/DATABASE.md)** - PostgreSQL/Redis setup

### Configuration

- **[CONFIG.md](./deployment/CONFIG.md)** - Environment variables and tuning

---

## 🎯 Common Tasks

| Task                    | Document                                          |
| ----------------------- | ------------------------------------------------- |
| First time setup        | [SETUP.md](./deployment/SETUP.md)                 |
| Run a 5-minute demo     | [QUICKSTART.md](./guides/QUICKSTART.md)           |
| Compare baselines       | [BASELINES.md](./architecture/BASELINES.md)       |
| Understand architecture | [ARCHITECTURE.md](./architecture/ARCHITECTURE.md) |
| Fix an issue            | [TROUBLESHOOTING.md](./guides/TROUBLESHOOTING.md) |
| Deploy to production    | [DEPLOYMENT.md](./deployment/DEPLOYMENT.md)       |
| Configure system        | [CONFIG.md](./deployment/CONFIG.md)               |

---

## 📁 Documentation Structure

```
docs/
├── INDEX.md (this file)
├── architecture/          (System design & concepts)
│   ├── ARCHITECTURE.md
│   ├── BASELINES.md
│   └── API_REFERENCE.md
├── guides/               (How-to guides & tutorials)
│   ├── QUICKSTART.md
│   ├── FOG_HANDOFF.md
│   └── TROUBLESHOOTING.md
└── deployment/           (Setup & operations)
    ├── SETUP.md
    ├── DEPLOYMENT.md
    ├── DATABASE.md
    └── CONFIG.md
```

---

## 🚀 Quick Start (30 seconds)

```bash
# 1. Setup PostgreSQL
python setup_postgresql.py

# 2. Run verification
python complete_system_setup.py

# 3. Terminal 1: Backend
python app.py proposed

# 4. Terminal 2: Frontend
cd frontend && npm start

# 5. Open browser
http://localhost:3000
```

For detailed walkthrough, see [QUICKSTART.md](./guides/QUICKSTART.md)

---

## 📊 System Overview

**Smart City Task Offloading** is a simulation platform for IoT-Fog-Cloud computing:

- **50 vehicles** with task generation (10 Hz)
- **4 fog nodes** (edge servers) with 2000 MIPS each
- **1 cloud** with 8000 MIPS
- **Optimization**: TOF classification + MMDE-NSGA-II
- **Learning**: DQN agents for task placement & routing
- **Real-time**: React dashboard with Leaflet.js map
- **Storage**: PostgreSQL (history) + Redis (live state)

---

## 🔑 Key Concepts

### TOF (Task Offloading Framework)

Classifies tasks as:

- **Boulder** (latency-sensitive) → Cloud
- **Pebble** (flexible) → Fog or optimized placement

### MMDE-NSGA-II

Multi-objective optimization balancing:

- Latency reduction
- Energy efficiency
- Deadline compliance

### DQN Agents

- **Agent1**: Task placement (device/fog/cloud)
- **Agent2**: SDN routing optimization

### Fog-to-Fog Handoff

Proactive task migration when vehicles transition between coverage zones.

---

## 📞 Support

- Check [TROUBLESHOOTING.md](./guides/TROUBLESHOOTING.md) first
- Review error logs in `results/logs/`
- Check PostgreSQL with: `psql -U postgres -d smart_city -c "SELECT COUNT(*) FROM metrics_history;"`

---

**Last Updated:** March 31, 2026  
**Version:** 2.0 Distributed Architecture
