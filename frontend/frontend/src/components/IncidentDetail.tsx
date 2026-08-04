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
  OPEN:        "ACKNOWLEDGED",
  ACKNOWLEDGED:"ASSIGNED",
  ASSIGNED:    "IN_PROGRESS",
  IN_PROGRESS: null, // from here, only telemetry (repair) verifies + closes
};

const NEXT_LABEL: Record<string, string> = {
  ACKNOWLEDGED: "Acknowledge",
  ASSIGNED:     "Mark crew assigned",
  IN_PROGRESS:  "Mark in progress",
};

function confidenceExplanation(incident: Incident): string {
  if (incident.confidence >= 95) {
    return "Both boundary poles have working telemetry and this transformer's wiring order is on record. This location is as precise as the system can report.";
  }
  if (incident.confidence >= 80) {
    return "Minor uncertainty — likely a small number of stale or missing readings nearby, not a location problem.";
  }
  if (incident.confidence >= 60) {
    return "This transformer's pole order was inferred from GPS positions rather than read from a survey record, or the fault boundary sits behind a pole with no telemetry device. Treat the span as a close estimate — worth a visual check on arrival.";
  }
  return "Low confidence: multiple compounding gaps (inferred wiring, missing devices, or stale telemetry). Dispatch can proceed, but expect to widen the search at the site.";
}

export function IncidentDetail({ incident, ticket, lookup, onClose, onChanged }: Props) {
  const [explaining,      setExplaining]      = useState(false);
  const [explainError,    setExplainError]    = useState<string | null>(null);
  const [busy,            setBusy]            = useState(false);
  const [showForceClose,  setShowForceClose]  = useState(false);

  const pole = lookup[incident.end_pole];
  const lat = incident.latitude ?? pole?.latitude;
  const lon = incident.longitude ?? pole?.longitude;
  const pincode = incident.pincode ?? pole?.pincode;

  const nextTicketStatus = ticket ? NEXT_TICKET_STATUS[ticket.status] : undefined;
  const isResolved = incident.status === "VERIFIED" || incident.status === "CLOSED";

  // Google Maps navigation URL — opens directly in the device's nav app
  const navUrl =
    lat != null && lon != null
      ? `https://maps.google.com/?q=${lat.toFixed(6)},${lon.toFixed(6)}`
      : null;

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

  return (
    <div className="detail-panel">
      {/* ---- Header ---- */}
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

      {/* ---- Location (operator's first need) ---- */}
      <section className="detail-section">
        <h3>Location</h3>
        <div className="detail-grid">
          <Field label="Fault span">
            {incident.start_pole
              ? `${incident.start_pole} → ${incident.end_pole}`
              : incident.end_pole}
          </Field>
          <Field label="Coordinates">
            {lat != null && lon != null
              ? `${lat.toFixed(5)}, ${lon.toFixed(5)}`
              : "Unavailable"}
          </Field>
          <Field label="PIN code">{pincode ?? "Unavailable"}</Field>
          <Field label="Transformer">{incident.transformer_id}</Field>
          <Field label="Feeder">{incident.feeder_id}</Field>
          <Field label="Affected poles">{incident.affected_pole_count}</Field>
        </div>

        {/* Navigate button — opens Google Maps at the fault coordinates */}
        {navUrl && (
          <div style={{ marginTop: 12 }}>
            <a
              href={navUrl}
              target="_blank"
              rel="noreferrer"
              className="btn-navigate"
            >
              🗺 Navigate to fault →
            </a>
          </div>
        )}
      </section>

      {/* ---- Confidence ---- */}
      <section className="detail-section">
        <h3>Confidence</h3>
        <ConfidenceMeter value={incident.confidence} />
        <p className="text-muted detail-explain-text">{confidenceExplanation(incident)}</p>
      </section>

      {/* ---- AI analysis ---- */}
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
            <p className="text-muted" style={{ fontSize: 12, marginTop: 0 }}>
              Not requested yet. Fault detection and ticketing stay fully deterministic whether
              or not the AI model is available.
            </p>
            <button className="btn-secondary" onClick={handleExplain} disabled={explaining}>
              {explaining ? "Asking…" : "Explain this fault"}
            </button>
            {explainError && <p className="error-text" style={{ marginTop: 6 }}>{explainError}</p>}
          </div>
        )}
      </section>

      {/* ---- Ticket workflow ---- */}
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

            {ticket.remarks && (
              <p className="text-muted detail-remarks">{ticket.remarks}</p>
            )}

            {!isResolved && (
              <div className="detail-actions">
                {nextTicketStatus && (
                  <button
                    className="btn-primary"
                    onClick={handleAdvanceTicket}
                    disabled={busy}
                  >
                    {NEXT_LABEL[nextTicketStatus]}
                  </button>
                )}
                {ticket.status === "IN_PROGRESS" && (
                  <p className="text-muted detail-hint">
                    Waiting on telemetry. This ticket closes automatically once the affected poles
                    report energized again — repair it in the simulator, or wait for real
                    restoration telemetry.
                  </p>
                )}
              </div>
            )}

            {isResolved && (
              <p className="text-muted" style={{ fontSize: 12 }}>
                {incident.status === "VERIFIED"
                  ? "✅ Verified from telemetry — the affected poles are confirmed energized again."
                  : "Closed."}
              </p>
            )}

            {!isResolved && (
              <div className="force-close-block">
                <button
                  className="btn-link-danger"
                  onClick={() => setShowForceClose(v => !v)}
                >
                  Admin override: force-close without verification
                </button>
                {showForceClose && (
                  <div className="force-close-confirm">
                    <p className="text-muted">
                      This closes the ticket immediately without checking telemetry. Use only if
                      you know the ticket is wrong (e.g. a duplicate) — never as a substitute for
                      repair verification.
                    </p>
                    <button
                      className="btn-danger"
                      onClick={handleForceClose}
                      disabled={busy}
                    >
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

      {/* ---- Affected poles ---- */}
      <section className="detail-section">
        <h3>Affected poles ({incident.affected_pole_ids.length})</h3>
        <div className="pole-chip-list mono">
          {incident.affected_pole_ids.map(id => (
            <span key={id} className="pole-chip">{id}</span>
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