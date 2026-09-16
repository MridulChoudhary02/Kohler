// frontend/src/lib/types.ts — TypeScript Interfaces for Dashboard API Data Shapes

export type ZoneTier = 'Tier 1' | 'Tier 2' | 'Tier 3' | 'Tier 4';

export interface DetectionEvent {
  event_id: string;
  fixture_id: string;
  event_type: 'leak' | 'hygiene' | 'sensor_fault' | string;
  confidence_score: number;
  evidence_value: number | null;
  detected_at: string;
  status: 'logged' | 'dispatched' | 'resolved' | string;
  fixture_type?: string;
  zone_id?: string;
  zone_name?: string;
  criticality_tier?: ZoneTier;
}

export interface Ticket {
  ticket_id: string;
  event_id: string;
  zone_id: string;
  priority_score: number;
  status: 'open' | 'acknowledged' | 'in_progress' | 'resolved';
  sla_due: string | null;
  assigned_team: string | null;
  assigned_tech_id: string | null;
  is_escalated: boolean;
  summary_text: string | null;
  acknowledged_at: string | null;
  started_at: string | null;
  resolved_at: string | null;
}

export interface HygieneCounter {
  id: string;
  fixture_id: string;
  uses_since_clean: number;
  last_cleaned: string | null;
  predicted_breach_time: string | null;
  fixture_type?: string;
  zone_id?: string;
  criticality_tier?: ZoneTier;
}

export interface TelemetryReading {
  reading_id: string;
  sensor_id: string;
  timestamp: string;
  flow_rate_lpm: number;
  flush_event: number;
  occupancy_state: number;
  diagnostic_status: string;
}

export interface BaselineProfile {
  fixture_id: string;
  mean_off_flow: number;
  std_off_flow: number;
  mean_flush_volume: number;
  mean_flush_duration_s: number;
  ucl: number;
  warmup_complete: boolean;
  last_updated: string;
}

export interface ZoneSummary {
  zone_id: string;
  name: string;
  criticality_tier: ZoneTier;
  open_ticket_count: number;
  max_priority_score: number;
  total_fixtures: number;
}
