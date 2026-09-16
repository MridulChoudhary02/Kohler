// frontend/src/components/LiveAlertFeed.tsx — View 2: Live Alert Feed Stream

import React, { useState } from 'react';
import { Activity, Search, ExternalLink } from 'lucide-react';
import { DetectionEvent } from '../lib/types';

interface LiveAlertFeedProps {
  events: DetectionEvent[];
  selectedZoneId: string | null;
  onSelectEvent: (event: DetectionEvent) => void;
}

export const LiveAlertFeed: React.FC<LiveAlertFeedProps> = ({
  events,
  selectedZoneId,
  onSelectEvent,
}) => {
  const [filterType, setFilterType] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState<string>('');

  const filteredEvents = events.filter((e) => {
    if (selectedZoneId && e.zone_id !== selectedZoneId) return false;
    if (filterType !== 'all' && e.event_type !== filterType) return false;
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      const matchFixture = e.fixture_id.toLowerCase().includes(term);
      const matchZone = (e.zone_name || '').toLowerCase().includes(term);
      const matchType = e.event_type.toLowerCase().includes(term);
      if (!matchFixture && !matchZone && !matchType) return false;
    }
    return true;
  });

  return (
    <div className="command-panel" style={{ padding: '20px', marginBottom: '20px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px', marginBottom: '16px' }} className="tech-divider">
        <div style={{ paddingBottom: '12px' }}>
          <h2 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Activity size={18} color="#06b6d4" />
            Live Anomaly & Hydraulic Event Telemetry Ledger
          </h2>
          <p style={{ fontSize: '0.78rem', color: '#64748b', marginTop: '2px' }}>
            Real-time telemetry anomaly stream evaluated by layered EWMA, occupancy, and health engine.
          </p>
        </div>

        {/* Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap', marginBottom: '12px' }}>
          {/* Search box */}
          <div style={{ position: 'relative' }}>
            <Search size={14} color="#64748b" style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)' }} />
            <input
              type="text"
              placeholder="SEARCH FIXTURE OR ZONE..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="font-mono"
              style={{
                background: 'var(--panel-bg)',
                border: '1px solid var(--panel-border)',
                borderRadius: '2px',
                padding: '5px 12px 5px 30px',
                fontSize: '0.75rem',
                color: '#f8fafc',
                outline: 'none',
                width: '210px'
              }}
            />
          </div>

          {/* Event type filter tabs */}
          <div style={{ display: 'flex', background: 'rgba(0,0,0,0.3)', padding: '2px', borderRadius: '2px', border: '1px solid var(--panel-border)' }}>
            {[
              { id: 'all', label: 'ALL' },
              { id: 'leak', label: 'LEAKS' },
              { id: 'hygiene', label: 'HYGIENE' },
              { id: 'sensor_fault', label: 'SENSOR FAULTS' },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setFilterType(tab.id)}
                className="font-mono"
                style={{
                  background: filterType === tab.id ? '#06b6d4' : 'transparent',
                  color: filterType === tab.id ? '#080c14' : '#94a3b8',
                  border: 'none',
                  borderRadius: '2px',
                  padding: '3px 8px',
                  fontSize: '0.7rem',
                  fontWeight: 700,
                  cursor: 'pointer',
                  transition: 'all 0.12s ease'
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Events Table */}
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.8rem' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--panel-border)', color: '#64748b', fontFamily: 'var(--font-mono)', fontSize: '0.7rem' }}>
              <th style={{ padding: '8px 12px' }}>TYPE</th>
              <th style={{ padding: '8px 12px' }}>FIXTURE ID</th>
              <th style={{ padding: '8px 12px' }}>ZONE & TIER</th>
              <th style={{ padding: '8px 12px' }}>CONFIDENCE</th>
              <th style={{ padding: '8px 12px' }}>EVIDENCE READOUT</th>
              <th style={{ padding: '8px 12px' }}>DISPATCH STATUS</th>
              <th style={{ padding: '8px 12px' }}>TIMESTAMP (UTC)</th>
              <th style={{ padding: '8px 12px', textAlign: 'right' }}>ACTION</th>
            </tr>
          </thead>
          <tbody>
            {filteredEvents.length === 0 ? (
              <tr>
                <td colSpan={8} style={{ padding: '24px', textAlign: 'center', color: '#64748b' }}>
                  No telemetry detection events match the selected criteria.
                </td>
              </tr>
            ) : (
              filteredEvents.slice(0, 25).map((ev) => {
                const eventTagClass = ev.event_type === 'leak' ? 'tag-leak' :
                                      ev.event_type === 'hygiene' ? 'tag-hygiene' : 'tag-sensor';
                const tierTagClass = ev.criticality_tier === 'Tier 1' ? 'tag-tier1' :
                                    ev.criticality_tier === 'Tier 2' ? 'tag-tier2' :
                                    ev.criticality_tier === 'Tier 3' ? 'tag-tier3' : 'tag-tier4';

                // Format evidence display
                let evidenceDisplay = 'N/A';
                if (ev.evidence_value !== null && ev.evidence_value !== undefined) {
                  if (ev.event_type === 'leak') {
                    evidenceDisplay = `${ev.evidence_value.toFixed(1)} L/hr waste`;
                  } else if (ev.event_type === 'hygiene') {
                    evidenceDisplay = `${ev.evidence_value.toFixed(1)}m to breach`;
                  } else if (ev.event_type === 'sensor_fault') {
                    evidenceDisplay = `Health score ${ev.evidence_value.toFixed(2)}`;
                  } else {
                    evidenceDisplay = `${ev.evidence_value}`;
                  }
                }

                return (
                  <tr
                    key={ev.event_id}
                    onClick={() => onSelectEvent(ev)}
                    style={{
                      borderBottom: '1px solid var(--panel-border-subtle)',
                      cursor: 'pointer',
                      transition: 'background 0.12s ease'
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--panel-hover)')}
                    onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                  >
                    <td style={{ padding: '8px 12px' }}>
                      <span className={`tag-tech ${eventTagClass}`}>{ev.event_type}</span>
                    </td>
                    <td style={{ padding: '8px 12px', fontWeight: 600, color: '#f8fafc' }} className="font-mono">
                      {ev.fixture_id}
                      {ev.fixture_type && <span style={{ fontSize: '0.68rem', color: '#64748b', display: 'block', fontWeight: 400 }}>{ev.fixture_type}</span>}
                    </td>
                    <td style={{ padding: '8px 12px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span>{ev.zone_name || ev.zone_id || 'Unknown'}</span>
                        {ev.criticality_tier && <span className={`tag-tech ${tierTagClass}`}>{ev.criticality_tier}</span>}
                      </div>
                    </td>
                    <td style={{ padding: '8px 12px' }} className="font-mono">
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <div style={{ width: '40px', height: '4px', background: 'rgba(255,255,255,0.1)', borderRadius: '1px', overflow: 'hidden' }}>
                          <div style={{ width: `${ev.confidence_score * 100}%`, height: '100%', background: ev.confidence_score >= 0.8 ? '#059669' : '#d97706' }} />
                        </div>
                        <span style={{ fontSize: '0.75rem', fontWeight: 700 }}>{(ev.confidence_score * 100).toFixed(0)}%</span>
                      </div>
                    </td>
                    <td style={{ padding: '8px 12px', fontWeight: 700, color: '#22d3ee' }} className="font-mono">
                      {evidenceDisplay}
                    </td>
                    <td style={{ padding: '8px 12px' }}>
                      <span className={`tag-tech ${ev.status === 'dispatched' ? 'tag-tier1' : 'tag-tier2'}`}>
                        {ev.status}
                      </span>
                    </td>
                    <td style={{ padding: '8px 12px', color: '#64748b', fontSize: '0.75rem' }} className="font-mono">
                      {new Date(ev.detected_at).toISOString().replace('T', ' ').slice(0, 19)}
                    </td>
                    <td style={{ padding: '8px 12px', textAlign: 'right' }}>
                      <button className="btn-action" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                        EVIDENCE <ExternalLink size={10} />
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

