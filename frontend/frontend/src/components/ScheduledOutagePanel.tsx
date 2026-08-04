import { useState } from "react";
import { api, ApiError } from "../api/client";
import { usePolling } from "../hooks/usePolling";
import type { ScheduledOutage } from "../types";
import { GlassSelect } from "./GlassSelect";

/**
 * CRUD panel for scheduled outages.
 *
 * Talks to:
 *   GET    /scheduled-outages            — list
 *   POST   /scheduled-outages            — create
 *   DELETE /scheduled-outages/{outage_id} — delete
 *
 * The "scope" field on creation is hardcoded to "feeder" (the most
 * common case). Transformer-scoped outages work identically but are
 * less common; a future iteration could add a scope selector.
 */

function formatDateTime(iso: string) {
  try {
    const d = new Date(iso);
    return d.toLocaleString("en-IN", {
      day: "2-digit",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });
  } catch {
    return iso;
  }
}

function outageStatusMeta(outage: ScheduledOutage): { label: string; color: string; bg: string } {
  const now = Date.now();
  const start = new Date(outage.start_time).getTime();
  const end = new Date(outage.end_time).getTime();
  if (now < start)  return { label: "Scheduled", color: "var(--medium)",  bg: "var(--medium-bg)"  };
  if (now <= end)   return { label: "Active",    color: "var(--critical)", bg: "var(--critical-bg)" };
  return               { label: "Completed",  color: "var(--text-faint)", bg: "var(--border-soft)" };
}

// Default start = now, end = now + 2h, formatted for <input type="datetime-local">
function toLocalInput(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

const FEEDER_OPTIONS = [
  { value: "F001" },
  { value: "F002" },
  { value: "F003" },
  { value: "F004" },
  { value: "F005" },
];

export function ScheduledOutagePanel() {
  const { data: outages, refresh } = usePolling(() => api.getScheduledOutages());

  // Create form state
  const [outageId,    setOutageId]    = useState("");
  const [feederId,    setFeederId]    = useState("F001");
  const [startTime,   setStartTime]   = useState(() => toLocalInput(new Date()));
  const [endTime,     setEndTime]     = useState(() => {
    const t = new Date();
    t.setHours(t.getHours() + 2);
    return toLocalInput(t);
  });
  const [reason,      setReason]      = useState("Planned maintenance");
  const [createError, setCreateError] = useState<string | null>(null);
  const [creating,    setCreating]    = useState(false);

  // Delete state
  const [deletingId,  setDeletingId]  = useState<string | null>(null);

  async function handleCreate() {
    if (!outageId || !feederId || !startTime || !endTime) return;
    setCreating(true);
    setCreateError(null);
    try {
      await api.createScheduledOutage({
        outage_id:    outageId.trim(),
        feeder_id:    feederId.trim(),
        transformer_id: null,
        start_time:   new Date(startTime).toISOString(),
        end_time:     new Date(endTime).toISOString(),
        reason:       reason.trim() || "Planned maintenance",
        status:       "SCHEDULED",
      });
      // Reset form
      setOutageId("");
      setReason("Planned maintenance");
      refresh();
    } catch (err) {
      setCreateError(err instanceof ApiError ? err.message : "Failed to create outage.");
    } finally {
      setCreating(false);
    }
  }

  async function handleDelete(id: string) {
    setDeletingId(id);
    try {
      await api.deleteScheduledOutage(id);
      refresh();
    } finally {
      setDeletingId(null);
    }
  }

  const list = outages ?? [];

  return (
    <div className="network-layout">
      <div className="network-grid">

        {/* ---- Outage list ---- */}
        <div className="panel-card">
          <div className="panel-card-header">
            <span className="panel-card-title">
              📅 Scheduled Outages
            </span>
            <span className="text-faint" style={{ fontSize: 11 }}>
              {list.length} record{list.length !== 1 ? "s" : ""}
            </span>
          </div>
          <div className="panel-card-body">
            {list.length === 0 ? (
              <div className="empty-state">
                <div className="empty-state-icon">🟢</div>
                <p>No scheduled outages.</p>
                <p className="text-faint" style={{ fontSize: 12 }}>
                  Create one on the right to suppress fault alerts during planned maintenance.
                </p>
              </div>
            ) : (
              <div className="outage-list">
                {list.map((o) => {
                  const meta = outageStatusMeta(o);
                  return (
                    <div key={o.outage_id} className="outage-item">
                      <div className="outage-item-info">
                        <div className="outage-item-id">{o.outage_id}</div>
                        <div className="outage-item-scope">
                          <span
                            className="outage-status-badge"
                            style={{ color: meta.color, background: meta.bg, borderColor: meta.color, marginRight: 6 }}
                          >
                            {meta.label}
                          </span>
                          {o.feeder_id}
                          {o.transformer_id ? ` / ${o.transformer_id}` : ""}
                        </div>
                        <div className="outage-item-reason">{o.reason}</div>
                        <div className="outage-item-time">
                          {formatDateTime(o.start_time)} → {formatDateTime(o.end_time)}
                        </div>
                      </div>
                      <button
                        className="outage-delete-btn"
                        title="Delete outage"
                        disabled={deletingId === o.outage_id}
                        onClick={() => handleDelete(o.outage_id)}
                      >
                        {deletingId === o.outage_id ? "…" : "✕"}
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* ---- Create form ---- */}
        <div className="panel-card">
          <div className="panel-card-header">
            <span className="panel-card-title">➕ Create Scheduled Outage</span>
          </div>
          <div className="panel-card-body">
            <p style={{ fontSize: 12, color: "var(--text-faint)", marginBottom: 14, marginTop: 0 }}>
              Outages registered here suppress fault alerts for the targeted feeder during the
              scheduled window. The system will still detect real faults but will not raise tickets
              if they coincide with a known planned shutdown.
            </p>
            <div className="outage-form">
              <div className="form-row">
                <label className="form-label">
                  Outage ID
                  <input
                    className="form-input"
                    value={outageId}
                    onChange={e => setOutageId(e.target.value)}
                    placeholder="SO-2026-08-05-001"
                  />
                </label>
                <label className="form-label">
                  Feeder ID
                  <GlassSelect
                    value={feederId}
                    options={FEEDER_OPTIONS}
                    onChange={setFeederId}
                    placeholder="— select feeder —"
                  />
                </label>
              </div>

              <div className="form-row">
                <label className="form-label">
                  Start time
                  <input
                    type="datetime-local"
                    className="form-input"
                    value={startTime}
                    onChange={e => setStartTime(e.target.value)}
                  />
                </label>
                <label className="form-label">
                  End time
                  <input
                    type="datetime-local"
                    className="form-input"
                    value={endTime}
                    onChange={e => setEndTime(e.target.value)}
                  />
                </label>
              </div>

              <label className="form-label">
                Reason
                <input
                  className="form-input"
                  value={reason}
                  onChange={e => setReason(e.target.value)}
                  placeholder="Planned maintenance"
                />
              </label>

              {createError && <p className="error-text">{createError}</p>}

              <div className="form-actions">
                <button
                  className="btn-primary"
                  disabled={creating || !outageId || !feederId}
                  onClick={handleCreate}
                >
                  {creating ? "Creating…" : "Create outage"}
                </button>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
