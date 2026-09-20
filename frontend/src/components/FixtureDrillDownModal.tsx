// frontend/src/components/FixtureDrillDownModal.tsx — View 4: Fixture Technical Evidence Modal (Evidence Timeline Spec)

import React, { useState, useEffect } from 'react';
import { X, BarChart2, Clock, Activity, Droplets, CheckCircle2, AlertTriangle, ArrowRight, Sparkles, Wrench, ShieldAlert, ListChecks, Loader2, ChevronDown, ChevronUp, TrendingDown } from 'lucide-react';
import { DetectionEvent, Ticket, BaselineProfile, TelemetryReading, InvestigationReport, TicketSustainabilityImpact } from '../lib/types';
import { fetchFixtureBaseline, fetchFixtureTelemetry, fetchTickets, fetchTicketInvestigation, fetchTicketSustainabilityImpact } from '../lib/api';

interface FixtureDrillDownModalProps {
  event: DetectionEvent | null;
  ticket: Ticket | null;
  onClose: () => void;
}

function formatDuration(sec: number | null | undefined): string {
  if (sec === null || sec === undefined || isNaN(sec)) return 'N/A';
  const s = Math.round(sec);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  const remS = s % 60;
  if (m < 60) return `${m}m ${remS}s`;
  const h = Math.floor(m / 60);
  const remM = m % 60;
  return `${h}h ${remM}m`;
}

function formatTimestamp(ts: string | null | undefined): string {
  if (!ts) return 'N/A';
  try {
    const d = new Date(ts);
    return d.toLocaleString([], {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    });
  } catch {
    return String(ts);
  }
}

export const FixtureDrillDownModal: React.FC<FixtureDrillDownModalProps> = ({
  event,
  ticket,
  onClose,
}) => {
  const [baseline, setBaseline] = useState<BaselineProfile | null>(null);
  const [telemetry, setTelemetry] = useState<TelemetryReading[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [investigation, setInvestigation] = useState<InvestigationReport | null>(null);
  const [investigating, setInvestigating] = useState<boolean>(false);
  const [investigationError, setInvestigationError] = useState<string | null>(null);
  const [showDiagnostics, setShowDiagnostics] = useState<boolean>(false);
  const [sustainabilityImpact, setSustainabilityImpact] = useState<TicketSustainabilityImpact | null>(null);

  const fixtureId = event?.fixture_id || 'Unknown Fixture';
  const [activeTicket, setActiveTicket] = useState<Ticket | null>(ticket);

  useEffect(() => {
    setActiveTicket(ticket);
    setInvestigation(null);
    setInvestigationError(null);
    setInvestigating(false);
  }, [ticket, event?.event_id]);

  useEffect(() => {
    const currentTicketId = activeTicket?.ticket_id || ticket?.ticket_id;
    const currentStatus = activeTicket?.status || ticket?.status;
    if (currentTicketId && currentStatus === 'resolved') {
      fetchTicketSustainabilityImpact(currentTicketId, 6.0)
        .then((data) => setSustainabilityImpact(data))
        .catch((err) => console.error('Error loading ticket sustainability impact:', err));
    } else {
      setSustainabilityImpact(null);
    }
  }, [activeTicket?.ticket_id, activeTicket?.status, ticket?.ticket_id, ticket?.status]);

  useEffect(() => {
    if (!fixtureId || fixtureId === 'Unknown Fixture') return;

    let isMounted = true;
    setLoading(true);

    const loadEvidenceData = async () => {
      try {
        const [bpData, telData, ticketsData] = await Promise.all([
          fetchFixtureBaseline(fixtureId, event?.detected_at, event?.evidence_value ?? undefined),
          fetchFixtureTelemetry(fixtureId, event?.detected_at),
          ticket ? Promise.resolve([]) : fetchTickets({ limit: 100 }),
        ]);
        if (isMounted) {
          setBaseline(bpData);
          setTelemetry(telData);
          if (!ticket && event && ticketsData.length > 0) {
            const match = ticketsData.find((t) => t.event_id === event.event_id);
            if (match) setActiveTicket(match);
          }
          setLoading(false);
        }
      } catch (err) {
        console.error('Error loading fixture evidence:', err);
        if (isMounted) setLoading(false);
      }
    };

    loadEvidenceData();
    return () => {
      isMounted = false;
    };
  }, [fixtureId, event?.detected_at, ticket, event?.event_id, event?.evidence_value]);

  if (!event && !ticket) return null;

  const eventType = event?.event_type || 'leak';
  const confidence = event?.confidence_score ?? 0.90;
  const evidenceValue = event?.evidence_value ?? 0.0;
  const zoneName = event?.zone_name || ticket?.zone_id || 'Hospital Zone';
  const tier = event?.criticality_tier || 'Tier 1';
  const status = activeTicket?.status || ticket?.status || event?.status || 'dispatched';

  // Evidence values & rates
  let evidenceDisplay = 'N/A';
  let lossRateLph = 0.0;
  if (evidenceValue !== null && evidenceValue !== undefined) {
    if (eventType === 'leak') {
      lossRateLph = evidenceValue;
      evidenceDisplay = `${evidenceValue.toFixed(2)} L/hr`;
    } else if (eventType === 'hygiene') {
      evidenceDisplay = `${evidenceValue.toFixed(1)}m to breach`;
    } else if (eventType === 'sensor_fault') {
      evidenceDisplay = `Health score ${evidenceValue.toFixed(2)}`;
    }
  }

  const meanOffFlow = baseline?.mean_off_flow ?? 0.008;
  const stdOffFlow = baseline?.std_off_flow ?? 0.0116;
  const ucl = baseline?.ucl ?? (meanOffFlow + 3.0 * stdOffFlow);

  // New Evidence Timeline fields
  const detectedAtStr = event?.detected_at || activeTicket?.started_at || null;
  const priorityScore = activeTicket?.priority_score ?? (event ? Math.round(confidence * 85) : 50);

  // Latest Telemetry reading flow & occupancy
  const latestReading = telemetry.length > 0 ? telemetry[telemetry.length - 1] : null;
  const currentFlowLpm = latestReading ? latestReading.flow_rate_lpm : (eventType === 'leak' ? evidenceValue / 60.0 : meanOffFlow);
  const occupancyState = latestReading ? latestReading.occupancy_state : 0;

  // New Backend Evidence Fields
  const detectionRule = event?.detection_rule || (
    eventType === 'leak' ? 'EWMA/UCL sustained breach' :
    eventType === 'hygiene' ? 'Predictive hygiene threshold breach' :
    'Sensor diagnostics anomaly'
  );

  const durationSeconds = event?.anomaly_duration_seconds ?? activeTicket?.anomaly_duration_seconds ?? (
    detectedAtStr ? Math.max(0, Math.round((new Date().getTime() - new Date(detectedAtStr).getTime()) / 1000)) : 0
  );

  const sensorHealthScore = baseline?.sensor_health_score ?? (eventType === 'sensor_fault' && evidenceValue !== null ? evidenceValue : 1.0);
  const estimatedCostInr = baseline?.estimated_cost_inr_per_day ?? (lossRateLph > 0 ? Math.round(lossRateLph * 24 * 0.15 * 100) / 100 : 0.0);
  const confirmationWindowSeconds = baseline?.confirmation_window_seconds ?? (tier === 'Tier 1' ? 180 : tier === 'Tier 2' ? 300 : tier === 'Tier 3' ? 420 : 600);
  const lastFlushAt = baseline?.last_flush_at || null;

  // Intervention Impact derived variables (strictly for Resolved tickets)
  const isResolved = status === 'resolved' || activeTicket?.status === 'resolved' || ticket?.status === 'resolved';
  const impactFlowLpm = lossRateLph > 0 ? lossRateLph / 60.0 : (sustainabilityImpact?.observed_flow_lpm ?? 0.0);
  const impactDurationMins = durationSeconds > 0 ? durationSeconds / 60.0 : (sustainabilityImpact?.elapsed_minutes ?? 18.0);
  const waterLostLiters = sustainabilityImpact?.prevented_waste?.actual_loss_liters ?? Number((impactFlowLpm * impactDurationMins).toFixed(1));
  const estimatedAvoidedLiters = sustainabilityImpact?.prevented_waste?.estimated_water_saved_liters ?? Number(Math.max(0, impactFlowLpm * (impactDurationMins >= 360 ? impactDurationMins + 360 : 360) - (impactFlowLpm * impactDurationMins)).toFixed(1));
  const avoidedCostInr = sustainabilityImpact?.prevented_waste?.avoided_cost_inr ?? Number((estimatedAvoidedLiters * 0.15).toFixed(2));
  const lostCostInr = sustainabilityImpact?.prevented_waste?.cost_impact_inr ?? Number((waterLostLiters * 0.15).toFixed(2));

  // Compute trigger timestamp (candidate start = detected_at - confirmation window)
  let triggerTimeStr = 'T - 0m';
  if (detectedAtStr) {
    try {
      const d = new Date(detectedAtStr);
      const trig = new Date(d.getTime() - confirmationWindowSeconds * 1000);
      triggerTimeStr = trig.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
    } catch {
      triggerTimeStr = 'Elevated Flow Start';
    }
  }

  const eventTagClass = eventType === 'leak' ? 'tag-leak' : eventType === 'hygiene' ? 'tag-hygiene' : 'tag-sensor';
  const tierTagClass = tier === 'Tier 1' ? 'tag-tier1' : tier === 'Tier 2' ? 'tag-tier2' : 'tag-tier3';

  const canInvestigate =
    !!activeTicket &&
    ['open', 'acknowledged', 'in_progress'].includes(activeTicket.status);

  const handleRunInvestigation = async () => {
    if (!activeTicket?.ticket_id) return;
    setInvestigating(true);
    setInvestigationError(null);
    try {
      const res = await fetchTicketInvestigation(activeTicket.ticket_id);
      if (res.error) {
        setInvestigationError(res.error);
      } else {
        setInvestigation(res.investigation);
      }
    } catch (err: any) {
      setInvestigationError(err?.message || 'Investigation request failed');
    } finally {
      setInvestigating(false);
    }
  };

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      zIndex: 100,
      background: 'rgba(0, 0, 0, 0.85)',
      backdropFilter: 'blur(8px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '20px'
    }}>
      <div id="fixture-drilldown-modal-dialog" className="command-panel" style={{
        width: '100%',
        maxWidth: '920px',
        maxHeight: '92vh',
        overflowY: 'auto',
        padding: '28px',
        background: '#0f0f11',
        border: '1px solid #27272a',
        borderRadius: '10px',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.7)'
      }}>
        {/* Modal Header */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', borderBottom: '1px solid #27272a', paddingBottom: '16px', marginBottom: '20px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', flexWrap: 'wrap' }}>
              <span className={`tag-tech ${eventTagClass}`}>
                <span className={`status-dot ${eventType === 'leak' ? 'status-dot-rose' : 'status-dot-cyan'}`} />
                {eventType}
              </span>
              <span className={`tag-tech ${tierTagClass}`}>
                {tier}
              </span>
              <span style={{ fontSize: '0.78rem', color: '#a1a1aa' }}>
                {zoneName}
              </span>
              <span style={{
                fontSize: '0.72rem',
                background: '#18181b',
                color: '#38bdf8',
                border: '1px solid #27272a',
                padding: '2px 8px',
                borderRadius: '4px',
                fontFamily: 'monospace'
              }}>
                {detectionRule}
              </span>
            </div>
            <h2 style={{ fontSize: '1.35rem', fontWeight: 700, color: '#f4f4f5', letterSpacing: '-0.02em' }}>
              Evidence Timeline & Diagnostics: <span className="font-mono" style={{ color: '#ffffff', fontWeight: 600 }}>{fixtureId}</span>
            </h2>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button
              onClick={onClose}
              className="btn-action"
              style={{ padding: '6px', background: '#18181b', border: '1px solid #27272a', borderRadius: '6px', cursor: 'pointer' }}
              aria-label="Close modal"
            >
              <X size={16} color="#a1a1aa" />
            </button>
          </div>
        </div>

        {/* Section 1: Primary Evidence & Operations Metrics (Requirement 7 & 9) */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))',
          gap: '14px',
          paddingBottom: '18px',
          borderBottom: '1px solid #222225',
          marginBottom: '20px'
        }}>
          <div style={{ background: '#141417', padding: '12px 14px', borderRadius: '6px', border: '1px solid #222225' }}>
            <div style={{ fontSize: '0.72rem', color: '#71717a', fontWeight: 500 }}>Estimated Loss Rate</div>
            <div className="font-mono" style={{ fontSize: '1.2rem', fontWeight: 700, color: '#f43f5e', marginTop: '2px' }}>
              {evidenceDisplay}
            </div>
            <div style={{ fontSize: '0.68rem', color: '#a1a1aa', marginTop: '2px' }}>
              Waste: {lossRateLph.toFixed(2)} LPH
            </div>
          </div>

          <div style={{ background: '#141417', padding: '12px 14px', borderRadius: '6px', border: '1px solid #222225' }}>
            <div style={{ fontSize: '0.72rem', color: '#71717a', fontWeight: 500 }}>Daily Cost at Risk</div>
            <div className="font-mono" style={{ fontSize: '1.2rem', fontWeight: 700, color: '#f59e0b', marginTop: '2px' }}>
              ₹{estimatedCostInr.toFixed(2)}
            </div>
            <div style={{ fontSize: '0.68rem', color: '#a1a1aa', marginTop: '2px' }}>
              ₹0.15 / L commercial tariff
            </div>
          </div>

          <div style={{ background: '#141417', padding: '12px 14px', borderRadius: '6px', border: '1px solid #222225' }}>
            <div style={{ fontSize: '0.72rem', color: '#71717a', fontWeight: 500 }}>Priority Score (0–100)</div>
            <div className="font-mono" style={{ fontSize: '1.2rem', fontWeight: 700, color: priorityScore >= 80 ? '#f43f5e' : priorityScore >= 50 ? '#f59e0b' : '#38bdf8', marginTop: '2px' }}>
              {priorityScore.toFixed(1)}
            </div>
            <div style={{ fontSize: '0.68rem', color: '#a1a1aa', marginTop: '2px' }}>
              Status: <span style={{ color: '#fbbf24', textTransform: 'uppercase', fontWeight: 600 }}>{status}</span>
            </div>
          </div>

          <div style={{ background: '#141417', padding: '12px 14px', borderRadius: '6px', border: '1px solid #222225' }}>
            <div style={{ fontSize: '0.72rem', color: '#71717a', fontWeight: 500 }}>Engine Confidence</div>
            <div className="font-mono" style={{ fontSize: '1.2rem', fontWeight: 700, color: '#4ade80', marginTop: '2px' }}>
              {(confidence * 100).toFixed(0)}%
            </div>
            <div style={{ fontSize: '0.68rem', color: '#a1a1aa', marginTop: '2px' }}>
              Sensor Health: {(sensorHealthScore * 100).toFixed(0)}%
            </div>
          </div>
        </div>

        {/* Section 2: Evidence Timeline Sequence (Requirement 8) */}
        <div style={{
          background: '#141417',
          border: '1px solid #27272a',
          borderRadius: '8px',
          padding: '16px 18px',
          marginBottom: '22px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
            <div style={{ fontSize: '0.78rem', fontWeight: 600, color: '#f4f4f5', letterSpacing: '0.04em', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Clock size={14} color="#38bdf8" />
              Evidence Timeline Progression
            </div>
            <span style={{ fontSize: '0.7rem', color: '#71717a' }} className="font-mono">
              Duration: {formatDuration(durationSeconds)}
            </span>
          </div>

          {/* Stepped horizontal sequence */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
            gap: '12px',
            position: 'relative'
          }}>
            {/* Step 1: Trigger / Candidate Start */}
            <div style={{
              background: '#18181b',
              border: '1px solid #27272a',
              borderRadius: '6px',
              padding: '10px 12px',
              display: 'flex',
              flexDirection: 'column',
              gap: '4px'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.68rem', color: '#a1a1aa', fontWeight: 600 }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#f59e0b' }} />
                1. TRIGGER START
              </div>
              <div className="font-mono" style={{ fontSize: '0.85rem', fontWeight: 600, color: '#f4f4f5' }}>
                {triggerTimeStr}
              </div>
              <div style={{ fontSize: '0.68rem', color: '#71717a' }}>
                Idle flow elevated &gt; UCL threshold
              </div>
            </div>

            {/* Step 2: Confirmation Window Elapsed */}
            <div style={{
              background: '#18181b',
              border: '1px solid #27272a',
              borderRadius: '6px',
              padding: '10px 12px',
              display: 'flex',
              flexDirection: 'column',
              gap: '4px'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.68rem', color: '#38bdf8', fontWeight: 600 }}>
                <Activity size={12} color="#38bdf8" />
                2. CONFIRMATION
              </div>
              <div className="font-mono" style={{ fontSize: '0.85rem', fontWeight: 600, color: '#38bdf8' }}>
                {confirmationWindowSeconds}s ({Math.round(confirmationWindowSeconds / 60)} min)
              </div>
              <div style={{ fontSize: '0.68rem', color: '#71717a' }}>
                Tier confirmation window observed
              </div>
            </div>

            {/* Step 3: Dispatch Timestamp */}
            <div style={{
              background: '#18181b',
              border: '1px solid #27272a',
              borderRadius: '6px',
              padding: '10px 12px',
              display: 'flex',
              flexDirection: 'column',
              gap: '4px'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.68rem', color: '#f43f5e', fontWeight: 600 }}>
                <AlertTriangle size={12} color="#f43f5e" />
                3. DISPATCHED
              </div>
              <div className="font-mono" style={{ fontSize: '0.82rem', fontWeight: 600, color: '#f4f4f5' }}>
                {formatTimestamp(detectedAtStr)}
              </div>
              <div style={{ fontSize: '0.68rem', color: '#71717a' }}>
                High-confidence alert committed to DB
              </div>
            </div>

            {/* Step 4: Current Operations Status */}
            <div style={{
              background: '#18181b',
              border: '1px solid #27272a',
              borderRadius: '6px',
              padding: '10px 12px',
              display: 'flex',
              flexDirection: 'column',
              gap: '4px'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.68rem', color: status === 'resolved' ? '#4ade80' : '#fbbf24', fontWeight: 600 }}>
                <CheckCircle2 size={12} color={status === 'resolved' ? '#4ade80' : '#fbbf24'} />
                4. CURRENT STATUS
              </div>
              <div className="font-mono" style={{ fontSize: '0.85rem', fontWeight: 700, color: status === 'resolved' ? '#4ade80' : '#fbbf24', textTransform: 'uppercase' }}>
                {status}
              </div>
              <div style={{ fontSize: '0.68rem', color: '#71717a' }}>
                Active for {formatDuration(durationSeconds)}
              </div>
            </div>
          </div>
        </div>

        {/* Section: Intervention Impact (Requirement 6 — Appears ONLY when ticket status is Resolved) */}
        {isResolved && (
          <div
            id="intervention-impact-section"
            style={{
              background: 'linear-gradient(180deg, #0d1a14 0%, #0a120e 100%)',
              border: '1px solid #166534',
              borderRadius: '8px',
              padding: '16px 18px',
              marginBottom: '22px',
              position: 'relative',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px', borderBottom: '1px solid #14532d', paddingBottom: '10px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <div style={{ background: '#166534', padding: '6px', borderRadius: '6px' }}>
                  <Droplets size={16} color="#86efac" />
                </div>
                <div>
                  <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#f0fdf4', letterSpacing: '0.02em', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    INTERVENTION IMPACT
                    <span style={{ fontSize: '0.65rem', background: '#15803d', color: '#dcfce7', padding: '2px 7px', borderRadius: '10px', textTransform: 'uppercase', fontWeight: 600 }}>
                      Resolved Incident
                    </span>
                  </div>
                  <div style={{ fontSize: '0.68rem', color: '#86efac', marginTop: '1px' }}>
                    Incident water waste vs. 6-hour unaddressed counterfactual baseline
                  </div>
                </div>
              </div>
              <div style={{ fontSize: '0.7rem', color: '#4ade80', fontFamily: 'monospace', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <CheckCircle2 size={13} color="#4ade80" />
                <span>RESOLVED INTERVENTION</span>
              </div>
            </div>

            {/* Stepped horizontal sequence / 3 Metric Tiles styled consistently with Evidence Timeline */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
              gap: '12px',
              position: 'relative',
              marginBottom: '10px',
            }}>
              {/* Tile 1: Water Lost During Incident */}
              <div style={{
                background: '#141417',
                border: '1px solid #27272a',
                borderRadius: '6px',
                padding: '12px 14px',
                display: 'flex',
                flexDirection: 'column',
                gap: '4px',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.68rem', color: '#f43f5e', fontWeight: 600 }}>
                  <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#f43f5e' }} />
                  WATER LOST DURING INCIDENT
                </div>
                <div className="font-mono" style={{ fontSize: '1.25rem', fontWeight: 700, color: '#f43f5e' }}>
                  {waterLostLiters.toFixed(1)} L
                </div>
                <div style={{ fontSize: '0.68rem', color: '#f59e0b' }} className="font-mono">
                  Cost impact: ₹{lostCostInr.toFixed(2)}
                </div>
                <div style={{ fontSize: '0.65rem', color: '#71717a' }}>
                  Incident active: {formatDuration(durationSeconds)}
                </div>
              </div>

              {/* Tile 2: Estimated Water Avoided */}
              <div style={{
                background: '#141417',
                border: '1px solid #27272a',
                borderRadius: '6px',
                padding: '12px 14px',
                display: 'flex',
                flexDirection: 'column',
                gap: '4px',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.68rem', color: '#4ade80', fontWeight: 600 }}>
                  <Droplets size={12} color="#4ade80" />
                  ESTIMATED WATER AVOIDED
                </div>
                <div className="font-mono" style={{ fontSize: '1.25rem', fontWeight: 700, color: '#4ade80' }}>
                  {estimatedAvoidedLiters.toFixed(1)} L
                </div>
                <div style={{ fontSize: '0.68rem', color: '#86efac' }}>
                  Prevented continuous leak
                </div>
                <div style={{ fontSize: '0.65rem', color: '#71717a' }}>
                  6h unaddressed counterfactual estimate
                </div>
              </div>

              {/* Tile 3: Estimated Cost Saved */}
              <div style={{
                background: '#141417',
                border: '1px solid #27272a',
                borderRadius: '6px',
                padding: '12px 14px',
                display: 'flex',
                flexDirection: 'column',
                gap: '4px',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.68rem', color: '#38bdf8', fontWeight: 600 }}>
                  <TrendingDown size={12} color="#38bdf8" />
                  ESTIMATED COST SAVED
                </div>
                <div className="font-mono" style={{ fontSize: '1.25rem', fontWeight: 700, color: '#38bdf8' }}>
                  ₹{avoidedCostInr.toFixed(2)}
                </div>
                <div style={{ fontSize: '0.68rem', color: '#a1a1aa' }}>
                  ₹0.15 / L commercial tariff
                </div>
                <div style={{ fontSize: '0.65rem', color: '#71717a' }}>
                  Avoided facility utility expense
                </div>
              </div>
            </div>

            {/* Clear estimate disclosure note */}
            <div style={{ fontSize: '0.68rem', color: '#86efac', opacity: 0.85, fontStyle: 'italic', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span>* Estimated water saved is a counterfactual projection (observed flow rate projected forward against a 6-hour unaddressed baseline).</span>
            </div>
          </div>
        )}

        {/* Section: AI Incident Investigator (Requirement 5) */}
        {(canInvestigate || investigation || investigating || investigationError) && (
          <div
            id="ai-investigator-section"
            style={{
              background: 'linear-gradient(180deg, #121124 0%, #0d0d14 100%)',
              border: '1px solid #312e81',
              borderRadius: '8px',
              padding: '16px 18px',
              marginBottom: '22px',
              position: 'relative'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px', borderBottom: '1px solid #1e1b4b', paddingBottom: '10px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <div style={{ background: '#312e81', padding: '6px', borderRadius: '6px' }}>
                  <Sparkles size={16} color="#a5b4fc" />
                </div>
                <div>
                  <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#f5f3ff', letterSpacing: '0.02em', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    AI INCIDENT INVESTIGATOR
                    <span style={{ fontSize: '0.65rem', background: '#3730a3', color: '#c7d2fe', padding: '2px 7px', borderRadius: '10px', textTransform: 'uppercase', fontWeight: 600 }}>
                      Autonomous Diagnostics
                    </span>
                  </div>
                  <div style={{ fontSize: '0.68rem', color: '#818cf8', marginTop: '1px' }}>
                    Bounded inference over ticket, detection event, telemetry window & baseline profile
                  </div>
                </div>
              </div>

              {canInvestigate && !investigation && !investigating && (
                <button
                  id="btn-section-ai-investigate"
                  onClick={handleRunInvestigation}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '6px 14px',
                    background: '#4338ca',
                    border: '1px solid #6366f1',
                    borderRadius: '6px',
                    color: '#ffffff',
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  <Sparkles size={13} />
                  <span>Run AI Diagnosis</span>
                </button>
              )}
            </div>

            {/* Loading State (Non-blocking) */}
            {investigating && (
              <div style={{ padding: '22px 16px', textAlign: 'center', color: '#c7d2fe' }}>
                <Loader2 size={24} className="animate-spin" style={{ margin: '0 auto 10px auto', color: '#818cf8' }} />
                <div style={{ fontSize: '0.82rem', fontWeight: 600, color: '#f5f3ff' }}>
                  Synthesizing telemetry data & hydraulic evidence with diagnostic model...
                </div>
                <div style={{ fontSize: '0.72rem', color: '#a5b4fc', marginTop: '4px' }}>
                  Evaluating breach margins, sensor reliability, and operational risk. The rest of the modal remains active.
                </div>
              </div>
            )}

            {/* Error State */}
            {investigationError && !investigating && (
              <div style={{ padding: '12px 14px', background: '#450a0a', border: '1px solid #991b1b', borderRadius: '6px', color: '#fecaca', fontSize: '0.75rem' }}>
                <div style={{ fontWeight: 600, marginBottom: '2px' }}>Investigation Notice</div>
                {investigationError}
              </div>
            )}

            {/* Prompt to run investigation if not yet run */}
            {!investigation && !investigating && !investigationError && (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '6px 2px' }}>
                <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                  Click <strong style={{ color: '#c7d2fe' }}>Run AI Diagnosis</strong> to trigger autonomous analysis of root causes, telemetry data points, and recommended technician actions.
                </div>
              </div>
            )}

            {/* Rendered Diagnostic Report */}
            {investigation && !investigating && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                {/* 1. Summary */}
                <div style={{ background: '#18181b', padding: '12px 14px', borderRadius: '6px', border: '1px solid #27272a' }}>
                  <div style={{ fontSize: '0.68rem', fontWeight: 600, color: '#a1a1aa', textTransform: 'uppercase', marginBottom: '4px', letterSpacing: '0.03em' }}>
                    Diagnostic Summary
                  </div>
                  <div style={{ fontSize: '0.82rem', color: '#f4f4f5', lineHeight: 1.55 }}>
                    {investigation.summary}
                  </div>
                </div>

                {/* 2. Likely Cause */}
                <div style={{ background: '#1c1917', border: '1px solid #44403c', padding: '12px 14px', borderRadius: '6px', display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
                  <Wrench size={16} color="#fbbf24" style={{ flexShrink: 0, marginTop: '2px' }} />
                  <div>
                    <div style={{ fontSize: '0.68rem', fontWeight: 600, color: '#f59e0b', textTransform: 'uppercase', marginBottom: '2px', letterSpacing: '0.03em' }}>
                      Likely Root Cause
                    </div>
                    <div style={{ fontSize: '0.82rem', color: '#fafaf9', lineHeight: 1.5 }}>
                      {investigation.likely_cause}
                    </div>
                  </div>
                </div>

                {/* 3. Evidence Bullets & Recommended Actions Grid */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '12px' }}>
                  {/* Evidence Bullets */}
                  <div style={{ background: '#141417', border: '1px solid #27272a', padding: '12px 14px', borderRadius: '6px' }}>
                    <div style={{ fontSize: '0.7rem', fontWeight: 600, color: '#38bdf8', textTransform: 'uppercase', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <Activity size={13} color="#38bdf8" />
                      Verified Evidence Data Points
                    </div>
                    <ul style={{ margin: 0, paddingLeft: '16px', fontSize: '0.75rem', color: '#d4d4d8', lineHeight: 1.6 }}>
                      {investigation.evidence.map((bullet, idx) => (
                        <li key={idx} style={{ marginBottom: '4px' }}>
                          {bullet}
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* Recommended Actions */}
                  <div style={{ background: '#141417', border: '1px solid #27272a', padding: '12px 14px', borderRadius: '6px' }}>
                    <div style={{ fontSize: '0.7rem', fontWeight: 600, color: '#4ade80', textTransform: 'uppercase', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <ListChecks size={13} color="#4ade80" />
                      Recommended Technician Actions
                    </div>
                    <ol style={{ margin: 0, paddingLeft: '16px', fontSize: '0.75rem', color: '#d4d4d8', lineHeight: 1.6 }}>
                      {investigation.recommended_actions.map((act, idx) => (
                        <li key={idx} style={{ marginBottom: '4px' }}>
                          {act}
                        </li>
                      ))}
                    </ol>
                  </div>
                </div>

                {/* 4. Operational & Clinical Impact */}
                <div style={{ background: '#18181b', padding: '10px 14px', borderRadius: '6px', border: '1px solid #27272a' }}>
                  <div style={{ fontSize: '0.68rem', fontWeight: 600, color: '#a1a1aa', textTransform: 'uppercase', marginBottom: '3px' }}>
                    Operational & Clinical Impact
                  </div>
                  <div style={{ fontSize: '0.78rem', color: '#e4e4e7', lineHeight: 1.5 }}>
                    {investigation.impact}
                  </div>
                </div>

                {/* 5. Visible Risk Note */}
                <div style={{ background: '#261b17', border: '1px solid #b45309', padding: '10px 14px', borderRadius: '6px', display: 'flex', gap: '8px', alignItems: 'flex-start' }}>
                  <AlertTriangle size={15} color="#f59e0b" style={{ flexShrink: 0, marginTop: '2px' }} />
                  <div>
                    <div style={{ fontSize: '0.68rem', fontWeight: 600, color: '#f59e0b', textTransform: 'uppercase', letterSpacing: '0.03em' }}>
                      Safety & Clinical Risk Note
                    </div>
                    <div style={{ fontSize: '0.78rem', color: '#fef3c7', marginTop: '2px', lineHeight: 1.45 }}>
                      {investigation.risk_note}
                    </div>
                  </div>
                </div>

                {/* 6. Fixed Safety Line */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.7rem', color: '#a1a1aa', fontStyle: 'italic', paddingTop: '4px' }}>
                  <ShieldAlert size={13} color="#f59e0b" />
                  <span>AI-generated decision support — technician verification required.</span>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Collapsible Technical Diagnostics Toggle (Requirement 2) */}
        <div style={{ marginBottom: '20px', borderTop: '1px solid #222225', paddingTop: '16px' }}>
          <button
            id="btn-toggle-diagnostics"
            type="button"
            onClick={() => setShowDiagnostics(!showDiagnostics)}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              width: '100%',
              padding: '12px 16px',
              background: showDiagnostics ? '#18181b' : '#141417',
              border: `1px solid ${showDiagnostics ? '#3f3f46' : '#27272a'}`,
              borderRadius: '8px',
              color: '#ededed',
              cursor: 'pointer',
              fontSize: '0.8rem',
              fontWeight: 600,
              letterSpacing: '0.02em',
              transition: 'all 0.15s ease',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <BarChart2 size={15} color="#a1a1aa" />
              <span>Sensor-Level Technical Diagnostics</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#38bdf8', fontSize: '0.75rem', fontFamily: 'monospace' }}>
              <span>{showDiagnostics ? 'Hide sensor-level diagnostics ▴' : 'Show sensor-level diagnostics ▾'}</span>
              {showDiagnostics ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
            </div>
          </button>

          {showDiagnostics && (
            <div id="technical-diagnostics-section" style={{ marginTop: '14px', padding: '16px', background: '#111113', border: '1px solid #222225', borderRadius: '8px' }}>
              {/* Section 3: Diagnostic Telemetry & Baseline Metadata */}
              <div style={{ marginBottom: '22px' }}>
                <h3 style={{ fontSize: '0.82rem', fontWeight: 600, color: '#f4f4f5', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px', letterSpacing: '0.03em', textTransform: 'uppercase' }}>
                  <BarChart2 size={14} color="#71717a" />
                  Statistical Baseline & Diagnostic State
                </h3>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '12px' }}>
                  <div style={{ background: '#141417', padding: '10px 12px', borderRadius: '6px', border: '1px solid #222225' }}>
                    <div style={{ fontSize: '0.7rem', color: '#71717a', fontWeight: 500 }}>Current Flow (Latest)</div>
                    <div className="font-mono" style={{ fontSize: '0.92rem', fontWeight: 600, color: currentFlowLpm > ucl ? '#f87171' : '#ededed', marginTop: '2px' }}>
                      {currentFlowLpm.toFixed(3)} L/min
                    </div>
                  </div>

                  <div style={{ background: '#141417', padding: '10px 12px', borderRadius: '6px', border: '1px solid #222225' }}>
                    <div style={{ fontSize: '0.7rem', color: '#71717a', fontWeight: 500 }}>Mean Idle Flow (μ)</div>
                    <div className="font-mono" style={{ fontSize: '0.92rem', fontWeight: 600, color: '#ededed', marginTop: '2px' }}>
                      {meanOffFlow.toFixed(4)} L/min
                    </div>
                  </div>

                  <div style={{ background: '#141417', padding: '10px 12px', borderRadius: '6px', border: '1px solid #222225' }}>
                    <div style={{ fontSize: '0.7rem', color: '#71717a', fontWeight: 500 }}>Upper Control Limit (UCL)</div>
                    <div className="font-mono" style={{ fontSize: '0.92rem', fontWeight: 600, color: '#f87171', marginTop: '2px' }}>
                      {ucl.toFixed(4)} L/min
                    </div>
                  </div>

                  <div style={{ background: '#141417', padding: '10px 12px', borderRadius: '6px', border: '1px solid #222225' }}>
                    <div style={{ fontSize: '0.7rem', color: '#71717a', fontWeight: 500 }}>Occupancy State</div>
                    <div className="font-mono" style={{ fontSize: '0.88rem', fontWeight: 600, color: occupancyState === 0 ? '#4ade80' : '#fbbf24', marginTop: '2px' }}>
                      {occupancyState === 0 ? '0 (Unoccupied)' : '1 (Occupied)'}
                    </div>
                  </div>

                  <div style={{ background: '#141417', padding: '10px 12px', borderRadius: '6px', border: '1px solid #222225' }}>
                    <div style={{ fontSize: '0.7rem', color: '#71717a', fontWeight: 500 }}>Last Flush Recorded</div>
                    <div className="font-mono" style={{ fontSize: '0.82rem', fontWeight: 600, color: '#ededed', marginTop: '2px' }}>
                      {lastFlushAt ? formatTimestamp(lastFlushAt) : 'None prior'}
                    </div>
                  </div>

                  <div style={{ background: '#141417', padding: '10px 12px', borderRadius: '6px', border: '1px solid #222225' }}>
                    <div style={{ fontSize: '0.7rem', color: '#71717a', fontWeight: 500 }}>Warmup Adaptation</div>
                    <div className="font-mono" style={{ fontSize: '0.82rem', fontWeight: 600, color: baseline?.warmup_complete ? '#4ade80' : '#fbbf24', marginTop: '2px' }}>
                      {baseline?.warmup_complete ? 'WARMUP COMPLETE' : 'WARMING UP'}
                    </div>
                  </div>
                </div>
              </div>

              {/* Section 4: Telemetry Readings Time-Series Bar Chart */}
              <div style={{ borderTop: '1px solid #222225', paddingTop: '18px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                  <div style={{ fontSize: '0.78rem', fontWeight: 600, color: '#ededed' }} className="font-mono">
                    RAW SENSOR TELEMETRY READINGS (/fixtures/{fixtureId}/telemetry)
                  </div>
                  {loading && <div style={{ fontSize: '0.72rem', color: '#71717a' }} className="font-mono">Loading readings...</div>}
                </div>

                {telemetry.length === 0 ? (
                  <div style={{ padding: '20px', textAlign: 'center', color: '#71717a', fontSize: '0.78rem' }}>
                    No telemetry readings stored for this fixture around the detection timestamp.
                  </div>
                ) : (
                  <div style={{ display: 'flex', alignItems: 'flex-end', gap: '6px', height: '115px', padding: '14px 0 4px 0', borderBottom: '1px solid #222225', overflowX: 'auto' }}>
                    {telemetry.slice(0, 20).map((pt, idx) => {
                      const isBreach = pt.flow_rate_lpm > ucl;
                      const timeStr = new Date(pt.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });

                      return (
                        <div key={idx} style={{ flex: 1, minWidth: '26px', display: 'flex', flexDirection: 'column', alignItems: 'center', height: '100%', justifyContent: 'flex-end' }}>
                          <div style={{
                            width: '100%',
                            maxWidth: '18px',
                            height: `${Math.min(100, Math.max(10, pt.flow_rate_lpm * 110))}%`,
                            background: isBreach ? '#f43f5e' : '#38bdf8',
                            borderRadius: '2px',
                            position: 'relative'
                          }}>
                            <span className="font-mono" style={{ position: 'absolute', top: '-16px', left: '50%', transform: 'translateX(-50%)', fontSize: '0.58rem', color: isBreach ? '#f43f5e' : '#a1a1aa' }}>
                              {pt.flow_rate_lpm.toFixed(2)}
                            </span>
                          </div>
                          <span className="font-mono" style={{ fontSize: '0.55rem', color: '#71717a', marginTop: '6px', whiteSpace: 'nowrap' }}>{timeStr}</span>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid #222225', paddingTop: '16px' }}>
          <div style={{ fontSize: '0.7rem', color: '#71717a' }} className="font-mono">
            Detection Rule: {detectionRule} • Tier: {tier} ({confirmationWindowSeconds}s window)
          </div>
          <button
            onClick={onClose}
            className="btn-pill-primary"
            style={{ padding: '8px 18px', background: '#38bdf8', color: '#09090b', fontWeight: 600, fontSize: '0.8rem', borderRadius: '6px', border: 'none', cursor: 'pointer' }}
          >
            Close window
          </button>
        </div>
      </div>
    </div>
  );
};
