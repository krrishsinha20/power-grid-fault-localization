import { useEffect, useMemo, useRef } from "react";
import { CircleMarker, MapContainer, TileLayer, Tooltip, useMap } from "react-leaflet";
import type { Incident } from "../types";
import type { PoleLookup } from "../hooks/usePoleLookup";

interface Props {
  incidents: Incident[];
  lookup: PoleLookup;
  selectedId: string | null;
  onSelect: (incidentId: string) => void;
}

const OPEN_STATUSES = new Set(["DETECTED", "ACKNOWLEDGED", "ASSIGNED", "IN_PROGRESS"]);

const faultColor: Record<string, string> = {
  SPAN_FAULT: "#f5a524",
  TRANSFORMER_FAULT: "#f0453a",
  FEEDER_FAULT: "#f0453a",
  SENSOR_FAILURE: "#5b8def",
  UNKNOWN: "#8b93a1",
};

// Bangalore -- matches the assignment's own example coordinates
// (00-candidate-brief.md: "12.9682° N 77.5946° E, PIN 560078") and
// network_generator.py's base_lat/base_lon.
const DEFAULT_CENTER: [number, number] = [12.9716, 77.5946];

/**
 * Nudges Leaflet to re-measure its container after any layout change
 * (e.g. the detail panel opening/closing resizes this pane). Lives
 * inside <MapContainer> so it can read react-leaflet's map instance
 * via useMap(). Renders nothing.
 */
function MapResizeHandler() {
  const map = useMap();

  useEffect(() => {
    const container = map.getContainer();
    const observer = new ResizeObserver(() => {
      requestAnimationFrame(() => map.invalidateSize());
    });
    observer.observe(container);
    requestAnimationFrame(() => map.invalidateSize());
    return () => observer.disconnect();
  }, [map]);

  return null;
}

/**
 * Recenters the map the first time real incident coordinates arrive,
 * without remounting <MapContainer>. IMPORTANT: this deliberately
 * does NOT use a `key` prop to force a remount on data changes --
 * react-leaflet's MapContainer does not tolerate being torn down and
 * recreated cleanly under React 18 StrictMode's dev-mode double-
 * invoke of effects, which produced a corrupted/duplicated map DOM.
 * Calling map.setView() imperatively avoids that entirely -- one
 * real Leaflet instance for the lifetime of this component, moved
 * rather than recreated.
 *
 * NOTE: an earlier version of this file also had a manual
 * `map.remove()` cleanup-on-unmount helper, added to fight a stale
 * dev-session map-stacking symptom. That was wrong: react-leaflet's
 * <MapContainer> already calls map.remove() itself on unmount, so
 * the extra manual call removed an already-removed map instance and
 * threw, crashing the whole app to a black screen. Removed --
 * <MapContainer>'s own lifecycle handling is sufficient.
 */
function MapRecenter({ center, enabled }: { center: [number, number]; enabled: boolean }) {
  const map = useMap();
  const hasCentered = useRef(false);

  useEffect(() => {
    if (enabled && !hasCentered.current) {
      map.setView(center, 13);
      hasCentered.current = true;
    }
  }, [enabled, center, map]);

  return null;
}

export function MapView({ incidents, lookup, selectedId, onSelect }: Props) {
  const points = useMemo(() => {
    return incidents
      .map((incident) => {
        const pole = lookup[incident.end_pole];
        const lat = incident.latitude ?? pole?.latitude;
        const lon = incident.longitude ?? pole?.longitude;
        if (lat == null || lon == null) return null;
        return { incident, lat, lon };
      })
      .filter((p): p is { incident: Incident; lat: number; lon: number } => p !== null);
  }, [incidents, lookup]);

  const firstPointCenter: [number, number] | null =
    points.length > 0 ? [points[0].lat, points[0].lon] : null;

  if (points.length === 0 && incidents.length > 0) {
    return (
      <div className="map-fallback">
        <p>Coordinates unavailable for current incidents.</p>
        <p className="text-muted">
          The pole registry hasn't loaded yet, or these poles aren't in it. See the incident list for
          full detail in the meantime.
        </p>
      </div>
    );
  }

  return (
    <div className="map-wrapper">
      <MapContainer center={DEFAULT_CENTER} zoom={12} className="map-container" scrollWheelZoom>
        <MapResizeHandler />
        {firstPointCenter && <MapRecenter center={firstPointCenter} enabled />}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {points.map(({ incident, lat, lon }) => {
          const isOpen = OPEN_STATUSES.has(incident.status);
          const color = faultColor[incident.fault_type] ?? faultColor.UNKNOWN;
          const isSelected = incident.incident_id === selectedId;
          return (
            <CircleMarker
              key={incident.incident_id}
              center={[lat, lon]}
              radius={isSelected ? 12 : 8}
              pathOptions={{
                color,
                fillColor: color,
                fillOpacity: isOpen ? 0.85 : 0.25,
                weight: isSelected ? 3 : 1.5,
                opacity: isOpen ? 1 : 0.4,
              }}
              eventHandlers={{ click: () => onSelect(incident.incident_id) }}
            >
              <Tooltip direction="top" offset={[0, -6]}>
                <div className="mono" style={{ fontSize: 12 }}>
                  <strong>{incident.incident_id}</strong>
                  <br />
                  {incident.fault_type} · {incident.affected_pole_count} poles
                </div>
              </Tooltip>
            </CircleMarker>
          );
        })}
      </MapContainer>
    </div>
  );
}