import React, { useEffect, useMemo } from "react";
import useSystemStore from "../store/systemStore";
import { useWebSocket } from "../hooks/useWebSocket";

const TinyTrend = ({ values = [], color = "bg-emerald-500" }) => {
    if (!values.length) {
        return <div className="text-xs text-gray-500">No history yet</div>;
    }

    const maxAbs = Math.max(1, ...values.map((v) => Math.abs(v)));

    return (
        <div className="flex items-end gap-1 h-14">
            {values.slice(-30).map((v, idx) => {
                const h = Math.max(8, Math.round((Math.abs(v) / maxAbs) * 50));
                return (
                    <div
                        key={`${idx}-${v}`}
                        className={`w-2 rounded-t ${color}`}
                        style={{
                            height: `${h}px`,
                            opacity: v >= 0 ? 0.95 : 0.5,
                        }}
                        title={`${v.toFixed(3)}`}
                    />
                );
            })}
        </div>
    );
};

const AgentCard = ({ name, data, rewardSeries, accent }) => {
    if (!data) {
        return (
            <div className="bg-gray-800/60 border border-gray-700 rounded-xl p-5">
                <h3 className="text-lg font-semibold">{name}</h3>
                <p className="text-sm text-gray-400 mt-2">
                    Waiting for data...
                </p>
            </div>
        );
    }

    return (
        <div className="bg-gray-800/60 border border-gray-700 rounded-xl p-5">
            <h3 className={`text-lg font-semibold ${accent}`}>{name}</h3>
            <div className="grid grid-cols-2 gap-3 mt-4 text-sm">
                <Stat label="Avg reward" value={data.avgReward?.toFixed(3)} />
                <Stat
                    label="Reward rate"
                    value={`${((data.rewardRate || 0) * 100).toFixed(1)}%`}
                />
                <Stat label="Penalties" value={data.penalties || 0} />
                <Stat label="Updates" value={data.updates || 0} />
                <Stat label="Epsilon" value={data.epsilon?.toFixed(3)} />
                <Stat label="Reward count" value={data.rewardCount || 0} />
            </div>
            <div className="mt-5">
                <p className="text-xs text-gray-400 mb-2">
                    Reward trend over time
                </p>
                <TinyTrend
                    values={rewardSeries}
                    color={
                        accent === "text-emerald-400"
                            ? "bg-emerald-500"
                            : "bg-sky-500"
                    }
                />
            </div>
        </div>
    );
};

const Stat = ({ label, value }) => (
    <div className="bg-gray-900/60 border border-gray-700 rounded p-2">
        <p className="text-[11px] text-gray-400">{label}</p>
        <p className="font-mono text-sm mt-1">{value ?? "--"}</p>
    </div>
);

const AgentsDashboard = () => {
    const { agentAnalytics, fetchAgentAnalytics } = useSystemStore();
    useWebSocket();

    useEffect(() => {
        fetchAgentAnalytics();
        const id = setInterval(fetchAgentAnalytics, 2000);
        return () => clearInterval(id);
    }, [fetchAgentAnalytics]);

    const history = useMemo(
        () => agentAnalytics?.history || [],
        [agentAnalytics],
    );
    const current = agentAnalytics?.current || {};

    const agent1Rewards = useMemo(
        () => history.map((h) => h?.agent1?.avgReward || 0),
        [history],
    );
    const agent2Rewards = useMemo(
        () => history.map((h) => h?.agent2?.avgReward || 0),
        [history],
    );

    return (
        <div className="min-h-screen bg-gradient-to-br from-gray-900 via-slate-900 to-zinc-900 text-white">
            <header className="border-b border-gray-700 bg-black/30 backdrop-blur">
                <div className="max-w-7xl mx-auto px-6 py-8">
                    <div className="flex flex-wrap gap-4 items-center justify-between">
                        <div>
                            <h1 className="text-3xl font-bold">
                                Agents Observability
                            </h1>
                            <p className="text-gray-400 mt-1">
                                Behavioral cloning readiness, NSGA context,
                                rewards, penalties, and live training
                                trajectories.
                            </p>
                        </div>
                        <a
                            href="/"
                            className="px-4 py-2 rounded bg-slate-700 hover:bg-slate-600 text-sm font-medium"
                        >
                            Back to main dashboard
                        </a>
                    </div>
                </div>
            </header>

            <main className="max-w-7xl mx-auto px-6 py-8 space-y-6">
                <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <div className="bg-gray-800/60 border border-gray-700 rounded-xl p-5">
                        <h2 className="text-lg font-semibold">
                            Behavioral Cloning
                        </h2>
                        <div className="mt-4 space-y-3 text-sm">
                            <div className="bg-gray-900/60 border border-gray-700 rounded p-3">
                                <p className="text-emerald-400 font-medium">
                                    Agent 1
                                </p>
                                <p className="text-gray-300 mt-1">
                                    {agentAnalytics?.behavioralCloning?.agent1
                                        ?.description || "--"}
                                </p>
                                <p className="text-xs text-gray-400 mt-2">
                                    Status:{" "}
                                    {agentAnalytics?.behavioralCloning?.agent1
                                        ?.status || "--"}
                                </p>
                            </div>
                            <div className="bg-gray-900/60 border border-gray-700 rounded p-3">
                                <p className="text-sky-400 font-medium">
                                    Agent 2
                                </p>
                                <p className="text-gray-300 mt-1">
                                    {agentAnalytics?.behavioralCloning?.agent2
                                        ?.description || "--"}
                                </p>
                                <p className="text-xs text-gray-400 mt-2">
                                    Status:{" "}
                                    {agentAnalytics?.behavioralCloning?.agent2
                                        ?.status || "--"}
                                </p>
                            </div>
                        </div>
                    </div>

                    <div className="bg-gray-800/60 border border-gray-700 rounded-xl p-5">
                        <h2 className="text-lg font-semibold">
                            NSGA-II/MMDE Results Context
                        </h2>
                        <div className="mt-4 overflow-auto">
                            <table className="w-full text-sm">
                                <thead>
                                    <tr className="text-gray-400 border-b border-gray-700">
                                        <th className="text-left py-2">
                                            Method
                                        </th>
                                        <th className="text-right py-2">
                                            Success %
                                        </th>
                                        <th className="text-right py-2">
                                            Latency ms
                                        </th>
                                        <th className="text-right py-2">
                                            Energy J
                                        </th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {Object.values(
                                        agentAnalytics?.nsgaResults || {},
                                    ).map((row) => (
                                        <tr
                                            key={row.name}
                                            className="border-b border-gray-800"
                                        >
                                            <td className="py-2">{row.name}</td>
                                            <td className="py-2 text-right font-mono">
                                                {row.successRate}
                                            </td>
                                            <td className="py-2 text-right font-mono">
                                                {row.avgLatency}
                                            </td>
                                            <td className="py-2 text-right font-mono">
                                                {row.totalEnergy}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </section>

                <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <AgentCard
                        name="Agent 1 - Task Placement"
                        data={current.agent1}
                        rewardSeries={agent1Rewards}
                        accent="text-emerald-400"
                    />
                    <AgentCard
                        name="Agent 2 - SDN Routing"
                        data={current.agent2}
                        rewardSeries={agent2Rewards}
                        accent="text-sky-400"
                    />
                </section>

                <section className="bg-gray-800/60 border border-gray-700 rounded-xl p-5">
                    <h2 className="text-lg font-semibold">
                        Agent 1 Decision Mix
                    </h2>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
                        <Stat
                            label="Local"
                            value={current.agent1?.decisions?.local || 0}
                        />
                        <Stat
                            label="Fog"
                            value={current.agent1?.decisions?.fog || 0}
                        />
                        <Stat
                            label="Cloud"
                            value={current.agent1?.decisions?.cloud || 0}
                        />
                        <Stat
                            label="Super tasks"
                            value={current.agent1?.decisions?.superTasks || 0}
                        />
                    </div>
                </section>
            </main>
        </div>
    );
};

export default AgentsDashboard;
