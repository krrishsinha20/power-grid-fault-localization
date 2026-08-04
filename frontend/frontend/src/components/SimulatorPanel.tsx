import { useEffect, useRef, useState, type ReactNode } from "react";
import { api, ApiError } from "../api/client";
import type { Pole } from "../types";
import { GlassSelect } from "./GlassSelect";

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
 * without switching to Swagger.
 *
 * v3 additions:
 * - Replaced all native <select> elements with GlassSelect component
 *   so dropdown popups match the dark glass UI theme.
 * - Fixed Feeder ID list: previously displayed transformer IDs by mistake.
 *   Now provides proper Feeder IDs (F001..F005) plus any feeder IDs from incidents.
 */
export function SimulatorPanel({ onAction }: Props) {
  const [log, setLog]   = useState<LogEntry[]>([]);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const busyRef = useRef(false);

  // Live data for pickers
  const [poles, setPoles] = useState<Pole[]>([]);
  const [feeders, setFeeders] = useState<string[]>(["F001", "F002", "F003"]);
  const [loadingPoles, setLoadingPoles] = useState(true);

  useEffect(() => {
    Promise.all([
      api.getPoles({ limit: 300 }).catch(() => [] as Pole[]),
      api.getIncidents().catch(() => []),
    ]).then(([polesData, incidentsData]) => {
      setPoles(polesData);
      
      // Derive feeder list from incidents + default standard active feeders
      const incidentFeeders = incidentsData.map(i => i.feeder_id).filter(Boolean);
      const combinedFeeders = [...new Set([...incidentFeeders, "F001", "F002", "F003"])].sort();
      setFeeders(combinedFeeders);

      // Pre-select first transformer ID
      const tList = [...new Set(polesData.map(p => p.transformer_id))].sort();
      if (tList.length > 0) {
        setTransformerId(tList[0]);
      }
    }).finally(() => setLoadingPoles(false));
  }, []);

  // Derive unique transformer & pole lists
  const transformers = [...new Set(poles.map(p => p.transformer_id))].sort();
  const poleIds = poles.map(p => p.pole_id).sort();

  // GlassSelect options format [{ value: string }]
  const feederOptions = feeders.map(f => ({ value: f }));
  const transformerOptions = transformers.map(t => ({ value: t }));
  const poleOptions = poleIds.map(p => ({ value: p }));

  // Form state
  const [spanPoles,      setSpanPoles]      = useState("");   // comma/space list
  const [transformerId,  setTransformerId]  = useState("");
  const [feederId,       setFeederId]       = useState("F001");
  const [singlePoleId,   setSinglePoleId]   = useState("");
  const [repeatCount,    setRepeatCount]    = useState(5);

  function parsePoleIds(input: string): string[] {
    return input.split(/[\s,]+/).map(s => s.trim()).filter(Boolean);
  }

  // Pick N adjacent connected poles along a single branch line
  function pickConnectedSpan(n: number = 4): string[] {
    if (poles.length === 0) return [];
    const candidates = poles.filter(p => p.parent_pole_id);
    if (candidates.length === 0) return poleIds.slice(0, n);

    const start = candidates[Math.floor(Math.random() * candidates.length)];
    const result: string[] = [start.pole_id];

    let current = start;
    while (result.length < n) {
      const child = poles.find(p => p.parent_pole_id === current.pole_id);
      if (!child) break;
      result.push(child.pole_id);
      current = child;
    }
    return result;
  }

  async function run(label: string, action: () => Promise<{ success: boolean; message: string }>) {
    // Instant synchronous lock against rapid double-clicks
    if (busyRef.current) return;
    busyRef.current = true;
    setBusy(true);
    setActionError(null);

    try {
      const result = await action();
      setLog(prev => [
        { time: new Date().toLocaleTimeString(), message: `${label}: ${result.message}`, ok: result.success },
        ...prev,
      ].slice(0, 40));
      onAction();
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Request failed.";
      setActionError(`${label} failed: ${message}`);
      setLog(prev => [
        { time: new Date().toLocaleTimeString(), message: `${label}: ${message}`, ok: false },
        ...prev,
      ].slice(0, 40));
    } finally {
      busyRef.current = false;
      setBusy(false);
    }
  }

  const hasPoles = !loadingPoles && poles.length > 0;

  return (
    <div>
      <div className="simulator-header">
        <h2>Fault Simulator</h2>
        <p>
          Inject faults and noise directly into the synthetic network and watch them get detected,
          localized, ticketed, and — after repair — auto-verified from telemetry.
          {hasPoles && (
            <> Loaded <strong>{poles.length}</strong> poles, <strong>{transformers.length}</strong> transformers, <strong>{feeders.length}</strong> feeders.</>
          )}
        </p>
      </div>

      {actionError && (
        <div className="sim-error-banner" style={{
          margin: "0 0 16px 0",
          padding: "12px 16px",
          borderRadius: "var(--radius)",
          background: "var(--critical-bg)",
          border: "1px solid var(--critical)",
          color: "#fca5a5",
          fontSize: 13,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center"
        }}>
          <span>⚠️ {actionError}</span>
          <button
            style={{ background: "none", border: "none", color: "#fca5a5", cursor: "pointer", fontSize: 16 }}
            onClick={() => setActionError(null)}
          >
            ✕
          </button>
        </div>
      )}

      <div className="simulator-grid">

        {/* ---- Network ---- */}
        <SimCard
          icon="🌐"
          title="Network"
          description="Seed or regenerate the synthetic pole/transformer registry."
        >
          <button className="btn-secondary" disabled={busy}
            onClick={() => run("Generate network", () => api.generateNetwork(false))}>
            Ensure network exists
          </button>
          <button className="btn-danger" disabled={busy}
            onClick={() => run("Reset network", () => api.generateNetwork(true))}>
            Reset network (destructive)
          </button>
        </SimCard>

        {/* ---- Span fault ---- */}
        <SimCard
          icon="⚡"
          title="Span fault"
          description="Mark a set of adjacent poles dark — the core fault type. One ticket is expected."
        >
          {hasPoles ? (
            <label className="sim-label">
              Pole IDs (comma/space separated)
              <input
                className="sim-input mono"
                value={spanPoles}
                onChange={e => setSpanPoles(e.target.value)}
                placeholder={poleIds.slice(0, 3).join(", ")}
              />
            </label>
          ) : (
            <label className="sim-label">
              Pole IDs (comma/space separated)
              <input className="sim-input mono" value={spanPoles}
                onChange={e => setSpanPoles(e.target.value)}
                placeholder="P00023, P00024, P00025" />
            </label>
          )}

          {hasPoles && (
            <button className="btn-secondary" disabled={busy}
              onClick={() => {
                const ids = pickConnectedSpan(4);
                setSpanPoles(ids.join(", "));
              }}>
              Pick 4 connected poles
            </button>
          )}

          <div className="sim-button-row">
            <button className="btn-primary"
              disabled={busy || parsePoleIds(spanPoles).length === 0}
              onClick={() => run("Span fault", () => api.injectSpanFault(parsePoleIds(spanPoles)))}>
              Inject fault
            </button>
            <button className="btn-secondary"
              disabled={busy || parsePoleIds(spanPoles).length === 0}
              onClick={() => run("Repair span", () => api.repairFault(parsePoleIds(spanPoles)))}>
              Repair
            </button>
          </div>
        </SimCard>

        {/* ---- Transformer fault ---- */}
        <SimCard
          icon="🔴"
          title="Transformer fault"
          description="Every pole under one DT goes dark at once."
        >
          <label className="sim-label">
            Transformer ID
            {hasPoles ? (
              <GlassSelect
                value={transformerId}
                options={transformerOptions}
                onChange={setTransformerId}
                placeholder="— select transformer —"
                disabled={busy}
              />
            ) : (
              <input className="sim-input mono" value={transformerId}
                onChange={e => setTransformerId(e.target.value)} placeholder="DT0003" />
            )}
          </label>
          <button className="btn-primary" disabled={busy || !transformerId}
            onClick={() => run("Transformer fault", () => api.injectTransformerFault(transformerId))}>
            Inject fault
          </button>
        </SimCard>

        {/* ---- Feeder fault ---- */}
        <SimCard
          icon="🔆"
          title="Feeder fault"
          description="Every transformer on the feeder goes dark — grouped into one ticket."
        >
          <label className="sim-label">
            Feeder ID
            <GlassSelect
              value={feederId}
              options={feederOptions}
              onChange={setFeederId}
              placeholder="— select feeder —"
              disabled={busy}
            />
          </label>
          <div className="sim-button-row">
            <button className="btn-primary" disabled={busy || !feederId}
              onClick={() => run("Feeder fault", () => api.injectFeederFault(feederId))}>
              Inject fault
            </button>
            <button className="btn-secondary" disabled={busy || !feederId}
              onClick={() => run("Repair feeder", () => api.repairFeeder(feederId))}>
              Repair
            </button>
          </div>
        </SimCard>

        {/* ---- Dead sensor ---- */}
        <SimCard
          icon="📡"
          title="Noise: dead sensor"
          description="Device goes silent while power stays on — must NOT create an outage ticket."
        >
          <label className="sim-label">
            Pole ID
            {hasPoles ? (
              <GlassSelect
                value={singlePoleId}
                options={poleOptions}
                onChange={setSinglePoleId}
                placeholder="— select pole —"
                disabled={busy}
              />
            ) : (
              <input className="sim-input mono" value={singlePoleId}
                onChange={e => setSinglePoleId(e.target.value)} placeholder="P00045" />
            )}
          </label>
          <button className="btn-secondary" disabled={busy || !singlePoleId}
            onClick={() => run("Sensor failure", () => api.simulateSensorFailure(singlePoleId))}>
            Kill sensor (power stays on)
          </button>
        </SimCard>

        {/* ---- Duplicate telemetry ---- */}
        <SimCard
          icon="♻️"
          title="Noise: duplicate packets"
          description="Same packet resent N times — must apply exactly one state change."
        >
          <label className="sim-label">
            Pole ID
            {hasPoles ? (
              <GlassSelect
                value={singlePoleId}
                options={poleOptions}
                onChange={setSinglePoleId}
                placeholder="— select pole —"
                disabled={busy}
              />
            ) : (
              <input className="sim-input mono" value={singlePoleId}
                onChange={e => setSinglePoleId(e.target.value)} placeholder="P00045" />
            )}
          </label>
          <label className="sim-label">
            Repeat count
            <input className="sim-input mono" type="number" min={2} max={20}
              value={repeatCount}
              onChange={e => setRepeatCount(Number(e.target.value))} />
          </label>
          <button className="btn-secondary" disabled={busy || !singlePoleId}
            onClick={() => run("Duplicate telemetry",
              () => api.simulateDuplicateTelemetry(singlePoleId, repeatCount))}>
            Send duplicates
          </button>
        </SimCard>

        {/* ---- Out-of-order ---- */}
        <SimCard
          icon="🔀"
          title="Noise: out-of-order"
          description="A stale 'restored' packet arrives after a newer 'lost' packet — must not win."
        >
          <label className="sim-label">
            Pole ID
            {hasPoles ? (
              <GlassSelect
                value={singlePoleId}
                options={poleOptions}
                onChange={setSinglePoleId}
                placeholder="— select pole —"
                disabled={busy}
              />
            ) : (
              <input className="sim-input mono" value={singlePoleId}
                onChange={e => setSinglePoleId(e.target.value)} placeholder="P00045" />
            )}
          </label>
          <button className="btn-secondary" disabled={busy || !singlePoleId}
            onClick={() => run("Out-of-order telemetry",
              () => api.simulateOutOfOrder(singlePoleId))}>
            Send out-of-order packets
          </button>
        </SimCard>

      </div>

      {/* ---- Activity log ---- */}
      <div className="sim-log">
        <div className="sim-log-header">
          <h3>Activity log</h3>
          {log.length > 0 && (
            <button className="sim-log-clear" onClick={() => setLog([])}>
              Clear
            </button>
          )}
        </div>
        {log.length === 0 ? (
          <p className="text-faint" style={{ fontSize: 12, margin: 0 }}>
            Actions you run here will appear as a log, newest first.
          </p>
        ) : (
          <ul className="mono">
            {log.map((entry, i) => (
              <li key={i} className={entry.ok ? "log-ok" : "log-error"}>
                <span className="log-time">{entry.time}</span>
                {entry.message}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function SimCard({
  icon,
  title,
  description,
  children,
}: {
  icon: string;
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <div className="sim-card">
      <div className="sim-card-header">
        <span className="sim-card-icon">{icon}</span>
        <div>
          <h3>{title}</h3>
          <p>{description}</p>
        </div>
      </div>
      <div className="sim-card-body">{children}</div>
    </div>
  );
}
