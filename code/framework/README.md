# PCNME (Predictive Cloud-Native Mobile Edge)

This folder contains a clean, framework-agnostic implementation of **PCNME**.

## Requirements

- Python **3.11+**
- Redis (required for the runtime server)

## Quick start (Phase 1: offline pretrain)

```bash
cd Freamwork
python -m venv .venv
./.venv/Scripts/activate

pip install -e .

# Run offline optimizer pretrain (synthetic batches)
pcnme pretrain --batches 10 --batch-size 100 --out results/

# Or use the built-in Istanbul topology stub
pcnme validate --config case_studies/istanbul/config.yaml
pcnme pretrain --case-study istanbul --batches 10 --batch-size 100 --out results/
```

## Training (Phase 2/3: Behavior Cloning)

```bash
# Agent1 (placement) from offline optimizer labels
pcnme train-agent1 --case-study istanbul --batches 10 --batch-size 100 --epochs 3 --out results/

# Agent2 (SDN routing) from a deterministic routing heuristic
pcnme train-agent2 --samples 5000 --epochs 3 --out results/
```

## Runtime server (Phase 5)

```bash
# Start Redis first (example)
# docker run -p 6379:6379 redis:7

pcnme serve --case-study istanbul

# Health
curl http://127.0.0.1:8080/api/health

# Start/stop simulation
curl -X POST http://127.0.0.1:8080/api/sim/start
curl -X POST http://127.0.0.1:8080/api/sim/stop
```

Runtime policy notes:

- If `results/agent1.pt` and/or `results/agent2.pt` exist and PyTorch is installed, the simulation loop will use them for placement/routing decisions.
- Otherwise it falls back to a simple heuristic (boulders → cloud, pebbles → least-loaded fog; routing action 0).

## Dashboard (Phase 6)

```bash
cd Freamwork/frontend
npm install
npm run dev
```

Notes:

- By default, the dev server proxies `/api/*` and `/ws/*` to `http://127.0.0.1:8080`.
- For a production build pointing to a different runtime host, build with `VITE_API_BASE`:
    - PowerShell: `$env:VITE_API_BASE="http://127.0.0.1:8080"; npm run build`
    - Bash: `VITE_API_BASE=http://127.0.0.1:8080 npm run build`

## Notes

- The original prototype lives in `implementation/` and is not the reference for this framework.
- This framework is designed to be **topology-agnostic**: all city/case-study specifics live outside the `pcnme/` core.
