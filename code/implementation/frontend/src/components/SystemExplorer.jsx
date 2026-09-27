import React, { useEffect } from "react";
import useSystemStore from "../store/systemStore";
import { useWebSocket } from "../hooks/useWebSocket";

const stageRows = [
    [
        "Vehicle/IoT",
        "Capture + tiny local steps + TOF-lite",
        "Local execution threshold, on-car preclassification, buffer health",
    ],
    [
        "Fog Broker",
        "Authoritative Pebble/Boulder split",
        "EC threshold decision, ingress zone, policy sync",
    ],
    [
        "Agent 1",
        "Placement policy",
        "Fog destination for pebbles, cloud fallback control",
    ],
    [
        "MMDE-NSGA-II",
        "Offline supervision",
        "Pareto/knee expert labels for behavioral cloning",
    ],
    [
        "Agent 2",
        "SDN routing policy",
        "Primary/alternate/VIP/best-effort path actions with reward shaping",
    ],
    [
        "SDN Controller",
        "Policy-based route execution",
        "Preinstalled hits, reactive overhead, packet drops, relay delays",
    ],
    [
        "Fog/Cloud",
        "Execution + relay tier",
        "Device->Fog, Fog->Cloud, Fog->Fog mobility handoff, HTB lifecycle",
    ],
    [
        "Message Bus",
        "Contract events",
        "At-least-once publish, dedup, store-and-forward, circuit breaker",
    ],
    [
        "Realtime Stream",
        "UI telemetry",
        "WebSocket + API history + structured logs + evaluation summary",
    ],
];

const KV = ({ label, value }) => (
    <div className="bg-gray-900/60 border border-gray-700 rounded p-3">
        <p className="text-xs text-gray-400">{label}</p>
        <p className="text-sm font-mono mt-1">{value ?? "--"}</p>
    </div>
);

const SystemExplorer = () => {
    const {
        metrics,
        logicSnapshot,
        recentTasks,
        recentLogs,
        evaluationSummary,
        fetchLogicSnapshot,
        fetchRecentTasks,
        fetchRecentLogs,
        fetchEvaluationSummary,
        fetchStorageHealth,
        fetchAnalyticsWindow,
        fetchVehicleAnalytics,
        analyticsWindow,
        vehicleAnalytics,
        storageHealth,
        selectedWindow,
        selectedVehicle,
        setSelectedWindow,
        setSelectedVehicle,
    } = useSystemStore();

    useWebSocket();

    useEffect(() => {
        fetchLogicSnapshot();
        fetchRecentTasks();
        fetchRecentLogs();
        fetchEvaluationSummary();
        fetchStorageHealth();
        fetchAnalyticsWindow("1h");
        fetchVehicleAnalytics("V000", "24h");

        const a = setInterval(fetchLogicSnapshot, 1500);
        const b = setInterval(fetchRecentTasks, 1800);
        const c = setInterval(fetchRecentLogs, 2000);
        const d = setInterval(fetchEvaluationSummary, 3500);
        const e = setInterval(fetchStorageHealth, 3000);
        return () => {
            clearInterval(a);
            clearInterval(b);
            clearInterval(c);
            clearInterval(d);
            clearInterval(e);
        };
    }, [
        fetchLogicSnapshot,
        fetchRecentTasks,
        fetchRecentLogs,
        fetchEvaluationSummary,
        fetchStorageHealth,
        fetchAnalyticsWindow,
        fetchVehicleAnalytics,
    ]);

    const logic = logicSnapshot?.logic || {};
    const agent = logicSnapshot?.agent || {};

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-950 via-gray-900 to-black text-white">
            <header className="border-b border-gray-700 bg-black/35 backdrop-blur">
                <div className="max-w-7xl mx-auto px-6 py-8 flex flex-wrap items-center justify-between gap-4">
                    <div>
                        <h1 className="text-3xl font-bold">
                            Full System Logic Explorer
                        </h1>
                        <p className="text-gray-400 mt-1">
                            Pipeline, agents, task generation, NSGA supervision,
                            runtime logs, and results in one page.
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
                            href="/agents"
                            className="px-4 py-2 rounded bg-emerald-700 hover:bg-emerald-600 text-sm font-medium"
                        >
                            Agents Page
                        </a>
                        <a
                            href="/thesis"
                            className="px-4 py-2 rounded bg-fuchsia-700 hover:bg-fuchsia-600 text-sm font-medium"
                        >
                            Thesis v2 Page
                        </a>
                    </div>
                </div>
            </header>

            <main className="max-w-7xl mx-auto px-6 py-8 space-y-6">
                <section className="bg-gray-800/60 border border-gray-700 rounded-xl p-5">
                    <h2 className="text-lg font-semibold mb-4">
                        End-to-End Pipeline
                    </h2>
                    <div className="overflow-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="border-b border-gray-700 text-gray-400">
                                    <th className="text-left py-2">Stage</th>
                                    <th className="text-left py-2">Logic</th>
                                    <th className="text-left py-2">
                                        What to Monitor
                                    </th>
                                </tr>
                            </thead>
                            <tbody>
                                {stageRows.map((r) => (
                                    <tr
                                        key={r[0]}
                                        className="border-b border-gray-800"
                                    >
                                        <td className="py-2 font-medium">
                                            {r[0]}
                                        </td>
                                        <td className="py-2">{r[1]}</td>
                                        <td className="py-2 text-gray-300">
                                            {r[2]}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </section>

                <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
                    <KV label="System Type" value={logic.systemType} />
                    <KV label="Running" value={String(logic.running)} />
                    <KV
                        label="Simulation Time"
                        value={`${logic.simulationTime ?? 0}s`}
                    />
                    <KV label="Tasks Total" value={logic.tasksTotal} />
                    <KV
                        label="Deadline Rate"
                        value={`${(logic.deadlineRate ?? 0).toFixed(2)}%`}
                    />
                    <KV
                        label="Avg Latency"
                        value={`${(logic.avgLatencyMs ?? 0).toFixed(2)} ms`}
                    />
                    <KV
                        label="Avg Energy"
                        value={`${(logic.avgEnergyJ ?? 0).toFixed(4)} J`}
                    />
                    <KV label="Offloads Active" value={logic.offloadsActive} />
                    <KV label="Local Exec" value={logic.localExec} />
                    <KV label="Fog Exec" value={logic.fogExec} />
                    <KV label="Cloud Exec" value={logic.cloudExec} />
                    <KV label="Super Tasks" value={logic.superTasks} />
                    <KV label="Handoffs" value={logic.handoffs} />
                    <KV label="Task Migrations" value={logic.taskMigrations} />
                    <KV label="SDN Reactive" value={logic.sdnReactive} />
                    <KV
                        label="SDN Preinstall Hits"
                        value={logic.sdnPreinstallHits}
                    />
                    <KV label="SDN Packet Drops" value={logic.sdnPacketDrops} />
                    <KV
                        label="Relay D->F Avg"
                        value={`${(logic.relayDeviceToFogMs || 0).toFixed(2)} ms`}
                    />
                    <KV
                        label="Relay F->C Avg"
                        value={`${(logic.relayFogToCloudMs || 0).toFixed(2)} ms`}
                    />
                    <KV label="Bus Published" value={logic.busPublished} />
                    <KV
                        label="Bus Dedup Dropped"
                        value={logic.busDedupDropped}
                    />
                    <KV label="Vehicle Buffer" value={logic.vehicleBuffer} />
                    <KV label="Fog Buffer" value={logic.fogBuffer} />
                    <KV
                        label="Agent1 Avg Reward"
                        value={agent.agent1?.avgReward?.toFixed(4)}
                    />
                    <KV
                        label="Agent2 Avg Reward"
                        value={agent.agent2?.avgReward?.toFixed(4)}
                    />
                </section>

                <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    <div className="bg-gray-800/60 border border-gray-700 rounded-xl p-5">
                        <h2 className="text-lg font-semibold mb-4">
                            Storage Health
                        </h2>
                        <div className="space-y-2 text-sm">
                            <KV
                                label="Redis Enabled"
                                value={String(storageHealth?.redisEnabled)}
                            />
                            <KV
                                label="Redis Connected"
                                value={String(storageHealth?.redisConnected)}
                            />
                            <KV
                                label="Postgres Enabled"
                                value={String(storageHealth?.postgresEnabled)}
                            />
                            <KV
                                label="Postgres Connected"
                                value={String(storageHealth?.postgresConnected)}
                            />
                            <KV
                                label="Batch Writer"
                                value={String(
                                    storageHealth?.batchWriterEnabled,
                                )}
                            />
                            <KV
                                label="Queue Size"
                                value={storageHealth?.queueSize}
                            />
                        </div>
                    </div>

                    <div className="bg-gray-800/60 border border-gray-700 rounded-xl p-5">
                        <h2 className="text-lg font-semibold mb-4">
                            Historical Window Analytics
                        </h2>
                        <div className="flex gap-2 mb-3">
                            {["1h", "24h"].map((w) => (
                                <button
                                    key={w}
                                    onClick={() => {
                                        setSelectedWindow(w);
                                        fetchAnalyticsWindow(w);
                                    }}
                                    className={`px-3 py-1 rounded text-sm ${selectedWindow === w ? "bg-cyan-600" : "bg-gray-700 hover:bg-gray-600"}`}
                                >
                                    {w}
                                </button>
                            ))}
                        </div>
                        <div className="space-y-2 text-sm">
                            <KV label="Tasks" value={analyticsWindow?.tasks} />
                            <KV
                                label="Avg Latency (ms)"
                                value={analyticsWindow?.avgLatencyMs?.toFixed?.(
                                    3,
                                )}
                            />
                            <KV
                                label="Avg Energy (J)"
                                value={analyticsWindow?.avgEnergyJ?.toFixed?.(
                                    4,
                                )}
                            />
                            <KV
                                label="Cloud Exec"
                                value={analyticsWindow?.cloudExec}
                            />
                            <KV
                                label="Fog Exec"
                                value={analyticsWindow?.fogExec}
                            />
                            <KV
                                label="Unique Vehicles"
                                value={analyticsWindow?.uniqueVehicles}
                            />
                        </div>
                    </div>

                    <div className="bg-gray-800/60 border border-gray-700 rounded-xl p-5">
                        <h2 className="text-lg font-semibold mb-4">
                            Vehicle Analytics
                        </h2>
                        <div className="flex gap-2 mb-3">
                            <input
                                className="bg-gray-900 border border-gray-700 rounded px-2 py-1 text-sm font-mono"
                                value={selectedVehicle || ""}
                                onChange={(e) =>
                                    setSelectedVehicle(e.target.value)
                                }
                                placeholder="V000"
                            />
                            <button
                                onClick={() =>
                                    fetchVehicleAnalytics(
                                        selectedVehicle || "V000",
                                        selectedWindow || "24h",
                                    )
                                }
                                className="px-3 py-1 rounded text-sm bg-emerald-600 hover:bg-emerald-500"
                            >
                                Query
                            </button>
                        </div>
                        <div className="space-y-2 text-sm">
                            <KV
                                label="Vehicle"
                                value={vehicleAnalytics?.summary?.vehicleId}
                            />
                            <KV
                                label="Window"
                                value={`${vehicleAnalytics?.summary?.hours || "--"}h`}
                            />
                            <KV
                                label="Tasks"
                                value={vehicleAnalytics?.summary?.tasks}
                            />
                            <KV
                                label="Avg Latency (ms)"
                                value={vehicleAnalytics?.summary?.avgLatencyMs?.toFixed?.(
                                    3,
                                )}
                            />
                            <KV
                                label="Avg Energy (J)"
                                value={vehicleAnalytics?.summary?.avgEnergyJ?.toFixed?.(
                                    4,
                                )}
                            />
                        </div>
                    </div>
                </section>

                {evaluationSummary && (
                    <section className="bg-gray-800/60 border border-gray-700 rounded-xl p-5">
                        <h2 className="text-lg font-semibold mb-4">
                            Evaluation Statistics (Windowed)
                        </h2>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
                            <KV
                                label="Latency Mean (95% CI)"
                                value={`${evaluationSummary.latency?.mean?.toFixed(2)} [${evaluationSummary.latency?.ci95Low?.toFixed(2)}, ${evaluationSummary.latency?.ci95High?.toFixed(2)}]`}
                            />
                            <KV
                                label="Success Mean (95% CI)"
                                value={`${evaluationSummary.successRate?.mean?.toFixed(2)} [${evaluationSummary.successRate?.ci95Low?.toFixed(2)}, ${evaluationSummary.successRate?.ci95High?.toFixed(2)}]`}
                            />
                            <KV
                                label="Throughput Mean (95% CI)"
                                value={`${evaluationSummary.throughput?.mean?.toFixed(2)} [${evaluationSummary.throughput?.ci95Low?.toFixed(2)}, ${evaluationSummary.throughput?.ci95High?.toFixed(2)}]`}
                            />
                        </div>
                    </section>
                )}

                <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <div className="bg-gray-800/60 border border-gray-700 rounded-xl p-5">
                        <h2 className="text-lg font-semibold mb-4">
                            Generated Tasks and Offloads
                        </h2>
                        <div className="max-h-96 overflow-auto">
                            <table className="w-full text-xs">
                                <thead>
                                    <tr className="text-gray-400 border-b border-gray-700">
                                        <th className="text-left py-2">Task</th>
                                        <th className="text-left py-2">
                                            Vehicle
                                        </th>
                                        <th className="text-left py-2">
                                            Class
                                        </th>
                                        <th className="text-left py-2">Dest</th>
                                        <th className="text-right py-2">
                                            Latency
                                        </th>
                                        <th className="text-right py-2">
                                            Energy
                                        </th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {(recentTasks || [])
                                        .slice(-120)
                                        .reverse()
                                        .map((t) => (
                                            <tr
                                                key={t.taskId}
                                                className="border-b border-gray-800"
                                            >
                                                <td className="py-1 font-mono">
                                                    {t.taskId}
                                                </td>
                                                <td className="py-1">
                                                    {t.vehicleId}
                                                </td>
                                                <td className="py-1">
                                                    {t.class}
                                                </td>
                                                <td className="py-1">
                                                    {t.destination}
                                                </td>
                                                <td className="py-1 text-right font-mono">
                                                    {t.latencyMs}
                                                </td>
                                                <td className="py-1 text-right font-mono">
                                                    {t.energyJ}
                                                </td>
                                            </tr>
                                        ))}
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <div className="bg-gray-800/60 border border-gray-700 rounded-xl p-5">
                        <h2 className="text-lg font-semibold mb-4">
                            Professional Runtime Logs
                        </h2>
                        <div className="max-h-96 overflow-auto">
                            <table className="w-full text-xs">
                                <thead>
                                    <tr className="text-gray-400 border-b border-gray-700">
                                        <th className="text-left py-2">Time</th>
                                        <th className="text-left py-2">
                                            Event
                                        </th>
                                        <th className="text-left py-2">Data</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {(recentLogs || [])
                                        .slice(-140)
                                        .reverse()
                                        .map((l, idx) => (
                                            <tr
                                                key={`${l.timestamp}-${idx}`}
                                                className="border-b border-gray-800 align-top"
                                            >
                                                <td className="py-1 font-mono">
                                                    {l.timestamp}
                                                </td>
                                                <td className="py-1">
                                                    {l.event}
                                                </td>
                                                <td className="py-1 font-mono text-gray-300">
                                                    {Object.entries(l)
                                                        .filter(
                                                            ([k]) =>
                                                                ![
                                                                    "timestamp",
                                                                    "event",
                                                                ].includes(k),
                                                        )
                                                        .map(
                                                            ([k, v]) =>
                                                                `${k}=${String(v)}`,
                                                        )
                                                        .join(" | ")}
                                                </td>
                                            </tr>
                                        ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </section>

                <section className="bg-gray-800/60 border border-gray-700 rounded-xl p-5">
                    <h2 className="text-lg font-semibold mb-3">
                        Latest Metrics Frame
                    </h2>
                    <pre className="text-xs bg-gray-950 border border-gray-700 rounded p-3 overflow-auto max-h-72">
                        {JSON.stringify(metrics || {}, null, 2)}
                    </pre>
                </section>
            </main>
        </div>
    );
};

export default SystemExplorer;
