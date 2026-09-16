// frontend/src/components/FixtureDrillDownModal.tsx — View 4: Fixture Technical Evidence Modal

import React, { useState, useEffect } from 'react';
import { X, BarChart2 } from 'lucide-react';
import { DetectionEvent, Ticket, BaselineProfile, TelemetryReading } from '../lib/types';
import { fetchFixtureBaseline, fetchFixtureTelemetry, fetchTickets } from '../lib/api';

interface FixtureDrillDownModalProps {
  event: DetectionEvent | null;
  ticket: Ticket | null;
  onClose: () => void;
}

export const FixtureDrillDownModal: React.FC<FixtureDrillDownModalProps> = ({
  event,
  ticket,
  onClose,
}) => {
  const [baseline, setBaseline] = useState<BaselineProfile | null>(null);
  const [telemetry, setTelemetry] = useState<TelemetryReading[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  const fixtureId = event?.fixture_id || 'Unknown Fixture';

  const [activeTicket, setActiveTicket] = useState<Ticket | null>(ticket);

  useEffect(() => {
    setActiveTicket(ticket);
  }, [ticket]);

  useEffect(() => {
    if (!fixtureId || fixtureId === 'Unknown Fixture') return;

    let isMounted = true;
    setLoading(true);

    const loadEvidenceData = async () => {
      try {
        const [bpData, telData, ticketsData] = await Promise.all([
          fetchFixtureBaseline(fixtureId),
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
  }, [fixtureId, event?.detected_at, ticket, event?.event_id]);

  if (!event && !ticket) return null;

  const eventType = event?.event_type || 'leak';
  const confidence = event?.confidence_score ?? 0.90;
  const evidenceValue = event?.evidence_value ?? 0.0;
  const zoneName = event?.zone_name || ticket?.zone_id || 'Hospital Zone';
  const tier = event?.criticality_tier || 'Tier 1';
  const status = activeTicket?.status || ticket?.status || event?.status || 'dispatched';
  const summary = activeTicket?.summary_text || ticket?.summary_text || null;

  let evidenceDisplay = 'N/A';
  if (evidenceValue !== null && evidenceValue !== undefined) {
    if (eventType === 'leak') {
      evidenceDisplay = `${evidenceValue.toFixed(2)} L/hr waste`;
    } else if (eventType === 'hygiene') {
      evidenceDisplay = `${evidenceValue.toFixed(1)}m to breach`;
    } else if (eventType === 'sensor_fault') {
      evidenceDisplay = `Health score ${evidenceValue.toFixed(2)}`;
    }
  }

  const meanOffFlow = baseline?.mean_off_flow ?? 0.008;
  const stdOffFlow = baseline?.std_off_flow ?? 0.0116;
  const ucl = baseline?.ucl ?? (meanOffFlow + 3.0 * stdOffFlow);

  const eventTagClass = eventType === 'leak' ? 'tag-leak' : eventType === 'hygiene' ? 'tag-hygiene' : 'tag-sensor';
  const tierTagClass = tier === 'Tier 1' ? 'tag-tier1' : tier === 'Tier 2' ? 'tag-tier2' : 'tag-tier3';

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      zIndex: 100,
      background: 'rgba(0, 0, 0, 0.82)',
      backdropFilter: 'blur(6px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '24px'
    }}>
      <div className="command-panel" style={{
        width: '100%',
        maxWidth: '820px',
        maxHeight: '90vh',
        overflowY: 'auto',
        padding: '28px',
        background: '#121212',
        border: '1px solid #262626',
        borderRadius: '8px'
      }}>
        {/* Modal Header — Linear Issue Detail View Hierarchy */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', borderBottom: '1px solid #1e1e1e', paddingBottom: '16px', marginBottom: '24px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
              <span className={`tag-tech ${eventTagClass}`}>
                <span className={`status-dot ${eventType === 'leak' ? 'status-dot-rose' : 'status-dot-cyan'}`} />
                {eventType}
              </span>
              <span className={`tag-tech ${tierTagClass}`}>
                {tier}
              </span>
              <span style={{ fontSize: '0.78rem', color: '#8f8f8f' }}>
                {zoneName}
              </span>
            </div>
            <h2 style={{ fontSize: '1.375rem', fontWeight: 700, color: '#ededed', letterSpacing: '-0.02em' }}>
              Fixture Technical Evidence: <span className="font-mono" style={{ color: '#ffffff', fontWeight: 600 }}>{fixtureId}</span>
            </h2>
          </div>

          <button
            onClick={onClose}
            className="btn-action"
            style={{ padding: '6px' }}
          >
            <X size={16} color="#8f8f8f" />
          </button>
        </div>

        {/* Primary Evidence Highlights — Clean Whitespace & Type Hierarchy */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: '20px',
          paddingBottom: '20px',
          borderBottom: '1px solid #1e1e1e',
          marginBottom: '24px'
        }}>
          <div>
            <div style={{ fontSize: '0.75rem', color: '#8f8f8f', fontWeight: 500, marginBottom: '4px' }}>Evidence Readout</div>
            <div className="font-mono" style={{ fontSize: '1.25rem', fontWeight: 700, color: '#ededed' }}>{evidenceDisplay}</div>
          </div>
          <div>
            <div style={{ fontSize: '0.75rem', color: '#8f8f8f', fontWeight: 500, marginBottom: '4px' }}>Engine Confidence</div>
            <div className="font-mono" style={{ fontSize: '1.25rem', fontWeight: 700, color: '#4ade80' }}>{(confidence * 100).toFixed(0)}%</div>
          </div>
          <div>
            <div style={{ fontSize: '0.75rem', color: '#8f8f8f', fontWeight: 500, marginBottom: '4px' }}>Operations Status</div>
            <div className="font-mono" style={{ fontSize: '1.125rem', fontWeight: 600, color: '#fbbf24', textTransform: 'uppercase' }}>{status}</div>
          </div>
        </div>

        {/* Learned Baseline Profile Evidence — No Heavy Inner Panels */}
        <div style={{ marginBottom: '24px' }}>
          <h3 style={{ fontSize: '0.9375rem', fontWeight: 600, color: '#ededed', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <BarChart2 size={16} color="#8f8f8f" />
            Learned Baseline Profile (PostgreSQL Store)
          </h3>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: '16px' }}>
            <div>
              <div style={{ fontSize: '0.72rem', color: '#8f8f8f', fontWeight: 500 }}>Mean Idle Flow (μ)</div>
              <div className="font-mono" style={{ fontSize: '0.9375rem', fontWeight: 600, color: '#ededed', marginTop: '3px' }}>
                {meanOffFlow.toFixed(4)} L/min
              </div>
            </div>

            <div>
              <div style={{ fontSize: '0.72rem', color: '#8f8f8f', fontWeight: 500 }}>Std Off Flow (σ)</div>
              <div className="font-mono" style={{ fontSize: '0.9375rem', fontWeight: 600, color: '#ededed', marginTop: '3px' }}>
                {stdOffFlow.toFixed(4)} L/min
              </div>
            </div>

            <div>
              <div style={{ fontSize: '0.72rem', color: '#8f8f8f', fontWeight: 500 }}>Upper Control Limit (UCL)</div>
              <div className="font-mono" style={{ fontSize: '0.9375rem', fontWeight: 600, color: '#f87171', marginTop: '3px' }}>
                {ucl.toFixed(4)} L/min
              </div>
            </div>

            <div>
              <div style={{ fontSize: '0.72rem', color: '#8f8f8f', fontWeight: 500 }}>Warmup Status</div>
              <div className="font-mono" style={{ fontSize: '0.875rem', fontWeight: 600, color: baseline?.warmup_complete ? '#4ade80' : '#fbbf24', marginTop: '3px' }}>
                {baseline?.warmup_complete ? 'WARMUP COMPLETE' : 'WARMING UP'}
              </div>
            </div>
          </div>
        </div>

        {/* Real Telemetry Flow Readings Visualization — Single Muted Accent Color */}
        <div style={{ borderTop: '1px solid #1e1e1e', paddingTop: '20px', marginBottom: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
            <div style={{ fontSize: '0.8125rem', fontWeight: 600, color: '#ededed' }} className="font-mono">
              TELEMETRY TIME-SERIES READINGS (/fixtures/{fixtureId}/telemetry)
            </div>
            {loading && <div style={{ fontSize: '0.75rem', color: '#8f8f8f' }} className="font-mono">Loading real readings...</div>}
          </div>

          {telemetry.length === 0 ? (
            <div style={{ padding: '20px', textAlign: 'center', color: '#525252', fontSize: '0.78rem' }}>
              No telemetry readings stored for this fixture around the detection timestamp.
            </div>
          ) : (
            <div style={{ display: 'flex', alignItems: 'flex-end', gap: '6px', height: '110px', padding: '12px 0 4px 0', borderBottom: '1px solid #1e1e1e', overflowX: 'auto' }}>
              {telemetry.slice(0, 20).map((pt, idx) => {
                const isBreach = pt.flow_rate_lpm > ucl;
                const timeStr = new Date(pt.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

                return (
                  <div key={idx} style={{ flex: 1, minWidth: '24px', display: 'flex', flexDirection: 'column', alignItems: 'center', height: '100%', justifyContent: 'flex-end' }}>
                    <div style={{
                      width: '100%',
                      maxWidth: '18px',
                      height: `${Math.min(100, Math.max(10, pt.flow_rate_lpm * 120))}%`,
                      background: isBreach ? '#f87171' : '#38bdf8',
                      borderRadius: '2px',
                      position: 'relative'
                    }}>
                      <span className="font-mono" style={{ position: 'absolute', top: '-16px', left: '50%', transform: 'translateX(-50%)', fontSize: '0.58rem', color: isBreach ? '#f87171' : '#8f8f8f' }}>
                        {pt.flow_rate_lpm.toFixed(2)}
                      </span>
                    </div>
                    <span className="font-mono" style={{ fontSize: '0.58rem', color: '#525252', marginTop: '6px', whiteSpace: 'nowrap' }}>{timeStr}</span>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Incident Narrative Summary */}
        <div style={{ borderTop: '1px solid #1e1e1e', paddingTop: '16px', marginBottom: '24px' }}>
          <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#8f8f8f', marginBottom: '6px' }}>
            Incident Narrative Summary
          </div>
          <p style={{ fontSize: '0.8125rem', color: summary ? '#ededed' : '#525252', fontStyle: summary ? 'normal' : 'italic', lineHeight: 1.5 }}>
            {summary || 'Summary pending'}
          </p>
        </div>

        {/* Modal Footer */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', borderTop: '1px solid #1e1e1e', paddingTop: '16px' }}>
          <button
            onClick={onClose}
            className="btn-pill-primary"
          >
            Close window
          </button>
        </div>
      </div>
    </div>
  );
};


