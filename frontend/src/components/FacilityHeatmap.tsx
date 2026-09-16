// frontend/src/components/FacilityHeatmap.tsx — View 1: Facility Zone Heatmap

import React from 'react';
import { Building2, AlertTriangle, ShieldCheck, Cpu } from 'lucide-react';
import { Ticket, ZoneTier } from '../lib/types';

interface ZoneMetadata {
  zone_id: string;
  name: string;
  tier: ZoneTier;
  fixtureCount: number;
  description: string;
}

const ZONES: ZoneMetadata[] = [
  { zone_id: 'zone-icu', name: 'ICU Restrooms & Scrub Area', tier: 'Tier 1', fixtureCount: 4, description: 'Critical Care — 15m SLA' },
  { zone_id: 'zone-ot', name: 'Operating Theatre Scrub Stations', tier: 'Tier 1', fixtureCount: 4, description: 'Critical Care — 15m SLA' },
  { zone_id: 'zone-ward', name: 'General Ward Restrooms', tier: 'Tier 2', fixtureCount: 4, description: 'Patient Care — 30m SLA' },
  { zone_id: 'zone-lab', name: 'Lab & Staff Scrub Rooms', tier: 'Tier 3', fixtureCount: 4, description: 'Clinical Support — 1h SLA' },
  { zone_id: 'zone-lobby', name: 'Lobby & Visitor Washrooms', tier: 'Tier 4', fixtureCount: 4, description: 'Public/Admin — 2h SLA' },
];

interface FacilityHeatmapProps {
  tickets: Ticket[];
  selectedZoneId: string | null;
  onSelectZone: (zoneId: string | null) => void;
}

export const FacilityHeatmap: React.FC<FacilityHeatmapProps> = ({
  tickets,
  selectedZoneId,
  onSelectZone,
}) => {
  return (
    <div className="command-panel" style={{ padding: '20px', marginBottom: '20px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }} className="tech-divider">
        <div style={{ paddingBottom: '12px' }}>
          <h2 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Building2 size={18} color="#06b6d4" />
            Facility Criticality Heatmap Matrix
          </h2>
          <p style={{ fontSize: '0.78rem', color: '#64748b', marginTop: '2px' }}>
            Real-time zone status grouped by hospital criticality tier (PRD §5). Click any zone to filter command board.
          </p>
        </div>

        {selectedZoneId && (
          <button
            onClick={() => onSelectZone(null)}
            className="btn-action"
            style={{ marginBottom: '12px' }}
          >
            RESET ZONE FILTER
          </button>
        )}
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
        gap: '12px'
      }}>
        {ZONES.map((zone) => {
          const zoneTickets = tickets.filter((t) => t.zone_id === zone.zone_id && t.status !== 'resolved');
          const openCount = zoneTickets.length;
          const maxPriority = zoneTickets.length > 0
            ? Math.max(...zoneTickets.map((t) => t.priority_score))
            : 0;

          const isSelected = selectedZoneId === zone.zone_id;

          const tagClass = zone.tier === 'Tier 1' ? 'tag-tier1' :
                           zone.tier === 'Tier 2' ? 'tag-tier2' :
                           zone.tier === 'Tier 3' ? 'tag-tier3' : 'tag-tier4';

          const borderStyle = isSelected
            ? '2px solid #06b6d4'
            : openCount > 0 && zone.tier === 'Tier 1'
            ? '1px solid #e11d48'
            : '1px solid var(--panel-border)';

          return (
            <div
              key={zone.zone_id}
              onClick={() => onSelectZone(isSelected ? null : zone.zone_id)}
              style={{
                background: isSelected ? 'rgba(6, 182, 212, 0.12)' : 'var(--panel-bg)',
                border: borderStyle,
                borderLeft: zone.tier === 'Tier 1' ? '3px solid #e11d48' : zone.tier === 'Tier 2' ? '3px solid #d97706' : '1px solid var(--panel-border)',
                borderRadius: '3px',
                padding: '14px',
                cursor: 'pointer',
                transition: 'background 0.12s ease',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span className={`tag-tech ${tagClass}`}>{zone.tier}</span>
                <span className="font-mono" style={{ fontSize: '0.7rem', color: '#64748b', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <Cpu size={12} color="#64748b" /> {zone.fixtureCount} FIXTURES
                </span>
              </div>

              <h3 style={{ fontSize: '0.92rem', fontWeight: 600, color: '#f8fafc', marginBottom: '2px' }}>
                {zone.name}
              </h3>
              <p style={{ fontSize: '0.72rem', color: '#64748b', marginBottom: '12px' }}>
                {zone.description}
              </p>

              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: '8px', borderTop: '1px solid var(--panel-border-subtle)' }}>
                <div>
                  <div style={{ fontSize: '0.65rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 600 }}>Active Tickets</div>
                  <div className="font-mono" style={{ fontSize: '0.95rem', fontWeight: 700, color: openCount > 0 ? '#fda4af' : '#34d399', display: 'flex', alignItems: 'center', gap: '6px', marginTop: '1px' }}>
                    {openCount > 0 ? <AlertTriangle size={14} color="#e11d48" /> : <ShieldCheck size={14} color="#059669" />}
                    {openCount} OPEN
                  </div>
                </div>

                {openCount > 0 && (
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '0.65rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 600 }}>Max Priority</div>
                    <div className="font-mono" style={{ fontSize: '1rem', fontWeight: 800, color: maxPriority >= 80 ? '#fda4af' : maxPriority >= 60 ? '#fde68a' : '#93c5fd', marginTop: '1px' }}>
                      {maxPriority.toFixed(1)}
                    </div>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

