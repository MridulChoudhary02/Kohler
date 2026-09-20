// frontend/src/components/CompactAlertsList.tsx — Overview Dashboard Compact Recent 5 Alerts

import React from 'react';
import Link from 'next/link';
import { Activity, ArrowRight } from 'lucide-react';
import { DetectionEvent } from '../lib/types';

interface CompactAlertsListProps {
  events: DetectionEvent[];
  selectedZoneId: string | null;
  onSelectEvent: (event: DetectionEvent) => void;
}

export const CompactAlertsList: React.FC<CompactAlertsListProps> = ({
  events,
  selectedZoneId,
  onSelectEvent,
}) => {
  const filtered = selectedZoneId
    ? events.filter((e) => e.zone_id === selectedZoneId)
    : events;

  const recent5 = [...filtered]
    .sort((a, b) => new Date(b.detected_at).getTime() - new Date(a.detected_at).getTime())
    .slice(0, 5);

  return (
    <div className="command-panel" style={{ padding: '20px' }}>
      {/* 4. Section Header: small-caps muted label + View all -> link pattern in top-right */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }} className="tech-divider">
        <div style={{ paddingBottom: '12px' }}>
          <h2 style={{ fontSize: '0.75rem', fontWeight: 600, color: '#8f8f8f', textTransform: 'uppercase', letterSpacing: '0.06em', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Activity size={14} color="#8f8f8f" />
            RECENT ANOMALY EVENTS
          </h2>
        </div>

        {/* 3. Solid pill-shaped primary action button */}
        <Link href="/alerts" className="btn-pill-primary" style={{ marginBottom: '12px' }}>
          View all <ArrowRight size={13} />
        </Link>
      </div>

      {/* 2. List rows: clean horizontal rows separated by subtle 1px divider */}
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        {recent5.length === 0 ? (
          <div style={{ padding: '24px 0', textAlign: 'center', color: '#525252', fontSize: '0.8125rem' }}>
            No recent telemetry anomaly events match the selected criteria.
          </div>
        ) : (
          recent5.map((ev, idx) => {
            const dotColorClass = ev.event_type === 'leak' ? 'status-dot-rose' : ev.event_type === 'hygiene' ? 'status-dot-cyan' : 'status-dot-amber';
            const typeInitials = ev.event_type === 'leak' ? 'LK' : ev.event_type === 'hygiene' ? 'HY' : 'SF';

            let evidenceDisplay = 'N/A';
            if (ev.evidence_value !== null && ev.evidence_value !== undefined) {
              if (ev.event_type === 'leak') {
                evidenceDisplay = `${ev.evidence_value.toFixed(1)} L/hr waste`;
              } else if (ev.event_type === 'hygiene') {
                evidenceDisplay = `${ev.evidence_value.toFixed(1)}m to breach`;
              } else if (ev.event_type === 'sensor_fault') {
                evidenceDisplay = `Health ${ev.evidence_value.toFixed(2)}`;
              }
            }

            return (
              <div
                key={ev.event_id}
                data-testid="compact-alert-item"
                onClick={() => onSelectEvent(ev)}
                style={{
                  padding: '12px 4px',
                  borderBottom: idx === recent5.length - 1 ? 'none' : '1px solid #1e1e1e',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: '16px',
                  transition: 'background 0.12s ease',
                }}
                onMouseEnter={(e) => (e.currentTarget.style.background = '#161616')}
                onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
              >
                {/* Left: Circular initial avatar + Title & Subtitle stacked */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flex: 1, minWidth: 0 }}>
                  <div className="avatar-circle">
                    {typeInitials}
                  </div>

                  <div style={{ overflow: 'hidden' }}>
                    <div className="font-mono" style={{ fontSize: '0.875rem', fontWeight: 600, color: '#ededed', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {ev.fixture_id} • <span style={{ color: '#8f8f8f', fontWeight: 400 }}>{ev.zone_name || ev.zone_id}</span>
                    </div>
                    <div style={{ fontSize: '0.75rem', color: '#8f8f8f', marginTop: '2px' }}>
                      {(ev.confidence_score * 100).toFixed(0)}% confidence • {ev.detected_at.slice(11, 16)}
                    </div>
                  </div>
                </div>

                {/* Far Right: Status badge/pill stacked above value */}
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px', flexShrink: 0 }}>
                  <span className="tag-tech" style={{ textTransform: 'uppercase' }}>
                    <span className={`status-dot ${dotColorClass}`} />
                    {ev.event_type}
                  </span>
                  <span className="font-mono" style={{ fontSize: '0.75rem', fontWeight: 600, color: '#ededed' }}>
                    {evidenceDisplay}
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

