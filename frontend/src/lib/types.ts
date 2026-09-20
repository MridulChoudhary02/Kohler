// frontend/src/lib/types.ts — TypeScript Interfaces for Dashboard API Data Shapes

export type ZoneTier = 'Tier 1' | 'Tier 2' | 'Tier 3' | 'Tier 4';

export interface DetectionEvent {
  event_id: string;
  fixture_id: string;
  event_type: 'leak' | 'hygiene' | 'sensor_fault' | string;
  sub_type?: string | null;
  detection_rule?: string | null;
  confidence_score: number;
  evidence_value: number | null;
  detected_at: string;
  status: 'logged' | 'dispatched' | 'resolved' | string;
  fixture_type?: string;
  zone_id?: string;
  zone_name?: string;
  criticality_tier?: ZoneTier;
  anomaly_duration_seconds?: number | null;
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
  anomaly_duration_seconds?: number | null;
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
  sensor_health_score?: number;
  estimated_cost_inr_per_day?: number;
  confirmation_window_seconds?: number;
  last_flush_at?: string | null;
}

export interface ZoneSummary {
  zone_id: string;
  name: string;
  criticality_tier: ZoneTier;
  open_ticket_count: number;
  max_priority_score: number;
  total_fixtures: number;
}

export interface FacilityMetrics {
  total_water_wasted_litres: number;
  cost_at_risk_inr: number;
  co2_at_risk_kg: number;
  sensors_online: number;
  sensors_total: number;
  avg_sensor_health_score: number;
  anomalies_today: number;
  total_anomalies: number;
  water_cost_per_litre: number;
  co2_per_litre: number;
}

export interface InvestigationReport {
  summary: string;
  likely_cause: string;
  evidence: string[];
  recommended_actions: string[];
  impact: string;
  risk_note: string;
}

export interface InvestigationResponse {
  ticket_id: string;
  evidence: Record<string, any>;
  investigation: InvestigationReport | null;
  error: string | null;
}

export interface FixtureHealthSubScores {
  frequency_score: number;
  recurrence_score: number;
  flow_drift_score: number;
  slow_leak_score: number;
  sensor_health_score: number;
  unresolved_score: number;
}

export interface FixtureIncidentSummary {
  event_id: string;
  event_type: string;
  sub_type: string | null;
  rule_label: string;
  detected_at: string;
  confidence_score: number;
  evidence_value: number | null;
  ticket_id: string | null;
  ticket_status: string | null;
  priority_score: number | null;
}

export interface FixtureHealthItem {
  fixture_id: string;
  fixture_type: string;
  zone_id: string;
  zone_tier: string;
  health_score: number;
  risk_score: number;
  health_status: 'healthy' | 'watch' | 'degrading' | 'high_risk';
  trend: 'stable' | 'deteriorating' | 'improving';
  total_incidents: number;
  active_tickets_count: number;
  leak_incidents_count: number;
  sensor_faults_count: number;
  hygiene_incidents_count: number;
  sub_scores: FixtureHealthSubScores;
  last_incident_at: string | null;
  last_resolved_at: string | null;
  recommendation: string;
}

export interface FixtureHealthListResponse {
  facility_health_score: number;
  high_risk_count: number;
  degrading_count: number;
  watch_count: number;
  healthy_count: number;
  fixtures: FixtureHealthItem[];
}

export interface FixtureHealthDetailResponse extends FixtureHealthItem {
  recent_incidents: FixtureIncidentSummary[];
}


