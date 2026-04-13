import React, { useEffect } from "react";
import Dashboard from "./components/Dashboard";
import AgentsDashboard from "./components/AgentsDashboard";
import SystemExplorer from "./components/SystemExplorer";
import ThesisArchitecture from "./components/ThesisArchitecture";
import useSystemStore from "./store/systemStore";
import "./App.css";

function App() {
    const fetchConfig = useSystemStore((state) => state.fetchConfig);
    const fetchBaselines = useSystemStore((state) => state.fetchBaselines);
    const fetchAgentAnalytics = useSystemStore(
        (state) => state.fetchAgentAnalytics,
    );

    useEffect(() => {
        // Load configuration and baselines on app start
        fetchConfig();
        fetchBaselines();
        fetchAgentAnalytics();
    }, [fetchConfig, fetchBaselines, fetchAgentAnalytics]);

    const isMapOnlyRoute =
        window.location.pathname === "/map" ||
        window.location.pathname === "/map/" ||
        window.location.hash === "#/map";

    const isAgentsRoute =
        window.location.pathname === "/agents" ||
        window.location.pathname === "/agents/" ||
        window.location.hash === "#/agents";

    const isLogicRoute =
        window.location.pathname === "/logic" ||
        window.location.pathname === "/logic/" ||
        window.location.hash === "#/logic";

    const isThesisRoute =
        window.location.pathname === "/thesis" ||
        window.location.pathname === "/thesis/" ||
        window.location.hash === "#/thesis";

    return (
        <div className="App">
            {isLogicRoute ? (
                <SystemExplorer />
            ) : isThesisRoute ? (
                <ThesisArchitecture />
            ) : isAgentsRoute ? (
                <AgentsDashboard />
            ) : (
                <Dashboard mapOnly={isMapOnlyRoute} />
            )}
        </div>
    );
}

export default App;
