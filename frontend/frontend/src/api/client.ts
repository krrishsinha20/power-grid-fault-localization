import type {
  DashboardStats,
  Incident,
  Pole,
  ScheduledOutage,
  SimulationResponse,
  Ticket,
} from "../types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      // response wasn't JSON -- fall back to statusText
    }
    throw new ApiError(res.status, detail);
  }

  // Some endpoints (e.g. PATCH status) return a plain message, not JSON
  // with content -- guard against empty bodies.
  const text = await res.text();
  return (text ? JSON.parse(text) : undefined) as T;
}

export const api = {
  // ---- Dashboard ----
  getDashboard: () => request<DashboardStats>("/dashboard"),

  // ---- Poles ----
  getPoles: (params?: { transformer_id?: string; limit?: number }) => {
    const qs = new URLSearchParams();
    if (params?.transformer_id) qs.set("transformer_id", params.transformer_id);
    if (params?.limit) qs.set("limit", String(params.limit));
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return request<Pole[]>(`/poles${suffix}`);
  },

  // ---- Incidents ----
  getIncidents: () => request<Incident[]>("/incidents"),

  getIncident: (incidentId: string) =>
    request<Incident>(`/incidents/${incidentId}`),

  explainIncident: (incidentId: string) =>
    request<Incident>(`/incidents/${incidentId}/explain`, { method: "POST" }),

  updateIncidentStatus: (incidentId: string, status: string) =>
    request<{ message: string }>(
      `/incidents/${incidentId}/status?status=${encodeURIComponent(status)}`,
      { method: "PATCH" }
    ),

  // ---- Tickets ----
  getTickets: () => request<Ticket[]>("/tickets"),

  getTicket: (ticketId: string) => request<Ticket>(`/tickets/${ticketId}`),

  // NOTE: there is no /assign endpoint on the backend -- assignment is
  // represented purely as a status transition to "ASSIGNED" today.
  // If the backend adds a real assign-to-engineer endpoint later, wire
  // it here instead of overloading updateTicketStatus.
  updateTicketStatus: (ticketId: string, status: string) =>
    request<{ message: string }>(
      `/tickets/${ticketId}/status?status=${encodeURIComponent(status)}`,
      { method: "PATCH" }
    ),

  // Raw admin override -- does NOT verify telemetry (see DECISIONS.md).
  // The operator console never calls this from the normal "resolve"
  // flow; it is exposed separately and labeled as a forced close.
  forceCloseTicket: (ticketId: string) =>
    request<{ message: string }>(`/tickets/${ticketId}/close`, {
      method: "POST",
    }),

  // ---- Scheduled outages ----
  getScheduledOutages: () => request<ScheduledOutage[]>("/scheduled-outages"),

  createScheduledOutage: (payload: Partial<ScheduledOutage>) =>
    request<ScheduledOutage>("/scheduled-outages", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  deleteScheduledOutage: (outageId: string) =>
    request<{ success: boolean; message: string }>(
      `/scheduled-outages/${outageId}`,
      { method: "DELETE" }
    ),

  // ---- Simulator ----
  generateNetwork: (reset = false) =>
    request<SimulationResponse>(`/simulate/network?reset=${reset}`, {
      method: "POST",
    }),

  injectSpanFault: (poleIds: string[]) =>
    request<SimulationResponse>("/simulate/span", {
      method: "POST",
      body: JSON.stringify({ pole_ids: poleIds }),
    }),

  injectTransformerFault: (transformerId: string) =>
    request<SimulationResponse>("/simulate/transformer", {
      method: "POST",
      body: JSON.stringify({ transformer_id: transformerId }),
    }),

  injectFeederFault: (feederId: string) =>
    request<SimulationResponse>("/simulate/feeder", {
      method: "POST",
      body: JSON.stringify({ feeder_id: feederId }),
    }),

  simulateSensorFailure: (poleId: string) =>
    request<SimulationResponse>("/simulate/noise/sensor-failure", {
      method: "POST",
      body: JSON.stringify({ pole_id: poleId }),
    }),

  simulateDuplicateTelemetry: (poleId: string, repeatCount = 5) =>
    request<SimulationResponse>("/simulate/noise/duplicate-telemetry", {
      method: "POST",
      body: JSON.stringify({ pole_id: poleId, repeat_count: repeatCount }),
    }),

  simulateOutOfOrder: (poleId: string) =>
    request<SimulationResponse>("/simulate/noise/out-of-order", {
      method: "POST",
      body: JSON.stringify({ pole_id: poleId }),
    }),

  repairFault: (poleIds: string[]) =>
    request<SimulationResponse>("/simulate/repair", {
      method: "POST",
      body: JSON.stringify({ pole_ids: poleIds }),
    }),

  repairFeeder: (feederId: string) =>
    request<SimulationResponse>("/simulate/repair/feeder", {
      method: "POST",
      body: JSON.stringify({ feeder_id: feederId }),
    }),
};

export { ApiError };
