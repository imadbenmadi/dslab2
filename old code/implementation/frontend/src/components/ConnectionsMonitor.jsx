import React, { useState, useEffect } from "react";
import { ChevronDown, Activity, GitBranch, Zap } from "lucide-react";

/**
 * Connections and Handoffs Monitor
 * Visualizes all active network connections and handoff events
 */
const ConnectionsMonitor = ({ isOpen, onToggle }) => {
    const [connections, setConnections] = useState([]);
    const [handoffs, setHandoffs] = useState([]);
    const [stats, setStats] = useState({
        device_to_fog: 0,
        fog_to_fog: 0,
        fog_to_cloud: 0,
        total: 0,
    });

    useEffect(() => {
        const fetchData = async () => {
            try {
                const [connRes, handRes] = await Promise.all([
                    fetch("/api/map/connections"),
                    fetch("/api/map/handoffs"),
                ]);

                const connData = await connRes.json();
                const handData = await handRes.json();

                setConnections(connData.connections || []);
                setHandoffs(handData.handoffs || []);

                // Calculate stats
                const stats = {
                    device_to_fog: 0,
                    fog_to_fog: 0,
                    fog_to_cloud: 0,
                    total: connData.connections?.length || 0,
                };

                (connData.connections || []).forEach((c) => {
                    const leg = c.leg || "unknown";
                    if (leg in stats) {
                        stats[leg]++;
                    }
                });

                setStats(stats);
            } catch (e) {
                console.error("Failed to fetch connections", e);
            }
        };

        if (isOpen) {
            const interval = setInterval(fetchData, 1000);
            fetchData();
            return () => clearInterval(interval);
        }
    }, [isOpen]);

    const getConnectionColor = (leg) => {
        switch (leg) {
            case "device_to_fog":
                return "text-green-400";
            case "fog_to_fog":
                return "text-yellow-400";
            case "fog_to_cloud":
                return "text-blue-400";
            default:
                return "text-gray-400";
        }
    };

    const getConnectionIcon = (leg) => {
        switch (leg) {
            case "fog_to_fog":
                return <GitBranch size={14} className="inline mr-1" />;
            case "fog_to_cloud":
                return <Zap size={14} className="inline mr-1" />;
            default:
                return <Activity size={14} className="inline mr-1" />;
        }
    };

    return (
        <div className="bg-gray-800 bg-opacity-50 backdrop-blur border border-gray-700 rounded-lg p-6">
            <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold">
                    Connections & Handoffs
                </h3>
                <button
                    onClick={onToggle}
                    className="text-gray-400 hover:text-white"
                >
                    <ChevronDown
                        size={20}
                        className={`transition-transform ${
                            isOpen ? "rotate-180" : ""
                        }`}
                    />
                </button>
            </div>

            {isOpen && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                    {/* Connection Stats */}
                    <div className="bg-gray-900 rounded p-4">
                        <div className="text-xs font-semibold text-gray-400 mb-3">
                            Active Connections
                        </div>
                        <div className="space-y-2">
                            <div className="flex justify-between items-center">
                                <span className="text-sm text-green-400">
                                    Device→Fog:
                                </span>
                                <span className="font-mono text-white">
                                    {stats.device_to_fog}
                                </span>
                            </div>
                            <div className="flex justify-between items-center">
                                <span className="text-sm text-yellow-400">
                                    Fog→Fog:
                                </span>
                                <span className="font-mono text-white">
                                    {stats.fog_to_fog}
                                </span>
                            </div>
                            <div className="flex justify-between items-center">
                                <span className="text-sm text-blue-400">
                                    Fog→Cloud:
                                </span>
                                <span className="font-mono text-white">
                                    {stats.fog_to_cloud}
                                </span>
                            </div>
                            <div className="border-t border-gray-700 pt-2 mt-2 flex justify-between items-center">
                                <span className="text-sm font-semibold text-gray-300">
                                    Total:
                                </span>
                                <span className="font-mono text-white font-semibold">
                                    {stats.total}
                                </span>
                            </div>
                        </div>
                    </div>

                    {/* Handoff Events */}
                    <div className="bg-gray-900 rounded p-4 col-span-2">
                        <div className="text-xs font-semibold text-gray-400 mb-3">
                            Recent Handoff Events ({handoffs.length})
                        </div>
                        <div className="space-y-2 max-h-32 overflow-y-auto">
                            {handoffs.length > 0 ? (
                                handoffs.slice(0, 5).map((h, i) => (
                                    <div
                                        key={i}
                                        className="text-xs text-gray-300 bg-gray-800 rounded p-2 flex items-center justify-between"
                                    >
                                        <span>
                                            <span className="text-yellow-400 font-mono">
                                                {h.vehicleId || "V?"}
                                            </span>
                                            : {h.source_fog || "?"} →{" "}
                                            {h.target_fog || "?"}
                                        </span>
                                        <span className="text-gray-500 text-xs">
                                            {h.mode || "REACTIVE"}
                                        </span>
                                    </div>
                                ))
                            ) : (
                                <div className="text-gray-500 text-xs italic">
                                    No handoffs detected
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {isOpen && connections.length > 0 && (
                <div className="bg-gray-900 rounded p-4">
                    <div className="text-xs font-semibold text-gray-400 mb-3">
                        Connection Details (Showing{" "}
                        {Math.min(10, connections.length)}/{connections.length})
                    </div>
                    <div className="space-y-1 max-h-48 overflow-y-auto text-xs">
                        {connections.slice(0, 10).map((c, i) => (
                            <div
                                key={i}
                                className="text-gray-400 flex items-center justify-between hover:bg-gray-800 p-1 rounded"
                            >
                                <div>
                                    <span
                                        className={`font-mono ${getConnectionColor(c.leg)}`}
                                    >
                                        {getConnectionIcon(c.leg)}
                                        {c.leg}
                                    </span>
                                    {c.taskId && (
                                        <span className="ml-2 text-gray-500">
                                            Task {c.taskId.substring(0, 8)}
                                        </span>
                                    )}
                                </div>
                                {c.network?.preinstalled && (
                                    <span className="text-purple-400 text-xs">
                                        ⚡
                                    </span>
                                )}
                                {c.network?.packetDrop && (
                                    <span className="text-red-400 text-xs">
                                        ✗
                                    </span>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};

export default ConnectionsMonitor;
