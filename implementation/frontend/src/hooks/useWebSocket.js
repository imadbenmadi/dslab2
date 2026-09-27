import { useEffect, useRef } from "react";
import useSystemStore from "../store/systemStore";

/**
 * Custom hook for WebSocket connection and real-time metrics
 */
export const useWebSocket = () => {
    const wsRef = useRef(null);
    const reconnectTimeoutRef = useRef(null);
    const heartbeatIntervalRef = useRef(null);
    const updateMetricsFromWebSocket = useSystemStore(
        (state) => state.updateMetricsFromWebSocket,
    );

    useEffect(() => {
        const WS_URL = process.env.REACT_APP_WS_URL || "ws://localhost:8765";

        const connect = () => {
            try {
                const ws = new WebSocket(WS_URL);

                ws.onopen = () => {
                    console.log("[WS] Connected to WebSocket server");

                    // Clear any stale heartbeat interval from previous socket
                    if (heartbeatIntervalRef.current) {
                        clearInterval(heartbeatIntervalRef.current);
                    }

                    // Send ping every 30 seconds to keep connection alive
                    heartbeatIntervalRef.current = setInterval(() => {
                        if (ws.readyState === WebSocket.OPEN) {
                            ws.send("ping");
                        }
                    }, 30000);
                };

                ws.onmessage = (event) => {
                    // Server keepalive response is plain text.
                    if (event.data === "pong") {
                        return;
                    }

                    try {
                        const message = JSON.parse(event.data);
                        if (message.type === "metrics") {
                            updateMetricsFromWebSocket(message.data);
                        }
                    } catch (error) {
                        console.warn("[WS] Ignoring non-JSON message");
                    }
                };

                ws.onerror = (error) => {
                    console.debug("[WS] Transient socket error event");
                };

                ws.onclose = () => {
                    if (heartbeatIntervalRef.current) {
                        clearInterval(heartbeatIntervalRef.current);
                        heartbeatIntervalRef.current = null;
                    }

                    console.log(
                        "[WS] WebSocket disconnected, attempting to reconnect...",
                    );
                    // Attempt to reconnect after 3 seconds
                    reconnectTimeoutRef.current = setTimeout(connect, 3000);
                };

                wsRef.current = ws;
            } catch (error) {
                console.error("[WS] Failed to connect:", error);
                // Attempt to reconnect after 3 seconds
                reconnectTimeoutRef.current = setTimeout(connect, 3000);
            }
        };

        connect();

        return () => {
            if (reconnectTimeoutRef.current) {
                clearTimeout(reconnectTimeoutRef.current);
            }
            if (heartbeatIntervalRef.current) {
                clearInterval(heartbeatIntervalRef.current);
            }
            if (wsRef.current) {
                wsRef.current.close();
            }
        };
    }, [updateMetricsFromWebSocket]);

    return wsRef.current;
};

export default useWebSocket;
