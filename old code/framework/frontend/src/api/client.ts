const API_BASE = import.meta.env.VITE_API_BASE ?? "";

export async function getJson<T>(path: string): Promise<T> {
    const res = await fetch(`${API_BASE}${path}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return (await res.json()) as T;
}

export async function postJson<T>(path: string): Promise<T> {
    const res = await fetch(`${API_BASE}${path}`, { method: "POST" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return (await res.json()) as T;
}

export function wsUrl(): string {
    const explicit = import.meta.env.VITE_WS_URL;
    if (explicit) return String(explicit);

    const apiBase = import.meta.env.VITE_API_BASE;
    if (apiBase) return `${String(apiBase).replace(/^http/, "ws")}/ws/stream`;

    const origin = window.location.origin.replace(/^http/, "ws");
    return `${origin}/ws/stream`;
}
