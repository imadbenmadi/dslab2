import React from "react";
import useSystemStore from "../store/systemStore";
import { useWebSocket } from "../hooks/useWebSocket";
import { MapContainer, TileLayer, Circle, Polyline } from "react-leaflet";
import VehicleTrajectoryPanel from "./VehicleTrajectoryPanel";
import ConnectionsMonitor from "./ConnectionsMonitor";

/**
 * Main Dashboard Component
 * Real-time display of all system metrics
 */
const Dashboard = ({ mapOnly = false }) => {
    const {
        metrics,
        isRunning,
        systemType,
        progress,
        startSimulation,
        stopSimulation,
        resetSimulation,
        setSystemType,
    } = useSystemStore();

    const [showTrajectory, setShowTrajectory] = React.useState(false);
    const [showConnections, setShowConnections] = React.useState(false);

    useWebSocket();

    return (
        <div className="min-h-screen bg-gradient-to-br from-gray-900 to-gray-800 text-white">
            {/* Header */}
            <header className="bg-black bg-opacity-50 backdrop-blur border-b border-gray-700">
                <div className="max-w-7xl mx-auto px-6 py-8">
                    <h1 className="text-4xl font-bold mb-2">
                        Smart City Vehicular Task Offloading System
                    </h1>
                    <p className="text-gray-400">
                        Real-Time Dashboard • Istanbul • 50 Vehicles • 4 Fog
                        Nodes
                    </p>
                    <div className="mt-4">
                        <a
                            href={mapOnly ? "/" : "/map"}
                            className="inline-block px-4 py-2 rounded bg-blue-600 hover:bg-blue-700 text-sm font-medium"
                        >
                            {mapOnly
                                ? "Back to Main Dashboard"
                                : "Open Full Istanbul Live Map"}
                        </a>
                        {!mapOnly && (
                            <a
                                href="/agents"
                                className="inline-block ml-3 px-4 py-2 rounded bg-emerald-600 hover:bg-emerald-700 text-sm font-medium"
                            >
                                Open Agents Observability
                            </a>
                        )}
                        {!mapOnly && (
                            <a
                                href="/logic"
                                className="inline-block ml-3 px-4 py-2 rounded bg-cyan-600 hover:bg-cyan-700 text-sm font-medium"
                            >
                                Open Full Logic Explorer
                            </a>
                        )}
                        {!mapOnly && (
                            <a
                                href="/thesis"
                                className="inline-block ml-3 px-4 py-2 rounded bg-fuchsia-600 hover:bg-fuchsia-700 text-sm font-medium"
                            >
                                Open Thesis Architecture v2
                            </a>
                        )}
                    </div>
                </div>
            </header>

            {/* Control Panel */}
            <div className="bg-gray-800 bg-opacity-50 border-b border-gray-700">
                <div className="max-w-7xl mx-auto px-6 py-6">
                    <div className="flex flex-wrap gap-4 items-center">
                        {/* System Type Selector */}
                        <div className="flex gap-2">
                            {[
                                "baseline1",
                                "baseline2",
                                "baseline3",
                                "proposed",
                            ].map((type) => (
                                <button
                                    key={type}
                                    onClick={() => setSystemType(type)}
                                    className={`px-4 py-2 rounded font-medium transition ${
                                        systemType === type
                                            ? "bg-green-600 text-white"
                                            : "bg-gray-700 text-gray-300 hover:bg-gray-600"
                                    }`}
                                    disabled={isRunning}
                                >
                                    {type === "baseline1" &&
                                        "Baseline 1 (NSGA-II)"}
                                    {type === "baseline2" && "Baseline 2 (TOF)"}
                                    {type === "baseline3" &&
                                        "Baseline 3 (MMDE)"}
                                    {type === "proposed" && "Proposed (DQN)"}
                                </button>
                            ))}
                        </div>

                        {/* Control Buttons */}
                        <div className="flex gap-2 ml-auto">
                            <button
                                onClick={() => startSimulation()}
                                disabled={isRunning}
                                className="px-6 py-2 bg-green-600 hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed rounded font-medium transition"
                            >
                                ▶ Start
                            </button>
                            <button
                                onClick={stopSimulation}
                                disabled={!isRunning}
                                className="px-6 py-2 bg-red-600 hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed rounded font-medium transition"
                            >
                                ⏹ Stop
                            </button>
                            <button
                                onClick={resetSimulation}
                                className="px-6 py-2 bg-gray-700 hover:bg-gray-600 rounded font-medium transition"
                            >
                                ↻ Reset
                            </button>
                            <button
                                onClick={() =>
                                    useSystemStore.getState().retrainAgents()
                                }
                                className="px-6 py-2 bg-orange-600 hover:bg-orange-700 disabled:opacity-50 disabled:cursor-not-allowed rounded font-medium transition flex items-center gap-2"
                            >
                                🔄 Retrain AI
                            </button>
                        </div>
                    </div>

                    {/* Progress Bar */}
                    <div className="mt-6">
                        <div className="flex justify-between mb-2">
                            <span className="text-sm text-gray-400">
                                Simulation Progress
                            </span>
                            <span className="text-sm font-mono">
                                {progress.toFixed(1)}% •{" "}
                                {metrics?.simulationTime?.toFixed(1)}s / 900s
                            </span>
                        </div>
                        <div className="w-full bg-gray-700 rounded-full h-2 overflow-hidden">
                            <div
                                className="bg-gradient-to-r from-blue-500 to-green-500 h-full transition-all duration-300"
                                style={{ width: `${progress}%` }}
                            />
                        </div>
                    </div>
                </div>
            </div>

            {/* Main Content */}
            <main className="max-w-7xl mx-auto px-6 py-8">
                {mapOnly ? (
                    <div className="grid grid-cols-1 gap-6">
                        <CityVisualization metrics={metrics} fullScreen />
                    </div>
                ) : (
                    <>
                        Open route:{" "}
                        <a className="text-blue-400" href="/map">
                            /map
                        </a>{" "}
                        for full-screen live map
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
                            <MetricCard
                                title="Deadline Success Rate"
                                value={metrics?.successRate}
                                unit="%"
                                target={85}
                                color="text-green-400"
                            />
                            <MetricCard
                                title="Avg Latency"
                                value={metrics?.avgLatency}
                                unit="ms"
                                target={150}
                                color="text-blue-400"
                                inverse
                            />
                            <MetricCard
                                title="Tasks Processed"
                                value={metrics?.taskCount}
                                unit="tasks"
                                color="text-yellow-400"
                            />
                            <MetricCard
                                title="Throughput"
                                value={metrics?.throughput}
                                unit="tasks/s"
                                color="text-purple-400"
                            />
                        </div>
                        {/* Device Utilization & Network */}
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
                            <DeviceUtilization metrics={metrics} />
                            <NetworkMetrics metrics={metrics} />
                        </div>
                        {/* Agent Performance & Handoff */}
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
                            <AgentPerformance metrics={metrics} />
                            <HandoffMetrics metrics={metrics} />
                        </div>
                        {/* Connections & Trajectory Monitoring */}
                        <div className="grid grid-cols-1 gap-6 mb-8">
                            <ConnectionsMonitor
                                isOpen={showConnections}
                                onToggle={() =>
                                    setShowConnections(!showConnections)
                                }
                            />
                        </div>
                        <div className="grid grid-cols-1 gap-6 mb-8">
                            <VehicleTrajectoryPanel
                                isOpen={showTrajectory}
                                onToggle={() =>
                                    setShowTrajectory(!showTrajectory)
                                }
                            />
                        </div>
                        {/* Istanbul City Visualization & Learning Status */}
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                            <CityVisualization metrics={metrics} />
                            <LearningStatus />
                        </div>
                    </>
                )}
            </main>
        </div>
    );
};

/**
 * Individual Metric Card
 */
const MetricCard = ({ title, value, unit, target, color, inverse }) => {
    const displayValue = value !== undefined ? value.toFixed(1) : "--";
    const isTarget =
        target && !inverse
            ? value >= target
            : inverse
              ? value <= target
              : false;

    return (
        <div className="bg-gray-800 bg-opacity-50 backdrop-blur border border-gray-700 rounded-lg p-6">
            <h3 className="text-gray-400 text-sm font-medium mb-3">{title}</h3>
            <div className="flex items-baseline gap-2">
                <span className={`text-3xl font-bold ${color}`}>
                    {displayValue}
                </span>
                <span className="text-gray-500 text-sm">{unit}</span>
            </div>
            {target && (
                <p
                    className={`text-xs mt-2 ${isTarget ? "text-green-400" : "text-red-400"}`}
                >
                    Target: {target}
                    {unit} {isTarget ? "✓" : "✗"}
                </p>
            )}
        </div>
    );
};

/**
 * Device Utilization Component
 */
const DeviceUtilization = ({ metrics }) => {
    if (!metrics) return null;

    const devices = [
        {
            name: "Fog 1",
            value: metrics.devices?.fog1 || 0,
            color: "from-red-500",
        },
        {
            name: "Fog 2",
            value: metrics.devices?.fog2 || 0,
            color: "from-orange-500",
        },
        {
            name: "Fog 3",
            value: metrics.devices?.fog3 || 0,
            color: "from-yellow-500",
        },
        {
            name: "Fog 4",
            value: metrics.devices?.fog4 || 0,
            color: "from-green-500",
        },
        {
            name: "Cloud",
            value: metrics.devices?.cloud || 0,
            color: "from-blue-500",
        },
    ];

    return (
        <div className="bg-gray-800 bg-opacity-50 backdrop-blur border border-gray-700 rounded-lg p-6">
            <h3 className="text-lg font-semibold mb-6">Device Utilization</h3>
            <div className="space-y-4">
                {devices.map((device) => (
                    <div key={device.name}>
                        <div className="flex justify-between mb-2">
                            <span className="text-sm text-gray-400">
                                {device.name}
                            </span>
                            <span className="text-sm font-mono">
                                {(device.value * 100).toFixed(1)}%
                            </span>
                        </div>
                        <div className="w-full bg-gray-700 rounded-full h-2">
                            <div
                                className={`bg-gradient-to-r ${device.color} to-transparent h-full rounded-full transition-all duration-300`}
                                style={{ width: `${device.value * 100}%` }}
                            />
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

/**
 * Network Metrics Component
 */
const NetworkMetrics = ({ metrics }) => {
    if (!metrics) return null;

    return (
        <div className="bg-gray-800 bg-opacity-50 backdrop-blur border border-gray-700 rounded-lg p-6">
            <h3 className="text-lg font-semibold mb-6">Network Metrics</h3>
            <div className="space-y-4">
                <div>
                    <div className="flex justify-between mb-2">
                        <span className="text-sm text-gray-400">
                            Bandwidth Used
                        </span>
                        <span className="text-sm font-mono">
                            {metrics.network?.bandwidthUsed?.toFixed(1)}Mbps /
                            100Mbps
                        </span>
                    </div>
                    <div className="w-full bg-gray-700 rounded-full h-2">
                        <div
                            className="bg-gradient-to-r from-cyan-500 to-blue-500 h-full rounded-full"
                            style={{
                                width: `${Math.min((metrics.network.bandwidthUsed / 100) * 100, 100)}%`,
                            }}
                        />
                    </div>
                </div>
                <div className="pt-4 border-t border-gray-700">
                    <div className="text-sm">
                        <p className="text-gray-400 mb-2">
                            Congestion Points:{" "}
                            <span className="font-mono text-red-400">
                                {metrics.network?.congestionPoints || 0}
                            </span>
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
};

/**
 * Agent Performance Component
 */
const AgentPerformance = ({ metrics }) => {
    if (!metrics) return null;

    return (
        <div className="bg-gray-800 bg-opacity-50 backdrop-blur border border-gray-700 rounded-lg p-6">
            <h3 className="text-lg font-semibold mb-6">Agent Performance</h3>
            <div className="space-y-6">
                <div>
                    <p className="text-sm text-gray-400 mb-3">
                        Agent 1 - Task Placement
                    </p>
                    <p className="text-2xl font-bold text-green-400">
                        {metrics.agents?.agent1Latency?.toFixed(2)}ms
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                        Decision latency
                    </p>
                </div>
                <div>
                    <p className="text-sm text-gray-400 mb-3">
                        Agent 2 - SDN Routing
                    </p>
                    <p className="text-2xl font-bold text-blue-400">
                        {metrics.agents?.agent2Latency?.toFixed(2)}ms
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                        Decision latency
                    </p>
                </div>
            </div>
        </div>
    );
};

/**
 * Handoff Metrics Component
 */
const HandoffMetrics = ({ metrics }) => {
    if (!metrics) return null;

    return (
        <div className="bg-gray-800 bg-opacity-50 backdrop-blur border border-gray-700 rounded-lg p-6">
            <h3 className="text-lg font-semibold mb-6">Handoff Activity</h3>
            <div className="space-y-6">
                <div>
                    <p className="text-sm text-gray-400 mb-3">Total Handoffs</p>
                    <p className="text-2xl font-bold text-yellow-400">
                        {metrics.handoff?.count || 0}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                        Vehicle transitions tracked
                    </p>
                </div>
                <div>
                    <p className="text-sm text-gray-400 mb-3">
                        Task Migrations
                    </p>
                    <p className="text-2xl font-bold text-purple-400">
                        {metrics.handoff?.taskMigrations || 0}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                        Tasks moved during handoff
                    </p>
                </div>
            </div>
        </div>
    );
};

/**
 * Istanbul City Visualization
 */
const CityVisualization = ({ metrics, fullScreen = false }) => {
    const map = metrics?.map || {};
    const bounds = map.bounds || { xMin: 0, xMax: 1000, yMin: 0, yMax: 1000 };
    const fogNodes = map.fogNodes || [];
    const vehicles = map.vehicles || [];
    const offloads = map.offloads || [];
    const fogOffloads = offloads.filter((o) => o?.to?.type === "fog");
    const cloudOffloads = offloads.filter((o) => o?.to?.type === "cloud");

    const toLatLng = (x, y) => {
        const normX =
            (x - bounds.xMin) / Math.max(1, bounds.xMax - bounds.xMin);
        const normY =
            (y - bounds.yMin) / Math.max(1, bounds.yMax - bounds.yMin);
        const lat = 41.11 - normY * 0.18;
        const lon = 28.84 + normX * 0.28;
        return [lat, lon];
    };

    const cloudPos = toLatLng(map.cloud?.x ?? 500, map.cloud?.y ?? 500);
    const preinstalledLinks = offloads.filter(
        (o) => o?.network?.preinstalled,
    ).length;
    const droppedLinks = offloads.filter((o) => o?.network?.packetDrop).length;
    const fogRelayLinks = offloads.filter(
        (o) => o?.leg === "fog_to_cloud",
    ).length;

    return (
        <div className="bg-gray-800 bg-opacity-50 backdrop-blur border border-gray-700 rounded-lg p-6">
            <h3 className="text-lg font-semibold mb-4">
                Istanbul Real Road Network
            </h3>
            <div className="space-y-4">
                <div
                    className={`bg-gray-900 rounded p-4 flex items-center justify-center relative overflow-hidden ${
                        fullScreen ? "h-[75vh]" : "h-64"
                    }`}
                >
                    <MapContainer
                        center={[41.015, 28.98]}
                        zoom={11}
                        scrollWheelZoom
                        className="w-full h-full rounded"
                    >
                        <TileLayer
                            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                            attribution="&copy; OpenStreetMap contributors"
                        />

                        {fogNodes.map((n) => (
                            <React.Fragment key={n.id}>
                                <Circle
                                    center={toLatLng(n.x, n.y)}
                                    radius={n.coverage || 250}
                                    pathOptions={{
                                        color: "#ef4444",
                                        fillColor: "#ef4444",
                                        fillOpacity: 0.12,
                                    }}
                                />
                                <Circle
                                    center={toLatLng(n.x, n.y)}
                                    radius={40}
                                    pathOptions={{
                                        color: "#ef4444",
                                        fillColor: "#ef4444",
                                        fillOpacity: 0.85,
                                    }}
                                />
                            </React.Fragment>
                        ))}

                        <Circle
                            center={cloudPos}
                            radius={55}
                            pathOptions={{
                                color: "#3b82f6",
                                fillColor: "#3b82f6",
                                fillOpacity: 0.8,
                            }}
                        />

                        {vehicles.map((v) => (
                            <Circle
                                key={v.id}
                                center={toLatLng(v.x, v.y)}
                                radius={14}
                                pathOptions={{
                                    color: "#facc15",
                                    fillColor: "#facc15",
                                    fillOpacity: 0.9,
                                }}
                            />
                        ))}

                        {offloads.map((o, idx) => {
                            const from = toLatLng(o.from.x, o.from.y);
                            const to = toLatLng(o.to.x, o.to.y);
                            let color = "#38bdf8";
                            if (o.leg === "device_to_fog") color = "#22c55e";
                            if (o.leg === "fog_to_cloud") color = "#60a5fa";
                            if (o.leg === "fog_to_fog") color = "#eab308";
                            if (
                                o.to?.type === "fog" &&
                                o.leg !== "device_to_fog" &&
                                o.leg !== "fog_to_fog"
                            )
                                color = "#84cc16";
                            if (o.network?.packetDrop) color = "#f43f5e";
                            return (
                                <Polyline
                                    key={`${o.taskId}-${idx}`}
                                    positions={[from, to]}
                                    pathOptions={{
                                        color,
                                        weight: o.network?.preinstalled ? 4 : 2,
                                        opacity: 0.8,
                                    }}
                                />
                            );
                        })}
                    </MapContainer>
                </div>
                <div className="text-sm text-gray-400 space-y-1">
                    <p>
                        Fog nodes: {fogNodes.length || 4} | Vehicles:{" "}
                        {vehicles.length || 0}
                    </p>
                    <p>
                        Active offloads: {offloads.length || 0} (Fog:{" "}
                        {fogOffloads.length || 0}, Cloud:{" "}
                        {cloudOffloads.length || 0}) | Sim time:{" "}
                        {map.simulationTime || 0}s
                    </p>
                    <p>
                        SDN links: preinstalled {preinstalledLinks} | packet
                        drops {droppedLinks} | fog-cloud relays {fogRelayLinks}
                    </p>
                    <p>
                        Mobility: handoffs {metrics?.handoff?.count || 0} |
                        migrations {metrics?.handoff?.taskMigrations || 0}
                    </p>
                    <p>
                        Open route:{" "}
                        <a className="text-blue-400" href="/map">
                            /map
                        </a>{" "}
                        for full-screen live map
                    </p>
                </div>
            </div>
        </div>
    );
};

/**
 * Learning/Retraining Status Component
 */
const LearningStatus = () => {
    const { isRetraining, trainingProgress } = useSystemStore();
    const [autoRetrain, setAutoRetrain] = React.useState(false);

    const handleRetrain = async () => {
        try {
            const response = await fetch("http://localhost:5000/api/retrain", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
            });

            if (response.ok) {
                console.log("Retraining started");
            }
        } catch (err) {
            console.error("Retrain failed:", err);
        }
    };

    return (
        <div className="bg-gray-800 bg-opacity-50 backdrop-blur border border-gray-700 rounded-lg p-6">
            <h3 className="text-lg font-semibold mb-6">AI Learning System</h3>
            <div className="space-y-4">
                {/* Retraining Status */}
                <div>
                    <div className="flex items-center gap-2 mb-3">
                        <div
                            className={`w-3 h-3 rounded-full ${isRetraining ? "bg-orange-500 animate-pulse" : "bg-green-500"}`}
                        />
                        <span className="text-sm font-medium">
                            {isRetraining
                                ? "Retraining in progress..."
                                : "Ready for retraining"}
                        </span>
                    </div>
                    {isRetraining && (
                        <div className="w-full bg-gray-700 rounded-full h-2">
                            <div
                                className="bg-gradient-to-r from-orange-500 to-red-500 h-full rounded-full transition-all duration-300"
                                style={{ width: `${trainingProgress || 50}%` }}
                            />
                        </div>
                    )}
                </div>

                {/* Info */}
                <div className="pt-4 border-t border-gray-700 text-xs text-gray-400 space-y-2">
                    <p>✓ Agent 1: Task Placement DQN</p>
                    <p>✓ Agent 2: SDN Routing Network</p>
                    <p>✓ Learning from recent tasks</p>
                </div>

                {/* Retrain Button */}
                <button
                    onClick={handleRetrain}
                    disabled={isRetraining}
                    className="w-full mt-6 px-4 py-2 bg-orange-600 hover:bg-orange-700 disabled:opacity-50 disabled:cursor-not-allowed rounded font-medium transition"
                >
                    🔄 Retrain Agents Now
                </button>

                {/* Auto Retrain Toggle */}
                <div className="flex items-center gap-2 pt-4 border-t border-gray-700">
                    <input
                        type="checkbox"
                        id="autoRetrain"
                        checked={autoRetrain}
                        onChange={(e) => setAutoRetrain(e.target.checked)}
                        className="w-4 h-4 rounded"
                    />
                    <label
                        htmlFor="autoRetrain"
                        className="text-xs text-gray-400"
                    >
                        Auto-retrain every 5 min
                    </label>
                </div>
            </div>
        </div>
    );
};

export default Dashboard;
