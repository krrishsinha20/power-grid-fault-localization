import { useState, type ReactNode } from "react";
import type { Incident, Ticket } from "../types";
import type { PoleLookup } from "../hooks/usePoleLookup";
import { FaultTypeBadge, StatusBadge, ConfidenceMeter } from "./Badges";
import { api, ApiError } from "../api/client";

interface Props {
  incident: Incident;
  ticket: Ticket | undefined;
  lookup: PoleLookup;
  onClose: () => void;
  onChanged: () => void;
}

const NEXT_TICKET_STATUS: Record<string, string | null> = {
  OPEN: "ACKNOWLEDGED",
  ACKNOWLEDGED: "ASSIGNED",
  ASSIGNED: "IN_PROGRESS",
  IN_PROGRESS: null, // from here, only telemetry (repair) verifies + closes
};

const NEXT_LABEL: Record<string, string> = {
  ACKNOWLEDGED: "Acknowledge",
  ASSIGNED: "Mark crew assigned",
  IN_PROGRESS: "Mark in progress",
};

function confidenceExplanation(incident: Incident): string {
  if (incident.confidence >= 95) {
    return "Both boundary poles have working telemetry and this transformer's wiring order is on record. This location is as precise as the system can report.";
  }
  if (incident.confidence >= 80) {
    return "Minor uncertainty — likely a small number of stale or missing readings nearby, not a location problem.";
  }
  if (incident.confidence >= 60) {
    return "This transformer's pole order was inferred from GPS positions rather than read from a survey record, or the fault boundary sits behind a pole with no telemetry device. Treat the span as a close estimate, not a confirmed point — worth a visual check on arrival.";
  }
  return "Low confidence: multiple compounding gaps (inferred wiring, missing devices, or stale telemetry). Dispatch can proceed, but expect to widen the search at the site.";
}

export function IncidentDetail({ incident, ticket, lookup, onClose, onChanged }: Props) {
  const [explaining, setExplaining] = useState(false);
  const [explainError, setExplainError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [showForceClose, setShowForceClose] = useState(false);

  const pole = lookup[incident.end_pole];
  const lat = incident.latitude ?? pole?.latitude;
  const lon = incident.longitude ?? pole?.longitude;
  const pincode = incident.pincode ?? pole?.pincode;

  const nextTicketStatus = ticket ? NEXT_TICKET_STATUS[ticket.status] : undefined;

  async function handleExplain() {
    setExplaining(true);
    setExplainError(null);
    try {
      await api.explainIncident(incident.incident_id);
      onChanged();
    } catch (err) {
      setExplainError(
        err instanceof ApiError
          ? "AI explanation is unavailable right now. The incident and ticket are unaffected."
          : "Something went wrong requesting the explanation."
      );
    } finally {
      setExplaining(false);
    }
  }

  async function handleAdvanceTicket() {
    if (!ticket || !nextTicketStatus) return;
    setBusy(true);
    try {
      await api.updateTicketStatus(ticket.ticket_id, nextTicketStatus);
      onChanged();
    } finally {
      setBusy(false);
    }
  }

  async function handleForceClose() {
    if (!ticket) return;
    setBusy(true);
    try {
      await api.forceCloseTicket(ticket.ticket_id);
      onChanged();
      setShowForceClose(false);
    } finally {
      setBusy(false);
    }
  }

  const isResolved = incident.status === "VERIFIED" || incident.status === "CLOSED";

  return (
    <div className="detail-panel">
      <div className="detail-header">
        <div>
          <span className="mono detail-id">{incident.incident_id}</span>
          <div className="detail-badges">
            <FaultTypeBadge type={incident.fault_type} />
            <StatusBadge status={incident.status} />
          </div>
        </div>
        <button className="btn-icon" onClick={onClose} aria-label="Close detail panel">
          ✕
        </button>
      </div>

      {/* Moved to the top, right under the badges -- reachable without
          scrolling, since it's one of the two things (location being
          the other) an operator actually needs first. */}
      <section className="detail-section">
        <h3>AI analysis</h3>
        {incident.ai_summary ? (
          <div className="ai-block">
            <p>{incident.ai_summary}</p>
            {incident.root_cause && (
              <>
                <h4>Probable root cause</h4>
                <p className="text-muted">{incident.root_cause}</p>
              </>
            )}
            {incident.recommended_action && (
              <>
                <h4>Recommended action</h4>
                <p className="text-muted">{incident.recommended_action}</p>
              </>
            )}
          </div>
        ) : (
          <div>
            <p className="text-muted">
              Not requested yet. This never runs automatically — fault detection and ticketing stay
              fully deterministic whether or not the AI model is available.
            </p>
            <button className="btn-secondary" onClick={handleExplain} disabled={explaining}>
              {explaining ? "Asking…" : "Explain this fault"}
            </button>
            {explainError && <p className="error-text">{explainError}</p>}
          </div>
        )}
      </section>

      <section className="detail-section">
        <h3>Location</h3>
        <div className="detail-grid">
          <Field label="Span">
            {incident.start_pole ? `${incident.start_pole} → ${incident.end_pole}` : incident.end_pole}
          </Field>
          <Field label="Coordinates">
            {lat != null && lon != null ? `${lat.toFixed(5)}, ${lon.toFixed(5)}` : "Unavailable"}
          </Field>
          <Field label="PIN code">{pincode ?? "Unavailable"}</Field>
          <Field label="Transformer">{incident.transformer_id}</Field>
          <Field label="Feeder">{incident.feeder_id}</Field>
          <Field label="Affected poles">{incident.affected_pole_count}</Field>
        </div>
      </section>

      <section className="detail-section">
        <h3>Confidence</h3>
        <ConfidenceMeter value={incident.confidence} />
        <p className="text-muted detail-explain-text">{confidenceExplanation(incident)}</p>
      </section>

      <section className="detail-section">
        <h3>Ticket workflow</h3>
        {ticket ? (
          <>
            <div className="detail-grid">
              <Field label="Ticket">{ticket.ticket_id}</Field>
              <Field label="Priority">{ticket.priority}</Field>
              <Field label="Status">
                <StatusBadge status={ticket.status} />
              </Field>
              <Field label="Assigned to">{ticket.assigned_to ?? "Unassigned"}</Field>
            </div>

            {ticket.remarks && <p className="text-muted detail-remarks">{ticket.remarks}</p>}

            {!isResolved && (
              <div className="detail-actions">
                {nextTicketStatus && (
                  <button className="btn-primary" onClick={handleAdvanceTicket} disabled={busy}>
                    {NEXT_LABEL[nextTicketStatus]}
                  </button>
                )}
                {ticket.status === "IN_PROGRESS" && (
                  <p className="text-muted detail-hint">
                    Waiting on telemetry. This ticket closes on its own once the affected poles report
                    energized again — repair it in the simulator, or wait for real restoration telemetry.
                  </p>
                )}
              </div>
            )}

            {isResolved && (
              <p className="text-muted">
                {incident.status === "VERIFIED"
                  ? "Verified from telemetry — the affected poles are confirmed energized again."
                  : "Closed."}
              </p>
            )}

            {!isResolved && (
              <div className="force-close-block">
                <button className="btn-link-danger" onClick={() => setShowForceClose((v) => !v)}>
                  Admin override: force-close without verification
                </button>
                {showForceClose && (
                  <div className="force-close-confirm">
                    <p className="text-muted">
                      This closes the ticket immediately without checking telemetry. Use only if you know
                      the ticket is wrong (e.g. a duplicate) — never as a substitute for repair
                      verification.
                    </p>
                    <button className="btn-danger" onClick={handleForceClose} disabled={busy}>
                      Force close anyway
                    </button>
                  </div>
                )}
              </div>
            )}
          </>
        ) : (
          <p className="text-muted">No ticket found for this incident.</p>
        )}
      </section>

      <section className="detail-section">
        <h3>Affected poles ({incident.affected_pole_ids.length})</h3>
        <div className="pole-chip-list mono">
          {incident.affected_pole_ids.map((id) => (
            <span key={id} className="pole-chip">
              {id}
            </span>
          ))}
        </div>
      </section>
    </div>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="detail-field">
      <span className="detail-field-label">{label}</span>
      <span className="detail-field-value mono">{children}</span>
    </div>
  );
}