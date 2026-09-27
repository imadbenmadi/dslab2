import { create } from "zustand";
import axios from "axios";

const API_URL = process.env.REACT_APP_API_URL || "http://localhost:5000/api";

/**
 * Zustand store for system state management
 */
const useSystemStore = create((set, get) => ({
    // State
    metrics: null,
    isRunning: false,
    systemType: "proposed",
    progress: 0,
    history: [],
    config: null,
    baselines: null,
    agentAnalytics: null,
    logicSnapshot: null,
    recentTasks: [],
    recentLogs: [],
    evaluationSummary: null,
    storageHealth: null,
    analyticsWindow: null,
    vehicleAnalytics: null,
    selectedWindow: "1h",
    selectedVehicle: "V000",
    isRetraining: false,
    trainingProgress: 0,

    // Actions
    setMetrics: (metrics) => set({ metrics }),
    setIsRunning: (isRunning) => set({ isRunning }),
    setSystemType: (systemType) => set({ systemType }),
    setProgress: (progress) => set({ progress }),
    setIsRetraining: (isRetraining) => set({ isRetraining }),
    setTrainingProgress: (trainingProgress) => set({ trainingProgress }),
    setSelectedWindow: (selectedWindow) => set({ selectedWindow }),
    setSelectedVehicle: (selectedVehicle) => set({ selectedVehicle }),
    setAgentAnalytics: (agentAnalytics) => set({ agentAnalytics }),
    setLogicSnapshot: (logicSnapshot) => set({ logicSnapshot }),
    addToHistory: (metric) =>
        set((state) => ({
            history: [...state.history.slice(-99), metric], // Keep last 100
        })),

    // API Actions
    startSimulation: async (systemType) => {
        try {
            const type =
                typeof systemType === "string" ? systemType : get().systemType;
            await axios.post(`${API_URL}/simulation/start`, {
                systemType: type,
            });
            set({ isRunning: true, systemType: type });
        } catch (error) {
            console.error("Failed to start simulation:", error);
        }
    },

    stopSimulation: async () => {
        try {
            await axios.post(`${API_URL}/simulation/stop`);
            set({ isRunning: false });
        } catch (error) {
            console.error("Failed to stop simulation:", error);
        }
    },

    retrainAgents: async () => {
        try {
            set({ isRetraining: true, trainingProgress: 0 });

            await axios.post(`${API_URL}/retrain`);

            // Poll training status
            let done = false;
            let progress = 0;

            while (!done) {
                await new Promise((resolve) => setTimeout(resolve, 500));

                const statusResponse = await axios.get(
                    `${API_URL}/training-status`,
                );
                const { retraining } = statusResponse.data;

                progress = Math.min(progress + 10, 90);
                set({ trainingProgress: progress });

                if (!retraining) {
                    done = true;
                    set({ trainingProgress: 100, isRetraining: false });
                    // Reset after delay
                    setTimeout(() => {
                        set({ trainingProgress: 0 });
                    }, 2000);
                }
            }
        } catch (error) {
            console.error("Retraining failed:", error);
            set({ isRetraining: false, trainingProgress: 0 });
        }
    },

    resetSimulation: async () => {
        try {
            await axios.post(`${API_URL}/simulation/reset`);
            set({
                isRunning: false,
                progress: 0,
                metrics: null,
                history: [],
            });
        } catch (error) {
            console.error("Failed to reset simulation:", error);
        }
    },

    fetchStatus: async () => {
        try {
            const response = await axios.get(`${API_URL}/status`);
            const data = response.data;
            set({
                isRunning: data.isRunning,
                progress: data.progress * 100,
                systemType: data.systemType,
            });
        } catch (error) {
            console.error("Failed to fetch status:", error);
        }
    },

    fetchStorageHealth: async () => {
        try {
            const response = await axios.get(`${API_URL}/health`);
            set({ storageHealth: response.data.storage || null });
        } catch (error) {
            console.error("Failed to fetch storage health:", error);
            set({ storageHealth: null });
        }
    },

    fetchAnalyticsWindow: async (window = null) => {
        try {
            const selected = window || get().selectedWindow || "1h";
            const response = await axios.get(
                `${API_URL}/analytics/window?window=${encodeURIComponent(selected)}`,
            );
            set({ analyticsWindow: response.data, selectedWindow: selected });
        } catch (error) {
            console.error("Failed to fetch analytics window:", error);
            set({ analyticsWindow: null });
        }
    },

    fetchVehicleAnalytics: async (vehicleId = null, window = null) => {
        try {
            const vid = vehicleId || get().selectedVehicle || "V000";
            const selected = window || get().selectedWindow || "24h";
            const response = await axios.get(
                `${API_URL}/analytics/vehicle/${encodeURIComponent(vid)}?window=${encodeURIComponent(selected)}&limit=200`,
            );
            set({
                vehicleAnalytics: response.data,
                selectedVehicle: vid,
                selectedWindow: selected,
            });
        } catch (error) {
            console.error("Failed to fetch vehicle analytics:", error);
            set({ vehicleAnalytics: null });
        }
    },

    fetchConfig: async () => {
        try {
            const response = await axios.get(`${API_URL}/config`);
            set({ config: response.data });
        } catch (error) {
            console.error("Failed to fetch config:", error);
        }
    },

    fetchBaselines: async () => {
        try {
            const response = await axios.get(`${API_URL}/baselines`);
            set({ baselines: response.data });
        } catch (error) {
            console.error("Failed to fetch baselines:", error);
        }
    },

    fetchAgentAnalytics: async () => {
        try {
            const response = await axios.get(`${API_URL}/agents/analytics`);
            set({ agentAnalytics: response.data });
        } catch (error) {
            console.error("Failed to fetch agent analytics:", error);
        }
    },

    fetchLogicSnapshot: async () => {
        try {
            const response = await axios.get(`${API_URL}/logic/snapshot`);
            set({ logicSnapshot: response.data });
        } catch (error) {
            console.error("Failed to fetch logic snapshot:", error);
        }
    },

    fetchRecentTasks: async () => {
        try {
            const response = await axios.get(`${API_URL}/tasks/recent`);
            set({ recentTasks: response.data.items || [] });
        } catch (error) {
            console.error("Failed to fetch tasks:", error);
        }
    },

    fetchRecentLogs: async () => {
        try {
            const response = await axios.get(`${API_URL}/logs/recent`);
            set({ recentLogs: response.data.items || [] });
        } catch (error) {
            console.error("Failed to fetch logs:", error);
        }
    },

    fetchEvaluationSummary: async () => {
        try {
            const response = await axios.get(`${API_URL}/evaluation/summary`);
            set({ evaluationSummary: response.data });
        } catch (error) {
            // Keep quiet when insufficient data early in a run.
            set({ evaluationSummary: null });
        }
    },

    updateMetricsFromWebSocket: (data) => {
        set((state) => ({
            metrics: data,
            agentAnalytics: data.agentDetails
                ? {
                      ...(state.agentAnalytics || {}),
                      current: data.agentDetails,
                  }
                : state.agentAnalytics,
            history: [...state.history.slice(-99), data],
        }));
    },
}));

export default useSystemStore;
