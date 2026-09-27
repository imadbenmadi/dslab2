import { create } from "zustand";
import type { Envelope, Snapshot } from "../types";

type StreamState = {
    connected: boolean;
    lastTs?: string;
    snapshot?: Snapshot;
    setConnected: (v: boolean) => void;
    setEnvelope: (env: Envelope) => void;
    setSnapshot: (s: Snapshot) => void;
};

export const useStreamStore = create<StreamState>((set) => ({
    connected: false,
    setConnected: (v) => set({ connected: v }),
    setEnvelope: (env) => set({ lastTs: env.ts, snapshot: env.state }),
    setSnapshot: (s) => set({ snapshot: s }),
}));
