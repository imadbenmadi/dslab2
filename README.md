# dslab2 — Thesis: Task Offloading in Vehicular Fog Computing (PCNME)

## Layout

```
code/     codebases (see below)
docs/     thesis documents: proposals, methodology, literature review, notes, reports, prompts
papers/   papers under review and reference papers
```

## Code

All codebases live in [code/](code/). They are separate attempts at the same system
(TOF + MMDE-NSGA-II optimisation, DQN agents, SDN, mobility); which one is kept is still open.

| Folder | What it is | Run tests |
|---|---|---|
| [code/pcnme/](code/pcnme/) | Simulation + experiment pipeline (pretrain → run_all → analyze → charts) | `cd code/pcnme && python test_verification.py` |
| [code/framework/](code/framework/) | Installable package: CLI, Redis runtime server, React frontend | `cd code/framework && pytest tests` |
| [code/implementation/](code/implementation/) | Distributed microservices (NATS/MQTT, mTLS, SDN, dashboard) | `cd code/implementation && pytest tests` |
| [code/VFC-Offloading-RL/](code/VFC-Offloading-RL/) | Third-party reference project (RL offloading) | — |
| [code/iFogSim/](code/iFogSim/) | Third-party iFogSim (Java) experiments (git submodule) | — |

## Documents

| Folder | Contents |
|---|---|
| [docs/proposals/](docs/proposals/) | Architecture proposals (v1, v2, PCNME) |
| [docs/methodology/](docs/methodology/) | Methodology (LaTeX + PDF) |
| [docs/literature-review/](docs/literature-review/) | Literature review (LaTeX + PDF) |
| [docs/technical-notes/](docs/technical-notes/) | NSGA-II/MMDE/TOF notes, worked example, DAG/SDN/mobility, equation checks |
| [docs/nsga2/](docs/nsga2/) | NSGA-II explainer pages (HTML) |
| [docs/reports/](docs/reports/) | Weekly and paper reports |
| [docs/prompts/](docs/prompts/) | Build / generation prompts |
| [papers/](papers/) | Papers under review; [papers/references/](papers/references/) holds NSGA-II, DRL and QECO reference papers |
