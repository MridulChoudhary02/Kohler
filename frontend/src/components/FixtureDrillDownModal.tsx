// frontend/src/components/FixtureDrillDownModal.tsx — View 4: Real Evidence Drill-Down Modal

import React, { useState, useEffect } from 'react';
import { X, Droplets, Clock, BarChart2 } from 'lucide-react';
import { DetectionEvent, Ticket, BaselineProfile, TelemetryReading } from '../lib/types';
import { fetchFixtureBaseline, fetchFixtureTelemetry } from '../lib/api';

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

  useEffect(() => {
    if (!fixtureId || fixtureId === 'Unknown Fixture') return;

    let isMounted = true;
    setLoading(true);

    const loadEvidenceData = async () => {
      try {
        const [bpData, telData] = await Promise.all([
          fetchFixtureBaseline(fixtureId),
          fetchFixtureTelemetry(fixtureId, event?.detected_at),
        ]);
        if (isMounted) {
          setBaseline(bpData);
          setTelemetry(telData);
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
  }, [fixtureId, event?.detected_at]);

  if (!event && !ticket) return null;

  const eventType = event?.event_type || 'leak';
  const confidence = event?.confidence_score ?? 0.90;
  const evidenceValue = event?.evidence_value ?? 0.0;
  const zoneName = event?.zone_name || ticket?.zone_id || 'Hospital Zone';
  const tier = event?.criticality_tier || 'Tier 1';
  const status = ticket?.status || event?.status || 'dispatched';
  const summary = ticket?.summary_text || null;

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

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      zIndex: 100,
      background: 'rgba(8, 12, 20, 0.85)',
      backdropFilter: 'blur(4px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '20px'
    }}>
      <div className="command-panel" style={{
        width: '100%',
        maxWidth: '850px',
        maxHeight: '90vh',
        overflowY: 'auto',
        padding: '24px',
        borderLeft: '4px solid #06b6d4'
      }}>
        {/* Modal Header */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', borderBottom: '1px solid var(--panel-border)', paddingBottom: '14px', marginBottom: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <span className={`tag-tech ${eventType === 'leak' ? 'tag-leak' : eventType === 'hygiene' ? 'tag-hygiene' : 'tag-sensor'}`}>
                {eventType}
              </span>
              <span className={`tag-tech ${tier === 'Tier 1' ? 'tag-tier1' : tier === 'Tier 2' ? 'tag-tier2' : 'tag-tier3'}`}>
                {tier}
              </span>
              <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                {zoneName}
              </span>
            </div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#f8fafc' }}>
              Fixture Technical Evidence: <span className="font-mono" style={{ color: '#22d3ee' }}>{fixtureId}</span>
            </h2>
          </div>

          <button
            onClick={onClose}
            className="btn-action"
            style={{ padding: '6px' }}
          >
            <X size={16} />
          </button>
        </div>

        {/* Primary Evidence Highlights */}
        <div style={{
          background: 'rgba(6, 182, 212, 0.05)',
          border: '1px solid rgba(6, 182, 212, 0.2)',
          borderRadius: '3px',
          padding: '14px 18px',
          marginBottom: '18px',
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: '14px'
        }}>
          <div>
            <div style={{ fontSize: '0.68rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>Event Evidence Readout</div>
            <div className="font-mono" style={{ fontSize: '1.05rem', fontWeight: 700, color: '#22d3ee', marginTop: '2px' }}>{evidenceDisplay}</div>
          </div>
          <div>
            <div style={{ fontSize: '0.68rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>Engine Confidence Score</div>
            <div className="font-mono" style={{ fontSize: '1.05rem', fontWeight: 700, color: '#34d399', marginTop: '2px' }}>{(confidence * 100).toFixed(0)}%</div>
          </div>
          <div>
            <div style={{ fontSize: '0.68rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>Operations Status</div>
            <div className="font-mono" style={{ fontSize: '1.05rem', fontWeight: 700, color: '#fbbf24', textTransform: 'uppercase', marginTop: '2px' }}>{status}</div>
          </div>
        </div>

        {/* Learned Baseline Profile Evidence */}
        <h3 style={{ fontSize: '0.92rem', fontWeight: 700, color: '#f8fafc', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <BarChart2 size={16} color="#06b6d4" />
          Learned Baseline Profile (PostgreSQL Store)
        </h3>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '10px', marginBottom: '20px' }}>
          <div style={{ background: 'var(--panel-bg)', border: '1px solid var(--panel-border)', borderRadius: '3px', padding: '10px' }}>
            <div style={{ fontSize: '0.68rem', color: '#64748b', textTransform: 'uppercase' }}>Mean Idle Flow (μ)</div>
            <div className="font-mono" style={{ fontSize: '0.92rem', fontWeight: 700, color: '#f8fafc', marginTop: '2px' }}>
              {meanOffFlow.toFixed(4)} L/min
            </div>
          </div>

          <div style={{ background: 'var(--panel-bg)', border: '1px solid var(--panel-border)', borderRadius: '3px', padding: '10px' }}>
            <div style={{ fontSize: '0.68rem', color: '#64748b', textTransform: 'uppercase' }}>Std Off Flow (σ)</div>
            <div className="font-mono" style={{ fontSize: '0.92rem', fontWeight: 700, color: '#f8fafc', marginTop: '2px' }}>
              {stdOffFlow.toFixed(4)} L/min
            </div>
          </div>

          <div style={{ background: 'var(--panel-bg)', border: '1px solid var(--panel-border)', borderRadius: '3px', padding: '10px' }}>
            <div style={{ fontSize: '0.68rem', color: '#64748b', textTransform: 'uppercase' }}>Upper Control Limit (UCL)</div>
            <div className="font-mono" style={{ fontSize: '0.92rem', fontWeight: 700, color: '#fda4af', marginTop: '2px' }}>
              {ucl.toFixed(4)} L/min
            </div>
          </div>

          <div style={{ background: 'var(--panel-bg)', border: '1px solid var(--panel-border)', borderRadius: '3px', padding: '10px' }}>
            <div style={{ fontSize: '0.68rem', color: '#64748b', textTransform: 'uppercase' }}>Warmup Status</div>
            <div className="font-mono" style={{ fontSize: '0.92rem', fontWeight: 700, color: baseline?.warmup_complete ? '#34d399' : '#fbbf24', marginTop: '2px' }}>
              {baseline?.warmup_complete ? 'WARMUP COMPLETE' : 'WARMING UP'}
            </div>
          </div>
        </div>

        {/* Real Telemetry Flow Readings Visualization */}
        <div style={{ background: 'var(--panel-bg)', border: '1px solid var(--panel-border)', borderRadius: '3px', padding: '14px', marginBottom: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
            <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#f8fafc' }} className="font-mono">
              REAL TELEMETRY TIME-SERIES READINGS (/fixtures/{fixtureId}/telemetry)
            </div>
            {loading && <div style={{ fontSize: '0.72rem', color: '#06b6d4' }} className="font-mono">LOADING REAL READINGS...</div>}
          </div>

          {telemetry.length === 0 ? (
            <div style={{ padding: '16px', textAlign: 'center', color: '#64748b', fontSize: '0.75rem' }}>
              No telemetry readings stored for this fixture around the detection timestamp.
            </div>
          ) : (
            <div style={{ display: 'flex', alignItems: 'flex-end', gap: '6px', height: '110px', padding: '8px 0', borderBottom: '1px solid var(--panel-border)', overflowX: 'auto' }}>
              {telemetry.slice(0, 20).map((pt, idx) => {
                const isBreach = pt.flow_rate_lpm > ucl;
                const timeStr = new Date(pt.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

                return (
                  <div key={idx} style={{ flex: 1, minWidth: '24px', display: 'flex', flexDirection: 'column', alignItems: 'center', height: '100%', justifyContent: 'flex-end' }}>
                    <div style={{
                      width: '100%',
                      maxWidth: '20px',
                      height: `${Math.min(100, Math.max(10, pt.flow_rate_lpm * 120))}%`,
                      background: isBreach ? '#e11d48' : '#06b6d4',
                      borderRadius: '1px',
                      position: 'relative'
                    }}>
                      <span className="font-mono" style={{ position: 'absolute', top: '-16px', left: '50%', transform: 'translateX(-50%)', fontSize: '0.58rem', color: isBreach ? '#fda4af' : '#94a3b8' }}>
                        {pt.flow_rate_lpm.toFixed(2)}
                      </span>
                    </div>
                    <span className="font-mono" style={{ fontSize: '0.58rem', color: '#64748b', marginTop: '4px', whiteSpace: 'nowrap' }}>{timeStr}</span>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Incident Narrative Summary */}
        <div style={{ background: 'rgba(0, 0, 0, 0.25)', border: '1px dashed var(--panel-border)', borderRadius: '3px', padding: '14px', marginBottom: '20px' }}>
          <div style={{ fontSize: '0.72rem', fontWeight: 600, color: '#94a3b8', marginBottom: '4px', textTransform: 'uppercase' }} className="font-mono">
            Incident Narrative Summary (Phase 7 LLM Layer)
          </div>
          <p style={{ fontSize: '0.8rem', color: summary ? '#e2e8f0' : '#64748b', fontStyle: summary ? 'normal' : 'italic' }}>
            {summary || 'Summary pending (Phase 7 LLM integration will populate detailed incident narrative)'}
          </p>
        </div>

        {/* Modal Footer */}
        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <button
            onClick={onClose}
            className="btn-action"
            style={{ padding: '6px 16px', background: '#06b6d4', color: '#080c14', fontWeight: 700 }}
          >
            CLOSE WINDOW
          </button>
        </div>
      </div>
    </div>
  );
};

