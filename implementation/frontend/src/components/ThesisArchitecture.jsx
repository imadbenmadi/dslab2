import React from "react";

const sections = [
    {
        title: "1) Application Scenario - Istanbul Smart Cars",
        body: "Fleet of connected vehicles (50-100), 10 FPS camera pipelines, 200ms safety deadline, multi-district topology mapped to four fog zones: Besiktas, Sisli, Kadikoy, Uskudar.",
    },
    {
        title: "2) DAG Pipeline (5 Steps)",
        body: "Step 1 capture/compress on-device; Steps 2,3,5 as pebbles; Step 4 as boulder sent to cloud. This enables partial offloading with per-step destination decisions.",
    },
    {
        title: "3) Three-Tier Architecture",
        body: "IoT vehicles produce DAG + spatial tags; Fog layer executes TOF broker, Aggregator, Agent1, Trajectory Predictor, NTB/HTB; Cloud executes boulders/supertasks and analytics.",
    },
    {
        title: "4) Network Control Plane",
        body: "SDN data plane remains rule-driven; Agent2 + SDN Controller proactively preinstall OpenFlow paths to reduce reactive overhead and packet loss.",
    },
    {
        title: "5) Offline + Online Intelligence",
        body: "TOF-MMDE-NSGA-II offline produces Pareto expert labels; behavioral cloning warm-starts Agent1/Agent2; live reinforcement updates continue online.",
    },
    {
        title: "6) Mobility and Proactive Handoff",
        body: "Spatial tag gives location/speed/heading. Predictor computes T_exit and compares to T_exec per DAG step. Modes: direct, proactive pre-spin, HTB reactive fallback.",
    },
    {
        title: "7) Cloud-Native Data Architecture",
        body: "Redis stores live dashboard state and recent feeds. Timescale/PostgreSQL stores long-term metrics, task events, and runtime logs with time and vehicle indexes.",
    },
];

const formulas = [
    {
        name: "Execution Cost",
        value: "EC = task_MI / fog_MIPS",
    },
    {
        name: "Mobility Exit Time",
        value: "T_exit = (R_fog - dist(car, fog_center)) / v_closing",
    },
    {
        name: "Agent1 Reward",
        value: "R = -0.5*latency - 0.3*energy - 0.2*deadline_violation",
    },
    {
        name: "Agent2 Reward",
        value: "R = +0.5*delivery - 0.3*delay - 0.2*ctrl_overhead",
    },
];

const stack = [
    ["IoT", "Vehicle edge daemon, camera DAG generation, spatial tag"],
    [
        "Fog/App",
        "TOF Broker, Aggregator, Agent1, Trajectory Predictor, NTB/HTB",
    ],
    ["Fog/Network", "Agent2, SDN Controller, OpenFlow pre-installation"],
    ["Cloud", "Boulder execution, super-task handling, analytics APIs"],
    ["Data", "Redis live state, Timescale/PostgreSQL historical storage"],
    ["UI", "Dashboard, Agents observability, Logic explorer, Thesis v2 view"],
];

const ThesisArchitecture = () => {
    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-950 via-zinc-900 to-gray-950 text-white">
            <header className="border-b border-gray-700 bg-black/35 backdrop-blur">
                <div className="max-w-7xl mx-auto px-6 py-8 flex flex-wrap items-center justify-between gap-4">
                    <div>
                        <h1 className="text-3xl font-bold">
                            Thesis Architecture Proposal v2
                        </h1>
                        <p className="text-gray-400 mt-1">
                            Predictive Cloud-Native Mobile Edge Optimized Task
                            Offloading for Smart City Vehicular IoT Networks
                        </p>
                        <p className="text-gray-500 text-sm mt-1">
                            Application domain: Autonomous & Connected Vehicles
                            in Istanbul urban network
                        </p>
                    </div>
                    <div className="flex gap-2">
                        <a
                            href="/"
                            className="px-4 py-2 rounded bg-blue-700 hover:bg-blue-600 text-sm font-medium"
                        >
                            Main Dashboard
                        </a>
                        <a
                            href="/logic"
                            className="px-4 py-2 rounded bg-cyan-700 hover:bg-cyan-600 text-sm font-medium"
                        >
                            Logic Explorer
                        </a>
                    </div>
                </div>
            </header>

            <main className="max-w-7xl mx-auto px-6 py-8 space-y-6">
                <section className="bg-gray-800/60 border border-gray-700 rounded-xl p-5">
                    <h2 className="text-lg font-semibold mb-3">
                        Architecture Summary
                    </h2>
                    <p className="text-gray-300 leading-7">
                        The system runs a proactive 3-tier IoT-Fog-Cloud
                        pipeline for object-detection DAG workloads. TOF broker
                        splits boulders and pebbles, NSGA-II/MMDE provides
                        offline expert supervision, Agent1 optimizes compute
                        placement, Agent2 optimizes SDN routing, and
                        mobility-aware handoff logic protects deadline
                        feasibility under high-speed urban movement.
                    </p>
                </section>

                <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {sections.map((s) => (
                        <article
                            key={s.title}
                            className="bg-gray-800/60 border border-gray-700 rounded-xl p-5"
                        >
                            <h3 className="text-base font-semibold text-fuchsia-300">
                                {s.title}
                            </h3>
                            <p className="text-sm text-gray-300 mt-2 leading-6">
                                {s.body}
                            </p>
                        </article>
                    ))}
                </section>

                <section className="bg-gray-800/60 border border-gray-700 rounded-xl p-5">
                    <h2 className="text-lg font-semibold mb-4">
                        Core Equations
                    </h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {formulas.map((f) => (
                            <div
                                key={f.name}
                                className="bg-gray-900/70 border border-gray-700 rounded p-3"
                            >
                                <p className="text-xs text-gray-400">
                                    {f.name}
                                </p>
                                <p className="font-mono text-sm mt-1 text-emerald-300">
                                    {f.value}
                                </p>
                            </div>
                        ))}
                    </div>
                </section>

                <section className="bg-gray-800/60 border border-gray-700 rounded-xl p-5">
                    <h2 className="text-lg font-semibold mb-4">
                        Runtime Stack Mapping (Implementation)
                    </h2>
                    <div className="overflow-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="border-b border-gray-700 text-gray-400">
                                    <th className="text-left py-2">Layer</th>
                                    <th className="text-left py-2">
                                        What It Does
                                    </th>
                                </tr>
                            </thead>
                            <tbody>
                                {stack.map((r) => (
                                    <tr
                                        key={r[0]}
                                        className="border-b border-gray-800"
                                    >
                                        <td className="py-2 font-medium">
                                            {r[0]}
                                        </td>
                                        <td className="py-2 text-gray-300">
                                            {r[1]}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </section>

                <section className="bg-gray-800/60 border border-gray-700 rounded-xl p-5">
                    <h2 className="text-lg font-semibold mb-3">
                        Evaluation Design
                    </h2>
                    <p className="text-sm text-gray-300 leading-6">
                        Baselines include plain NSGA-II, TOF+NSGA-II, and
                        TOF+MMDE-NSGA-II without online RL. The proposed full
                        system adds both DQN agents and proactive
                        mobility/network control. Core metrics: latency,
                        deadline feasibility, energy, handoff success, SDN
                        pre-install hit-rate, and load balance across fog nodes.
                    </p>
                </section>
            </main>
        </div>
    );
};

export default ThesisArchitecture;
