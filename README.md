# dslab2 — Thesis: Task Offloading in Vehicular Fog Computing (PCNME)

## Code

All codebases live in [code/](code/). They are separate attempts at the same system
(TOF + MMDE-NSGA-II optimisation, DQN agents, SDN, mobility); which one is kept is still open.

| Folder | What it is | Run tests |
|---|---|---|
| [code/pcnme/](code/pcnme/) | Simulation + experiment pipeline (pretrain → run_all → analyze → charts) | `cd code/pcnme && python test_verification.py` |
| [code/framework/](code/framework/) | Installable package: CLI, Redis runtime server, React frontend | `cd code/framework && pytest tests` |
| [code/implementation/](code/implementation/) | Distributed microservices (NATS/MQTT, mTLS, SDN, dashboard) | `cd code/implementation && pytest tests` |
| [code/VFC-Offloading-RL/](code/VFC-Offloading-RL/) | Third-party reference project (RL offloading) | — |
| [iFogSim/](iFogSim/) | Third-party iFogSim (Java) experiments | — |

## Documents

- [docs/](docs/) — architecture, literature review, build prompts
- [methodology/](methodology/) — methodology (LaTeX + PDF)
- [reports/](reports/), [papers/](papers/), [prompt/](prompt/)
- Root `.docx` / `.pdf` files — proposals, technical notes, NSGA-II papers
