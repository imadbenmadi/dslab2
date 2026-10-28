import { useQuery } from "@tanstack/react-query";
import { getJson, postJson } from "./api/client";
import { useStream } from "./hooks/useStream";
import { useStreamStore } from "./state/store";
import type { Envelope, Snapshot } from "./types";
import { MapView } from "./components/MapView";

export function App() {
    useStream();
    const connected = useStreamStore((s) => s.connected);
    const snapshot = useStreamStore((s) => s.snapshot);
    const lastTs = useStreamStore((s) => s.lastTs);
    const setEnvelope = useStreamStore((s) => s.setEnvelope);

    useQuery({
        queryKey: ["state"],
        queryFn: async () => {
            const data = await getJson<Envelope | Snapshot>("/api/state");
            if ((data as any).state) setEnvelope(data as Envelope);
            else {
                // fall back if server returns raw snapshot
                setEnvelope({
                    ts: new Date().toISOString(),
                    state: data as Snapshot,
                });
            }
            return data;
        },
    });

    const metrics = snapshot?.metrics;

    return (
        <div className="min-h-screen bg-slate-50 text-slate-900">
            <div className="mx-auto max-w-6xl px-4 py-6">
                <div className="flex items-center justify-between">
                    <h1 className="text-2xl font-semibold">PCNME Dashboard</h1>
                    <div className="text-sm">
                        <span
                            className={
                                connected ? "text-green-700" : "text-red-700"
                            }
                        >
                            {connected ? "WS connected" : "WS disconnected"}
                        </span>
                        {lastTs ? (
                            <span className="ml-3 text-slate-500">
                                {lastTs}
                            </span>
                        ) : null}
                    </div>
                </div>

                <div className="mt-4 flex gap-2">
                    <button
                        className="rounded bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700"
                        onClick={() => postJson("/api/sim/start")}
                    >
                        Start Simulation
                    </button>
                    <button
                        className="rounded bg-slate-900 px-3 py-2 text-sm font-medium text-white hover:bg-slate-800"
                        onClick={() => postJson("/api/sim/stop")}
                    >
                        Stop Simulation
                    </button>
                </div>

                <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-3">
                    <div className="rounded border bg-white p-4">
                        <div className="text-xs text-slate-500">Tasks</div>
                        <div className="mt-1 text-xl font-semibold">
                            {metrics?.tasks_total ?? 0}
                        </div>
                        <div className="mt-2 text-sm text-slate-700">
                            Fog: {metrics?.tasks_fog ?? 0} | Cloud:{" "}
                            {metrics?.tasks_cloud ?? 0}
                        </div>
                    </div>
                    <div className="rounded border bg-white p-4">
                        <div className="text-xs text-slate-500">
                            Avg Latency
                        </div>
                        <div className="mt-1 text-xl font-semibold">
                            {(metrics?.avg_latency_ms ?? 0).toFixed(1)} ms
                        </div>
                        <div className="mt-2 text-sm text-slate-700">
                            Drops: {metrics?.packet_drops ?? 0}
                        </div>
                    </div>
                    <div className="rounded border bg-white p-4">
                        <div className="text-xs text-slate-500">Avg Energy</div>
                        <div className="mt-1 text-xl font-semibold">
                            {(metrics?.avg_energy ?? 0).toFixed(4)}
                        </div>
                    </div>
                </div>

                <div className="mt-6 rounded border bg-white p-2">
                    {snapshot ? (
                        <MapView snapshot={snapshot} />
                    ) : (
                        <div className="p-6 text-slate-500">
                            Waiting for state…
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
