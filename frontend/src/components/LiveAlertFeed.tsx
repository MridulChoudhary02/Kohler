// frontend/src/components/LiveAlertFeed.tsx — View 2: Telemetry Event Ledger Stream

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
    <div className="command-panel" style={{ padding: '20px', marginBottom: '24px' }}>
      {/* 4. Section Header: small-caps muted label */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px', marginBottom: '16px' }} className="tech-divider">
        <div style={{ paddingBottom: '12px' }}>
          <h2 style={{ fontSize: '0.75rem', fontWeight: 600, color: '#8f8f8f', textTransform: 'uppercase', letterSpacing: '0.06em', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Activity size={14} color="#8f8f8f" />
            TELEMETRY ANOMALY LEDGER STREAM
          </h2>
        </div>

        {/* 3. Controls & Pill Tabs */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap', marginBottom: '12px' }}>
          {/* Search box */}
          <div style={{ position: 'relative' }}>
            <Search size={14} color="#8f8f8f" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
            <input
              type="text"
              placeholder="Filter fixture or zone..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="font-mono"
              style={{
                background: '#141414',
                border: '1px solid #262626',
                borderRadius: '9999px',
                padding: '5px 14px 5px 34px',
                fontSize: '0.75rem',
                color: '#ededed',
                outline: 'none',
                width: '220px'
              }}
            />
          </div>

          {/* Event type filter tabs — Pill style */}
          <div style={{ display: 'flex', background: '#141414', padding: '3px', borderRadius: '9999px', border: '1px solid #262626', gap: '2px' }}>
            {[
              { id: 'all', label: 'All' },
              { id: 'leak', label: 'Leaks' },
              { id: 'hygiene', label: 'Hygiene' },
              { id: 'sensor_fault', label: 'Faults' },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setFilterType(tab.id)}
                style={{
                  background: filterType === tab.id ? '#ffffff' : 'transparent',
                  color: filterType === tab.id ? '#0a0a0a' : '#8f8f8f',
                  border: 'none',
                  borderRadius: '9999px',
                  padding: '3px 12px',
                  fontSize: '0.75rem',
                  fontWeight: filterType === tab.id ? 600 : 500,
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

      {/* 2. List Rows Table */}
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.8125rem' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #1e1e1e', color: '#8f8f8f', fontFamily: 'var(--font-mono)', fontSize: '0.72rem' }}>
              <th style={{ padding: '10px 12px', fontWeight: 500 }}>TYPE</th>
              <th style={{ padding: '10px 12px', fontWeight: 500 }}>FIXTURE ID</th>
              <th style={{ padding: '10px 12px', fontWeight: 500 }}>ZONE & TIER</th>
              <th style={{ padding: '10px 12px', fontWeight: 500 }}>CONFIDENCE</th>
              <th style={{ padding: '10px 12px', fontWeight: 500 }}>EVIDENCE READOUT</th>
              <th style={{ padding: '10px 12px', fontWeight: 500 }}>STATUS</th>
              <th style={{ padding: '10px 12px', fontWeight: 500 }}>TIMESTAMP (UTC)</th>
              <th style={{ padding: '10px 12px', textAlign: 'right', fontWeight: 500 }}>ACTION</th>
            </tr>
          </thead>
          <tbody>
            {filteredEvents.length === 0 ? (
              <tr>
                <td colSpan={8} style={{ padding: '32px', textAlign: 'center', color: '#525252' }}>
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

                const dotColorClass = ev.event_type === 'leak' ? 'status-dot-rose' :
                                      ev.event_type === 'hygiene' ? 'status-dot-cyan' : 'status-dot-amber';

                const typeInitials = ev.event_type === 'leak' ? 'LK' : ev.event_type === 'hygiene' ? 'HY' : 'SF';

                let evidenceDisplay = 'N/A';
                if (ev.evidence_value !== null && ev.evidence_value !== undefined) {
                  if (ev.event_type === 'leak') {
                    evidenceDisplay = `${ev.evidence_value.toFixed(1)} L/hr waste`;
                  } else if (ev.event_type === 'hygiene') {
                    evidenceDisplay = `${ev.evidence_value.toFixed(1)}m to breach`;
                  } else if (ev.event_type === 'sensor_fault') {
                    evidenceDisplay = `Health ${ev.evidence_value.toFixed(2)}`;
                  } else {
                    evidenceDisplay = `${ev.evidence_value}`;
                  }
                }

                return (
                  <tr
                    key={ev.event_id}
                    onClick={() => onSelectEvent(ev)}
                    style={{
                      borderBottom: '1px solid #1e1e1e',
                      cursor: 'pointer',
                      transition: 'background 0.12s ease'
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = '#161616')}
                    onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                  >
                    <td style={{ padding: '12px 12px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <div className="avatar-circle" style={{ width: '32px', height: '32px', fontSize: '0.7rem' }}>
                          {typeInitials}
                        </div>
                        <span className={`tag-tech ${eventTagClass}`}>
                          <span className={`status-dot ${dotColorClass}`} />
                          {ev.event_type}
                        </span>
                      </div>
                    </td>
                    <td style={{ padding: '12px 12px', fontWeight: 600, color: '#ededed' }} className="font-mono">
                      {ev.fixture_id}
                      {ev.fixture_type && <span style={{ fontSize: '0.7rem', color: '#8f8f8f', display: 'block', fontWeight: 400 }}>{ev.fixture_type}</span>}
                    </td>
                    <td style={{ padding: '12px 12px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span>{ev.zone_name || ev.zone_id || 'Unknown'}</span>
                        {ev.criticality_tier && <span className={`tag-tech ${tierTagClass}`}>{ev.criticality_tier}</span>}
                      </div>
                    </td>
                    <td style={{ padding: '12px 12px' }} className="font-mono">
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <div style={{ width: '40px', height: '4px', background: '#262626', borderRadius: '2px', overflow: 'hidden' }}>
                          <div style={{ width: `${ev.confidence_score * 100}%`, height: '100%', background: ev.confidence_score >= 0.8 ? '#4ade80' : '#fbbf24' }} />
                        </div>
                        <span style={{ fontSize: '0.75rem', fontWeight: 600 }}>{(ev.confidence_score * 100).toFixed(0)}%</span>
                      </div>
                    </td>
                    <td style={{ padding: '12px 12px', fontWeight: 600, color: '#ededed' }} className="font-mono">
                      {evidenceDisplay}
                    </td>
                    <td style={{ padding: '12px 12px' }}>
                      <span className="tag-tech" style={{ color: ev.status === 'dispatched' ? '#f87171' : '#8f8f8f' }}>
                        <span className={`status-dot ${ev.status === 'dispatched' ? 'status-dot-rose' : 'status-dot-amber'}`} />
                        {ev.status}
                      </span>
                    </td>
                    <td style={{ padding: '12px 12px', color: '#8f8f8f', fontSize: '0.75rem' }} className="font-mono">
                      {new Date(ev.detected_at).toISOString().replace('T', ' ').slice(0, 19)}
                    </td>
                    <td style={{ padding: '12px 12px', textAlign: 'right' }}>
                      {/* 3. Outlined pill action button */}
                      <button className="btn-pill-outline">
                        Evidence <ExternalLink size={10} />
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



