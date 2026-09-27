import { useEffect, useRef } from "react";
import { wsUrl } from "../api/client";
import type { Envelope } from "../types";
import { useStreamStore } from "../state/store";

export function useStream() {
    const setConnected = useStreamStore((s) => s.setConnected);
    const setEnvelope = useStreamStore((s) => s.setEnvelope);
    const wsRef = useRef<WebSocket | null>(null);

    useEffect(() => {
        let cancelled = false;

        function connect() {
            if (cancelled) return;
            const ws = new WebSocket(wsUrl());
            wsRef.current = ws;

            ws.onopen = () => setConnected(true);
            ws.onclose = () => {
                setConnected(false);
                if (!cancelled) setTimeout(connect, 800);
            };
            ws.onerror = () => {
                setConnected(false);
                try {
                    ws.close();
                } catch {
                    // ignore
                }
            };
            ws.onmessage = (ev) => {
                try {
                    const parsed = JSON.parse(String(ev.data)) as any;
                    if (parsed && parsed.state) {
                        setEnvelope(parsed as Envelope);
                    } else if (parsed && parsed.vehicles && parsed.fogs) {
                        setEnvelope({
                            ts: new Date().toISOString(),
                            state: parsed,
                        });
                    }
                } catch {
                    // ignore parse errors
                }
            };
        }

        connect();
        return () => {
            cancelled = true;
            try {
                wsRef.current?.close();
            } catch {
                // ignore
            }
            wsRef.current = null;
        };
    }, [setConnected, setEnvelope]);
}
