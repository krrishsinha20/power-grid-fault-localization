import type { Incident } from "../types";
import { ConfidenceMeter, FaultTypeBadge, PriorityDot, StatusBadge } from "./Badges";

interface Props {
  incidents: Incident[];
  selectedId: string | null;
  onSelect: (incidentId: string) => void;
}

const OPEN_STATUSES = new Set(["DETECTED", "ACKNOWLEDGED", "ASSIGNED", "IN_PROGRESS"]);

/**
 * Open incidents first (worst impact first), resolved ones pushed to
 * the bottom in a visually quieter state -- an operator working the
 * night shift should never have to scroll past closed tickets to find
 * the next thing that needs attention.
 */
function sortIncidents(incidents: Incident[]): Incident[] {
  return [...incidents].sort((a, b) => {
    const aOpen = OPEN_STATUSES.has(a.status);
    const bOpen = OPEN_STATUSES.has(b.status);
    if (aOpen !== bOpen) return aOpen ? -1 : 1;
    if (a.affected_pole_count !== b.affected_pole_count) {
      return b.affected_pole_count - a.affected_pole_count;
    }
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  });
}

export function IncidentList({ incidents, selectedId, onSelect }: Props) {
  const sorted = sortIncidents(incidents);

  if (sorted.length === 0) {
    return (
      <div className="empty-state">
        <p>No incidents.</p>
        <p className="text-muted">The grid is quiet. New faults will appear here the moment telemetry confirms one.</p>
      </div>
    );
  }

  return (
    <div className="incident-list">
      {sorted.map((incident) => {
        const isOpen = OPEN_STATUSES.has(incident.status);
        return (
          <button
            key={incident.incident_id}
            className={`incident-card ${incident.incident_id === selectedId ? "incident-card-selected" : ""} ${
              !isOpen ? "incident-card-resolved" : ""
            }`}
            onClick={() => onSelect(incident.incident_id)}
          >
            <div className="incident-card-top">
              <PriorityDot affectedPoles={incident.affected_pole_count} />
              <span className="mono incident-card-id">{incident.incident_id}</span>
              <StatusBadge status={incident.status} />
            </div>

            <div className="incident-card-mid">
              <FaultTypeBadge type={incident.fault_type} />
              <span className="text-muted">
                {incident.start_pole ? `${incident.start_pole} → ${incident.end_pole}` : incident.end_pole}
              </span>
            </div>

            <div className="incident-card-bottom">
              <span className="mono text-muted">
                {incident.affected_pole_count} pole{incident.affected_pole_count === 1 ? "" : "s"} · {incident.transformer_id} · {incident.feeder_id}
              </span>
              <ConfidenceMeter value={incident.confidence} />
            </div>
            <div className="incident-card-footer">
  <span className="view-details">
    View Details →
  </span>

  {incident.ai_summary ? (
    <span className="ai-chip">
      AI Analysis ✓
    </span>
  ) : (
    <span className="ai-chip pending">
      Explain with AI
    </span>
  )}
</div>
          </button>
        );
      })}
    </div>
  );
}
