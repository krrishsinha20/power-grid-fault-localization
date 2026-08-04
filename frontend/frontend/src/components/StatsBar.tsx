import { useEffect, useState } from "react";
import type { DashboardStats } from "../types";

interface Props {
  stats: DashboardStats | null;
  lastUpdated: Date | null;
}

/**
 * The signature element of this console: a single horizontal strip
 * that reads like a real annunciator panel's summary line. The bar
 * itself IS the fleet — a segmented live/dark ratio, not a chart of
 * it — so the operator's eye lands on "how much of the grid is dark
 * right now" before it lands on anything else.
 *
 * Additions over v1:
 * - Live wall clock so an operator at 2 a.m. always knows the time
 * - Flashing "N ACTIVE FAULTS" badge on the right when alarms are present
 */
export function StatsBar({ stats, lastUpdated }: Props) {
  const healthyRatio = stats ? stats.healthy_poles / Math.max(1, stats.total_poles) : 1;
  const hasActiveIncidents = (stats?.active_incidents ?? 0) > 0;

  // Live wall clock — ticks every second
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  const clockStr = now.toLocaleTimeString("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });

  return (
    <div className="stats-bar">
      {/* Fleet health bar */}
      <div
        className="grid-pulse"
        title={`${Math.round(healthyRatio * 100)}% of poles energized`}
      >
        <div
          className="grid-pulse-fill"
          style={{
            width: `${healthyRatio * 100}%`,
            background: hasActiveIncidents ? "var(--critical)" : "var(--healthy)",
          }}
        >
          {hasActiveIncidents && <span className="grid-pulse-dot" />}
        </div>
      </div>

      <div className="stats-divider" />

      <div className="stats-cells">
        <StatCell label="Poles"     value={stats?.total_poles} />
        <StatCell label="Energized" value={stats?.healthy_poles} tone="healthy" />
        <StatCell
          label="Dark"
          value={stats?.faulty_poles}
          tone={stats && stats.faulty_poles > 0 ? "critical" : undefined}
        />
        <StatCell
          label="Active Faults"
          value={stats?.active_incidents}
          tone={hasActiveIncidents ? "critical" : undefined}
          emphasize
        />
        <StatCell label="Open Tickets" value={stats?.open_tickets} />
      </div>

      {/* Right side: active fault flash + clock */}
      <div className="stats-right">
        <span className="stats-clock mono">{clockStr}</span>
        {lastUpdated ? (
          <span className="stats-updated">
            synced {lastUpdated.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false })}
          </span>
        ) : (
          <span className="stats-updated">connecting…</span>
        )}
      </div>

      {hasActiveIncidents && (
        <span className="critical-flash">
          ⚡ {stats!.active_incidents} ACTIVE FAULT{stats!.active_incidents > 1 ? "S" : ""}
        </span>
      )}
    </div>
  );
}

function StatCell({
  label,
  value,
  tone,
  emphasize,
}: {
  label: string;
  value?: number;
  tone?: "healthy" | "critical";
  emphasize?: boolean;
}) {
  const color =
    tone === "critical"
      ? "var(--critical)"
      : tone === "healthy"
      ? "var(--healthy)"
      : "var(--text)";
  return (
    <div className={`stat-cell ${emphasize ? "stat-cell-emphasize" : ""}`}>
      <span className="stat-value mono" style={{ color }}>
        {value ?? "–"}
      </span>
      <span className="stat-label">{label}</span>
    </div>
  );
}
