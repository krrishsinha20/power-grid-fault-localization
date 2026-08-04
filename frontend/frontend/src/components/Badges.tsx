import type { FaultType, IncidentStatus, TicketStatus } from "../types";

const faultTypeMeta: Record<
  FaultType,
  { label: string; color: string; bg: string }
> = {
  SPAN_FAULT: { label: "Span fault", color: "var(--high)", bg: "var(--high-bg)" },
  TRANSFORMER_FAULT: {
    label: "Transformer fault",
    color: "var(--critical)",
    bg: "var(--critical-bg)",
  },
  FEEDER_FAULT: {
    label: "Feeder fault",
    color: "var(--critical)",
    bg: "var(--critical-bg)",
  },
  SENSOR_FAILURE: {
    label: "Sensor failure",
    color: "var(--low)",
    bg: "var(--low-bg)",
  },
  UNKNOWN: { label: "Unknown", color: "var(--text-muted)", bg: "var(--border-soft)" },
};

export function FaultTypeBadge({ type }: { type: FaultType }) {
  const meta = faultTypeMeta[type] ?? faultTypeMeta.UNKNOWN;
  return (
    <span
      className="badge"
      style={{ color: meta.color, background: meta.bg, borderColor: meta.color }}
    >
      {meta.label}
    </span>
  );
}

const statusMeta: Record<string, { label: string; color: string; bg: string }> = {
  DETECTED: { label: "Detected", color: "var(--critical)", bg: "var(--critical-bg)" },
  ACKNOWLEDGED: { label: "Acknowledged", color: "var(--high)", bg: "var(--high-bg)" },
  ASSIGNED: { label: "Crew assigned", color: "var(--medium)", bg: "var(--medium-bg)" },
  IN_PROGRESS: { label: "In progress", color: "var(--medium)", bg: "var(--medium-bg)" },
  OPEN: { label: "Open", color: "var(--critical)", bg: "var(--critical-bg)" },
  VERIFIED: { label: "Verified", color: "var(--healthy)", bg: "var(--healthy-bg)" },
  CLOSED: { label: "Closed", color: "var(--text-muted)", bg: "var(--border-soft)" },
};

export function StatusBadge({ status }: { status: IncidentStatus | TicketStatus | string }) {
  const meta = statusMeta[status] ?? {
    label: status,
    color: "var(--text-muted)",
    bg: "var(--border-soft)",
  };
  return (
    <span
      className="badge"
      style={{ color: meta.color, background: meta.bg, borderColor: meta.color }}
    >
      {meta.label}
    </span>
  );
}

export function ConfidenceMeter({ value }: { value: number }) {
  const color =
    value >= 90 ? "var(--healthy)" : value >= 70 ? "var(--medium)" : "var(--high)";
  return (
    <div className="confidence-meter" title={`${value}% confidence`}>
      <div className="confidence-track">
        <div
          className="confidence-fill"
          style={{ width: `${Math.max(0, Math.min(100, value))}%`, background: color }}
        />
      </div>
      <span className="mono confidence-label" style={{ color }}>
        {value}%
      </span>
    </div>
  );
}

export function PriorityDot({ affectedPoles }: { affectedPoles: number }) {
  let color = "var(--low)";
  if (affectedPoles >= 50) color = "var(--critical)";
  else if (affectedPoles >= 20) color = "var(--high)";
  else if (affectedPoles >= 5) color = "var(--medium)";
  return <span className="priority-dot" style={{ background: color }} />;
}
