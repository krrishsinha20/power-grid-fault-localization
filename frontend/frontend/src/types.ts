// Mirrors the backend's Pydantic response models exactly
// (app/schemas/*.py). Keep in sync if the backend shape changes.

export type FaultType =
  | "SPAN_FAULT"
  | "TRANSFORMER_FAULT"
  | "FEEDER_FAULT"
  | "SENSOR_FAILURE"
  | "UNKNOWN";

export type IncidentStatus =
  | "DETECTED"
  | "ACKNOWLEDGED"
  | "ASSIGNED"
  | "IN_PROGRESS"
  | "VERIFIED"
  | "CLOSED";

export type TicketStatus =
  | "OPEN"
  | "ACKNOWLEDGED"
  | "ASSIGNED"
  | "IN_PROGRESS"
  | "CLOSED";

export type Priority = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface Incident {
  incident_id: string;
  fault_type: FaultType;
  feeder_id: string;
  transformer_id: string;
  start_pole: string | null;
  end_pole: string;
  affected_pole_count: number;
  affected_pole_ids: string[];
  confidence: number;
  id: number;
  status: IncidentStatus;
  root_cause: string | null;
  ai_summary: string | null;
  recommended_action: string | null;
  created_at: string;
  updated_at: string;
  // Not always present on every backend build -- see
  // localization_service.py. Optional so the UI degrades gracefully
  // if an older backend doesn't send them.
  latitude?: number;
  longitude?: number;
  pincode?: string;
}

export interface Ticket {
  ticket_id: string;
  incident_id: number;
  priority: Priority;
  id: number;
  assigned_to: string | null;
  assigned_team: string | null;
  status: TicketStatus;
  remarks: string | null;
  created_at: string;
  updated_at: string;
}

export interface Pole {
  pole_id: string;
  parent_pole_id: string | null;
  transformer_id: string;
  latitude: number;
  longitude: number;
  pincode: string | null;
  energized: boolean;
  active: boolean;
}

export interface DashboardStats {
  total_poles: number;
  healthy_poles: number;
  faulty_poles: number;
  active_incidents: number;
  open_tickets: number;
}

export interface ScheduledOutage {
  outage_id: string;
  feeder_id: string;
  transformer_id: string | null;
  start_time: string;
  end_time: string;
  reason: string;
  status: string;
  id: number;
  created_at: string;
  updated_at: string;
}

export interface SimulationResponse {
  success: boolean;
  message: string;
}

export interface AIExplainResult extends Incident {
  root_cause: string;
  ai_summary: string;
  recommended_action: string;
}
