export type Vehicle = {
    id: string;
    x: number;
    y: number;
    speed_ms: number;
    heading_deg: number;
    connected_fog_id?: string | null;
};

export type Fog = {
    id: string;
    x: number;
    y: number;
    load: number;
    queue_depth: number;
};

export type Metrics = {
    tasks_total: number;
    tasks_cloud: number;
    tasks_fog: number;
    packet_drops: number;
    avg_latency_ms: number;
    avg_energy: number;
};

export type Snapshot = {
    sim_time_s: number;
    vehicles: Vehicle[];
    fogs: Fog[];
    metrics: Metrics;
};

export type Envelope = {
    ts: string;
    state: Snapshot;
};
