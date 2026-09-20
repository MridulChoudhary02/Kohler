// frontend/src/lib/api.ts — API Client Module for Backend Communication

import { DetectionEvent, Ticket, HygieneCounter, BaselineProfile, TelemetryReading, FacilityMetrics } from './types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function fetchFacilityMetrics(): Promise<FacilityMetrics> {
  const url = `${API_BASE_URL}/api/v1/facility/metrics`;
  const res = await fetch(url, { cache: 'no-store' });
  if (!res.ok) {
    throw new Error(`Failed to fetch facility metrics: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchEvents(params?: {
  fixture_id?: string;
  zone_id?: string;
  event_type?: string;
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<DetectionEvent[]> {
  const query = new URLSearchParams();
  if (params?.fixture_id) query.set('fixture_id', params.fixture_id);
  if (params?.zone_id) query.set('zone_id', params.zone_id);
  if (params?.event_type) query.set('event_type', params.event_type);
  if (params?.status) query.set('status', params.status);
  if (params?.limit) query.set('limit', String(params.limit));
  if (params?.offset) query.set('offset', String(params.offset));

  const url = `${API_BASE_URL}/api/v1/events?${query.toString()}`;
  const res = await fetch(url, { cache: 'no-store' });
  if (!res.ok) {
    throw new Error(`Failed to fetch events: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchEventById(eventId: string): Promise<DetectionEvent> {
  const url = `${API_BASE_URL}/api/v1/events/${eventId}`;
  const res = await fetch(url, { cache: 'no-store' });
  if (!res.ok) {
    throw new Error(`Failed to fetch event ${eventId}: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchTickets(params?: {
  status?: string;
  zone_id?: string;
  assigned_tech_id?: string;
  limit?: number;
  offset?: number;
}): Promise<Ticket[]> {
  const query = new URLSearchParams();
  if (params?.status) query.set('status', params.status);
  if (params?.zone_id) query.set('zone_id', params.zone_id);
  if (params?.assigned_tech_id) query.set('assigned_tech_id', params.assigned_tech_id);
  if (params?.limit) query.set('limit', String(params.limit));
  if (params?.offset) query.set('offset', String(params.offset));

  const url = `${API_BASE_URL}/api/v1/tickets?${query.toString()}`;
  const res = await fetch(url, { cache: 'no-store' });
  if (!res.ok) {
    throw new Error(`Failed to fetch tickets: ${res.statusText}`);
  }
  return res.json();
}

export async function acknowledgeTicket(ticketId: string): Promise<Ticket> {
  const url = `${API_BASE_URL}/api/v1/tickets/${ticketId}/acknowledge`;
  const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' } });
  if (!res.ok) {
    throw new Error(`Failed to acknowledge ticket ${ticketId}`);
  }
  return res.json();
}

export async function startTicket(ticketId: string): Promise<Ticket> {
  const url = `${API_BASE_URL}/api/v1/tickets/${ticketId}/start`;
  const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' } });
  if (!res.ok) {
    throw new Error(`Failed to start ticket ${ticketId}`);
  }
  return res.json();
}

export async function resolveTicket(ticketId: string): Promise<Ticket> {
  const url = `${API_BASE_URL}/api/v1/tickets/${ticketId}/resolve`;
  const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' } });
  if (!res.ok) {
    throw new Error(`Failed to resolve ticket ${ticketId}`);
  }
  return res.json();
}

export async function fetchHygieneCounters(fixtureId?: string): Promise<HygieneCounter[]> {
  const query = new URLSearchParams();
  if (fixtureId) query.set('fixture_id', fixtureId);
  const url = `${API_BASE_URL}/api/v1/hygiene-counters?${query.toString()}`;
  const res = await fetch(url, { cache: 'no-store' });
  if (!res.ok) {
    throw new Error(`Failed to fetch hygiene counters: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchFixtureBaseline(
  fixtureId: string,
  detectedAt?: string,
  evidenceValue?: number
): Promise<BaselineProfile | null> {
  const query = new URLSearchParams();
  if (detectedAt) query.set('detected_at', detectedAt);
  if (evidenceValue !== undefined && evidenceValue !== null) query.set('evidence_value', String(evidenceValue));
  const url = `${API_BASE_URL}/api/v1/fixtures/${fixtureId}/baseline${query.toString() ? `?${query.toString()}` : ''}`;
  const res = await fetch(url, { cache: 'no-store' });
  if (!res.ok) return null;
  return res.json();
}

export async function fetchFixtureTelemetry(
  fixtureId: string,
  detectedAt?: string
): Promise<TelemetryReading[]> {
  const query = new URLSearchParams();
  if (detectedAt) query.set('detected_at', detectedAt);
  query.set('limit', '30');
  const url = `${API_BASE_URL}/api/v1/fixtures/${fixtureId}/telemetry?${query.toString()}`;
  const res = await fetch(url, { cache: 'no-store' });
  if (!res.ok) return [];
  return res.json();
}

export async function sendChatQuery(queryText: string): Promise<{ answer: string }> {
  const url = `${API_BASE_URL}/api/v1/chat`;
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: queryText }),
  });
  if (!res.ok) {
    throw new Error(`Chat query failed: ${res.statusText}`);
  }
  return res.json();
}

