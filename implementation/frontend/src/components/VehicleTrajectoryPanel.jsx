import React, { useState, useEffect } from "react";
import { ChevronDown } from "lucide-react";

/**
 * Vehicle Trajectory and Handoff Prediction Panel
 * Shows individual vehicle trajectory predictions and handoff opportunities
 */
const VehicleTrajectoryPanel = ({ isOpen, onToggle }) => {
    const [vehicles, setVehicles] = useState([]);
    const [selectedVehicle, setSelectedVehicle] = useState(null);
    const [trajectoryData, setTrajectoryData] = useState(null);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        const fetchVehicles = async () => {
            try {
                const res = await fetch("/api/map/state");
                const data = await res.json();
                setVehicles(data.vehicles || []);
            } catch (e) {
                console.error("Failed to fetch vehicles", e);
            }
        };

        if (isOpen) {
            const interval = setInterval(fetchVehicles, 1000);
            fetchVehicles();
            return () => clearInterval(interval);
        }
    }, [isOpen]);

    const handleSelectVehicle = async (vehicleId) => {
        setSelectedVehicle(vehicleId);
        setLoading(true);
        try {
            const res = await fetch(`/api/map/trajectory/${vehicleId}`);
            const data = await res.json();
            setTrajectoryData(data);
        } catch (e) {
            console.error("Failed to fetch trajectory", e);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="bg-gray-800 bg-opacity-50 backdrop-blur border border-gray-700 rounded-lg p-6">
            <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold">
                    Vehicle Trajectory Predictions
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
                <div className="grid grid-cols-3 gap-4">
                    {/* Vehicle List */}
                    <div className="col-span-1">
                        <div className="bg-gray-900 rounded p-4 max-h-96 overflow-y-auto">
                            <h4 className="text-sm font-semibold text-gray-300 mb-3">
                                Active Vehicles ({vehicles.length})
                            </h4>
                            <div className="space-y-1">
                                {vehicles.map((v) => (
                                    <button
                                        key={v.id}
                                        onClick={() =>
                                            handleSelectVehicle(v.id)
                                        }
                                        className={`w-full text-left px-3 py-2 rounded text-sm transition ${
                                            selectedVehicle === v.id
                                                ? "bg-blue-600 text-white"
                                                : "text-gray-300 hover:bg-gray-800"
                                        }`}
                                    >
                                        <div className="font-mono">{v.id}</div>
                                        <div className="text-xs text-gray-400">
                                            {v.speed_kmh?.toFixed(1) || "0"}
                                            km/h
                                        </div>
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>

                    {/* Trajectory Details */}
                    <div className="col-span-2">
                        {loading ? (
                            <div className="bg-gray-900 rounded p-4 text-gray-400">
                                Loading trajectory data...
                            </div>
                        ) : trajectoryData ? (
                            <div className="bg-gray-900 rounded p-4 space-y-3">
                                <div>
                                    <div className="text-xs font-semibold text-gray-400 mb-1">
                                        Vehicle ID
                                    </div>
                                    <div className="text-white font-mono">
                                        {trajectoryData.vehicleId}
                                    </div>
                                </div>

                                <div className="grid grid-cols-2 gap-3">
                                    <div>
                                        <div className="text-xs font-semibold text-gray-400 mb-1">
                                            Position
                                        </div>
                                        <div className="text-white text-sm">
                                            (
                                            {trajectoryData.position?.x?.toFixed(
                                                0,
                                            ) || 0}
                                            ,{" "}
                                            {trajectoryData.position?.y?.toFixed(
                                                0,
                                            ) || 0}
                                            )
                                        </div>
                                    </div>

                                    <div>
                                        <div className="text-xs font-semibold text-gray-400 mb-1">
                                            Speed
                                        </div>
                                        <div className="text-white text-sm">
                                            {trajectoryData.speed?.toFixed(1) ||
                                                0}
                                            km/h
                                        </div>
                                    </div>

                                    <div>
                                        <div className="text-xs font-semibold text-gray-400 mb-1">
                                            Current Fog
                                        </div>
                                        <div className="text-white text-sm">
                                            {trajectoryData.currentFog || "—"}
                                        </div>
                                    </div>

                                    <div>
                                        <div className="text-xs font-semibold text-gray-400 mb-1">
                                            Heading
                                        </div>
                                        <div className="text-white text-sm">
                                            {trajectoryData.heading?.toFixed(
                                                1,
                                            ) || 0}
                                            °
                                        </div>
                                    </div>
                                </div>

                                <div className="border-t border-gray-700 pt-3">
                                    <h4 className="text-xs font-semibold text-yellow-400 mb-2">
                                        Handoff Prediction
                                    </h4>
                                    <div className="space-y-2">
                                        <div className="flex items-center justify-between">
                                            <span className="text-xs text-gray-400">
                                                T_exit (time to leave zone):
                                            </span>
                                            <span className="text-white font-mono text-sm">
                                                {trajectoryData.t_exit
                                                    ? trajectoryData.t_exit.toFixed(
                                                          2,
                                                      ) + "s"
                                                    : "—"}
                                            </span>
                                        </div>
                                        <div className="flex items-center justify-between">
                                            <span className="text-xs text-gray-400">
                                                Next Fog Zone:
                                            </span>
                                            <span className="text-green-400 font-mono text-sm">
                                                {trajectoryData.nextFog ||
                                                    "CLOUD"}
                                            </span>
                                        </div>
                                    </div>

                                    {trajectoryData.trajectory &&
                                        trajectoryData.trajectory.length >
                                            0 && (
                                            <div className="mt-3 pt-3 border-t border-gray-700">
                                                <h5 className="text-xs font-semibold text-gray-400 mb-2">
                                                    Predicted Path (
                                                    {
                                                        trajectoryData
                                                            .trajectory.length
                                                    }{" "}
                                                    points)
                                                </h5>
                                                <div className="text-xs text-gray-400 space-y-1">
                                                    {trajectoryData.trajectory
                                                        .slice(0, 3)
                                                        .map((pt, i) => (
                                                            <div
                                                                key={i}
                                                                className="font-mono"
                                                            >
                                                                Waypoint {i}: (
                                                                {pt.x?.toFixed(
                                                                    0,
                                                                ) || 0}
                                                                ,{" "}
                                                                {pt.y?.toFixed(
                                                                    0,
                                                                ) || 0}
                                                                )
                                                            </div>
                                                        ))}
                                                    {trajectoryData.trajectory
                                                        .length > 3 && (
                                                        <div className="text-gray-500">
                                                            ...
                                                            {trajectoryData
                                                                .trajectory
                                                                .length -
                                                                3}{" "}
                                                            more points
                                                        </div>
                                                    )}
                                                </div>
                                            </div>
                                        )}
                                </div>
                            </div>
                        ) : (
                            <div className="bg-gray-900 rounded p-4 text-gray-400 text-center">
                                <p>Select a vehicle to view trajectory</p>
                                <p className="text-xs text-gray-500 mt-2">
                                    Shows predicted path, handoff opportunities,
                                    and T_exit time
                                </p>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};

export default VehicleTrajectoryPanel;
