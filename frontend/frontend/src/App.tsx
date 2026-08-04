import { useEffect, useState } from "react";
import { api } from "./api/client";
import { usePolling } from "./hooks/usePolling";
import { usePoleLookup } from "./hooks/usePoleLookup";
import { StatsBar } from "./components/StatsBar";
import { IncidentList } from "./components/IncidentList";
import { MapView } from "./components/MapView";
import { IncidentDetail } from "./components/IncidentDetail";
import { SimulatorPanel } from "./components/SimulatorPanel";
import "./App.css";

type Tab = "console" | "simulator";

export default function App() {
  const [tab, setTab] = useState<Tab>("console");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const {
    data: dashboard,
    refresh: refreshDashboard,
  } = usePolling(() => api.getDashboard());

  const {
    data: incidents,
    error: incidentsError,
    refresh: refreshIncidents,
  } = usePolling(() => api.getIncidents());

  const { data: tickets, refresh: refreshTickets } = usePolling(() => api.getTickets());

  const { lookup } = usePoleLookup();

  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  // Any poll landing updates the "last updated" clock in the stats
  // bar -- close enough for an operator glance. Runs as an effect
  // (not during render) so it never triggers a same-render re-set.
  useEffect(() => {
    if (incidents) setLastUpdated(new Date());
  }, [incidents]);

  function refreshAll() {
    refreshDashboard();
    refreshIncidents();
    refreshTickets();
    setLastUpdated(new Date());
  }

  const selectedIncident = incidents?.find((i) => i.incident_id === selectedId) ?? null;
  const selectedTicket = selectedIncident
    ? tickets?.find((t) => t.incident_id === selectedIncident.id)
    : undefined;

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-title">
          <span className="app-title-main">KSPDB</span>
          <span className="app-title-sub">Fault Localization Console</span>
        </div>
        <nav className="app-tabs">
          <button
            className={`app-tab ${tab === "console" ? "app-tab-active" : ""}`}
            onClick={() => setTab("console")}
          >
            Operator console
          </button>
          <button
            className={`app-tab ${tab === "simulator" ? "app-tab-active" : ""}`}
            onClick={() => setTab("simulator")}
          >
            Fault simulator
          </button>
        </nav>
      </header>

      <StatsBar stats={dashboard} lastUpdated={lastUpdated} />

      {tab === "console" ? (
        <main className="console-layout">
          <div className="console-list-pane">
            {incidentsError && (
              <div className="banner-error">
                Can't reach the backend at the configured API URL. Check VITE_API_BASE_URL and that
                the backend is running.
              </div>
            )}
            <IncidentList
              incidents={incidents ?? []}
              selectedId={selectedId}
              onSelect={setSelectedId}
            />
          </div>

          <div className="console-map-pane">
            <MapView
              incidents={incidents ?? []}
              lookup={lookup}
              selectedId={selectedId}
              onSelect={setSelectedId}
            />
          </div>

          {selectedIncident && (
            <div className="console-detail-pane">
              <IncidentDetail
                incident={selectedIncident}
                ticket={selectedTicket}
                lookup={lookup}
                onClose={() => setSelectedId(null)}
                onChanged={refreshAll}
              />
            </div>
          )}
        </main>
      ) : (
        <main className="simulator-layout">
          <SimulatorPanel onAction={refreshAll} />
        </main>
      )}
    </div>
  );
}
