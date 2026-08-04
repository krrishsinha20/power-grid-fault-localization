import { useState, type ReactNode } from "react";
import { api, ApiError } from "../api/client";

interface LogEntry {
  time: string;
  message: string;
  ok: boolean;
}

interface Props {
  onAction: () => void;
}

/**
 * The fault simulator required by the brief. Every action here calls
 * the backend's /simulate/* endpoints directly and writes a one-line
 * result into a running log, so a reviewer can watch cause and effect
 * without switching to Swagger. `onAction` triggers an immediate
 * refresh of the console's incident/ticket data instead of waiting
 * for the next poll tick.
 */
export function SimulatorPanel({ onAction }: Props) {
  const [log, setLog] = useState<LogEntry[]>([]);
  const [busy, setBusy] = useState(false);

  const [poleIdsInput, setPoleIdsInput] = useState("");
  const [transformerId, setTransformerId] = useState("");
  const [feederId, setFeederId] = useState("");
  const [singlePoleId, setSinglePoleId] = useState("");
  const [repeatCount, setRepeatCount] = useState(5);

  function parsePoleIds(input: string): string[] {
    return input
      .split(/[\s,]+/)
      .map((s) => s.trim())
      .filter(Boolean);
  }

  async function run(label: string, action: () => Promise<{ success: boolean; message: string }>) {
    setBusy(true);
    try {
      const result = await action();
      setLog((prev) => [
        { time: new Date().toLocaleTimeString(), message: `${label}: ${result.message}`, ok: result.success },
        ...prev,
      ].slice(0, 30));
      onAction();
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Request failed.";
      setLog((prev) => [
        { time: new Date().toLocaleTimeString(), message: `${label}: ${message}`, ok: false },
        ...prev,
      ].slice(0, 30));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="simulator-panel">
      <div className="simulator-grid">
        <SimCard title="Network" description="Seed or regenerate the synthetic pole/transformer registry.">
          <button className="btn-secondary" disabled={busy} onClick={() => run("Generate network", () => api.generateNetwork(false))}>
            Ensure network exists
          </button>
          <button className="btn-danger" disabled={busy} onClick={() => run("Reset network", () => api.generateNetwork(true))}>
            Reset network (destructive)
          </button>
        </SimCard>

        <SimCard title="Span fault" description="Dark two or more adjacent poles — the core fault type.">
          <label className="sim-label">
            Pole IDs (space or comma separated)
            <input
              className="sim-input mono"
              value={poleIdsInput}
              onChange={(e) => setPoleIdsInput(e.target.value)}
              placeholder="P00023 P00024 P00025"
            />
          </label>
          <button
            className="btn-primary"
            disabled={busy || parsePoleIds(poleIdsInput).length === 0}
            onClick={() => run("Span fault", () => api.injectSpanFault(parsePoleIds(poleIdsInput)))}
          >
            Inject span fault
          </button>
          <button
            className="btn-secondary"
            disabled={busy || parsePoleIds(poleIdsInput).length === 0}
            onClick={() => run("Repair", () => api.repairFault(parsePoleIds(poleIdsInput)))}
          >
            Repair these poles
          </button>
        </SimCard>

        <SimCard title="Transformer fault" description="Every pole under one DT goes dark at once.">
          <label className="sim-label">
            Transformer ID
            <input
              className="sim-input mono"
              value={transformerId}
              onChange={(e) => setTransformerId(e.target.value)}
              placeholder="DT0003"
            />
          </label>
          <button
            className="btn-primary"
            disabled={busy || !transformerId}
            onClick={() => run("Transformer fault", () => api.injectTransformerFault(transformerId))}
          >
            Inject transformer fault
          </button>
        </SimCard>

        <SimCard title="Feeder fault" description="Every transformer on the feeder goes dark — grouped into one incident.">
          <label className="sim-label">
            Feeder ID
            <input
              className="sim-input mono"
              value={feederId}
              onChange={(e) => setFeederId(e.target.value)}
              placeholder="F002"
            />
          </label>
          <div className="sim-button-row">
            <button
              className="btn-primary"
              disabled={busy || !feederId}
              onClick={() => run("Feeder fault", () => api.injectFeederFault(feederId))}
            >
              Inject feeder fault
            </button>
            <button
              className="btn-secondary"
              disabled={busy || !feederId}
              onClick={() => run("Repair feeder", () => api.repairFeeder(feederId))}
            >
              Repair feeder
            </button>
          </div>
        </SimCard>

        <SimCard title="Noise: dead sensor" description="Device goes silent while power stays on — must NOT create an outage ticket.">
          <label className="sim-label">
            Pole ID
            <input
              className="sim-input mono"
              value={singlePoleId}
              onChange={(e) => setSinglePoleId(e.target.value)}
              placeholder="P00045"
            />
          </label>
          <button
            className="btn-secondary"
            disabled={busy || !singlePoleId}
            onClick={() => run("Sensor failure", () => api.simulateSensorFailure(singlePoleId))}
          >
            Kill sensor (power stays on)
          </button>
        </SimCard>

        <SimCard title="Noise: duplicate telemetry" description="Same packet resent several times — must apply exactly one state change.">
          <label className="sim-label">
            Pole ID
            <input className="sim-input mono" value={singlePoleId} onChange={(e) => setSinglePoleId(e.target.value)} placeholder="P00045" />
          </label>
          <label className="sim-label">
            Repeat count
            <input
              className="sim-input mono"
              type="number"
              min={2}
              max={20}
              value={repeatCount}
              onChange={(e) => setRepeatCount(Number(e.target.value))}
            />
          </label>
          <button
            className="btn-secondary"
            disabled={busy || !singlePoleId}
            onClick={() => run("Duplicate telemetry", () => api.simulateDuplicateTelemetry(singlePoleId, repeatCount))}
          >
            Send duplicates
          </button>
        </SimCard>

        <SimCard title="Noise: out-of-order telemetry" description="A stale 'restored' packet arrives after a newer 'lost' packet — must not win.">
          <label className="sim-label">
            Pole ID
            <input className="sim-input mono" value={singlePoleId} onChange={(e) => setSinglePoleId(e.target.value)} placeholder="P00045" />
          </label>
          <button
            className="btn-secondary"
            disabled={busy || !singlePoleId}
            onClick={() => run("Out-of-order telemetry", () => api.simulateOutOfOrder(singlePoleId))}
          >
            Send out-of-order packets
          </button>
        </SimCard>
      </div>

      <div className="sim-log">
        <h3>Activity log</h3>
        {log.length === 0 ? (
          <p className="text-muted">Actions you run here will show up as a log, newest first.</p>
        ) : (
          <ul className="mono">
            {log.map((entry, i) => (
              <li key={i} className={entry.ok ? "log-ok" : "log-error"}>
                <span className="text-faint">{entry.time}</span> — {entry.message}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function SimCard({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <div className="sim-card">
      <h3>{title}</h3>
      <p className="text-muted">{description}</p>
      <div className="sim-card-body">{children}</div>
    </div>
  );
}
