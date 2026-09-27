Let me read the implementation file first.Good — now I have the full picture of what you built. Let me write the complete agent prompt.Here is what the prompt contains and why each part is there.

**The existing codebase section** tells the agent exactly what you already built so it does not rewrite things from scratch that already work. It maps to your explanation.md directly — the agent will keep your broker, optimizer, agents, mobility, and SDN abstractions and refactor them into the clean package structure.

**The stack section** locks the agent into FastAPI instead of Flask (async, proper WebSocket support), Vite instead of CRA, and Recharts + Leaflet for the frontend. These are non-negotiable choices that will save days of debugging.

**The real data section** is critical. It points the agent at IETT bus GPS traces and OSMnx for the Istanbul road network. Vehicles will follow actual Istanbul streets. Rush hours and football match traffic spikes are specified with real timing so the mobility patterns are realistic.

**The framework structure** separates `pcnme/` (the installable package) from `case_studies/istanbul/` (the specific scenario). This is what the professor asked for — a framework that works everywhere, not an Istanbul-only script.

**The complete WebSocket schema** means the agent cannot fake metrics. Every field is specified. The dashboard will only accept this exact shape.

**The build order** is the most important part. Six phases, each with a checkpoint that produces observable output. If the agent follows this exactly, you end up with a working system. If it skips ahead, you end up with a beautiful dashboard showing fake numbers.

**The final instruction** is the one thing academic AI-generated code always violates — stubbing out the hard parts. I told the agent explicitly: agents must actually train, NSGA-II must actually run, T_exit must actually be computed from GPS, TimescaleDB must actually store history. Every number will be cited in your thesis — they have to be real.