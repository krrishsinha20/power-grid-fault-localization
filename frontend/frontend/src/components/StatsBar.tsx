import type { DashboardStats } from "../types";

interface Props {
  stats: DashboardStats | null;
  lastUpdated: Date | null;
}

/**
 * The signature element of this console: a single horizontal strip
 * that reads like a real annunciator panel's summary line. The bar
 * itself IS the fleet -- a segmented live/dark ratio, not a chart of
 * it -- so the operator's eye lands on "how much of the grid is dark
 * right now" before it lands on anything else, per the brief's ask
 * for the most important thing to dominate the screen.
 */
export function StatsBar({ stats, lastUpdated }: Props) {
  const healthyRatio = stats ? stats.healthy_poles / Math.max(1, stats.total_poles) : 1;
  const hasActiveIncidents = (stats?.active_incidents ?? 0) > 0;

  return (
    <div className="stats-bar">
      <div className="grid-pulse" title={`${Math.round(healthyRatio * 100)}% of poles energized`}>
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

      <div className="stats-cells">
        <StatCell label="Poles" value={stats?.total_poles} />
        <StatCell label="Energized" value={stats?.healthy_poles} tone="healthy" />
        <StatCell
          label="Dark"
          value={stats?.faulty_poles}
          tone={stats && stats.faulty_poles > 0 ? "critical" : undefined}
        />
        <StatCell
          label="Active incidents"
          value={stats?.active_incidents}
          tone={hasActiveIncidents ? "critical" : undefined}
          emphasize
        />
        <StatCell label="Open tickets" value={stats?.open_tickets} />
      </div>

      <div className="stats-updated mono">
        {lastUpdated ? `updated ${lastUpdated.toLocaleTimeString()}` : "connecting…"}
      </div>
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
    tone === "critical" ? "var(--critical)" : tone === "healthy" ? "var(--healthy)" : "var(--text)";
  return (
    <div className={`stat-cell ${emphasize ? "stat-cell-emphasize" : ""}`}>
      <span className="stat-value mono" style={{ color }}>
        {value ?? "–"}
      </span>
      <span className="stat-label">{label}</span>
    </div>
  );
}
