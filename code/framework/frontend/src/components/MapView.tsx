import "leaflet/dist/leaflet.css";
import type { Snapshot } from "../types";
import { MapContainer, CircleMarker, Popup } from "react-leaflet";
import L from "leaflet";

type Props = {
    snapshot: Snapshot;
};

export function MapView({ snapshot }: Props) {
    const fogs = snapshot.fogs ?? [];
    const vehicles = snapshot.vehicles ?? [];

    const xs = [...fogs.map((f) => f.x), ...vehicles.map((v) => v.x)];
    const ys = [...fogs.map((f) => f.y), ...vehicles.map((v) => v.y)];
    const minX = Math.min(...xs, 0);
    const maxX = Math.max(...xs, 1000);
    const minY = Math.min(...ys, 0);
    const maxY = Math.max(...ys, 1000);

    const bounds: L.LatLngBoundsExpression = [
        [minY - 50, minX - 50],
        [maxY + 50, maxX + 50],
    ];

    return (
        <MapContainer
            bounds={bounds}
            crs={L.CRS.Simple}
            style={{ height: 520, width: "100%" }}
        >
            {fogs.map((f) => (
                <CircleMarker
                    key={f.id}
                    center={[f.y, f.x]}
                    radius={10}
                    pathOptions={{ className: "pcnme-fog-marker" }}
                >
                    <Popup>
                        <div>
                            <div>
                                <b>{f.id}</b>
                            </div>
                            <div>Load: {f.load.toFixed(2)}</div>
                            <div>Queue: {f.queue_depth}</div>
                        </div>
                    </Popup>
                </CircleMarker>
            ))}

            {vehicles.map((v) => (
                <CircleMarker
                    key={v.id}
                    center={[v.y, v.x]}
                    radius={4}
                    pathOptions={{ className: "pcnme-vehicle-marker" }}
                >
                    <Popup>
                        <div>
                            <div>
                                <b>{v.id}</b>
                            </div>
                            <div>Speed: {v.speed_ms.toFixed(1)} m/s</div>
                            <div>Fog: {v.connected_fog_id ?? "-"}</div>
                        </div>
                    </Popup>
                </CircleMarker>
            ))}
        </MapContainer>
    );
}
