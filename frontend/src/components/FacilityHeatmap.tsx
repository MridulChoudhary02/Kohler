// frontend/src/components/FacilityHeatmap.tsx — View 1: Facility Zone Heatmap

import React from 'react';
import { Building2 } from 'lucide-react';
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
    <div className="command-panel" style={{ padding: '20px', marginBottom: '24px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }} className="tech-divider">
        <div style={{ paddingBottom: '12px' }}>
          <h2 style={{ fontSize: '0.75rem', fontWeight: 600, color: '#8f8f8f', textTransform: 'uppercase', letterSpacing: '0.06em', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Building2 size={14} color="#8f8f8f" />
            Facility Criticality Matrix
          </h2>
        </div>

        {selectedZoneId && (
          <button
            onClick={() => onSelectZone(null)}
            className="btn-pill-outline"
            style={{ marginBottom: '12px' }}
          >
            Reset zone filter
          </button>
        )}
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
        gap: '14px'
      }}>
        {ZONES.map((zone) => {
          const zoneTickets = tickets.filter((t) => t.zone_id === zone.zone_id && t.status !== 'resolved');
          const openCount = zoneTickets.length;
          const maxPriority = zoneTickets.length > 0
            ? Math.max(...zoneTickets.map((t) => t.priority_score))
            : 0;

          const isSelected = selectedZoneId === zone.zone_id;

          const topStripColor = zone.tier === 'Tier 1' ? '#f87171' :
                                zone.tier === 'Tier 2' ? '#fbbf24' :
                                zone.tier === 'Tier 3' ? '#60a5fa' : '#4ade80';

          return (
            <div
              key={zone.zone_id}
              onClick={() => onSelectZone(isSelected ? null : zone.zone_id)}
              style={{
                background: isSelected ? '#1c1c1c' : '#141414',
                border: isSelected ? '1px solid #ffffff' : '1px solid #262626',
                borderTop: `4px solid ${topStripColor}`,
                borderRadius: '6px',
                padding: '16px',
                cursor: 'pointer',
                transition: 'all 0.12s ease',
              }}
            >
              {/* 1. Small-caps muted label at top */}
              <div style={{
                fontSize: '0.68rem',
                fontWeight: 600,
                color: '#8f8f8f',
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
                marginBottom: '4px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between'
              }}>
                <span>{zone.tier} • {zone.name}</span>
              </div>

              {/* 2. Large bold number below it */}
              <div className="font-mono" style={{
                fontSize: '2rem',
                fontWeight: 700,
                color: openCount > 0 ? topStripColor : '#ededed',
                lineHeight: 1.1,
                margin: '6px 0 4px 0'
              }}>
                {openCount}
              </div>

              {/* 3. Small muted subtitle line */}
              <div style={{ fontSize: '0.75rem', color: '#8f8f8f', marginTop: '4px' }}>
                {openCount > 0 ? (
                  <span>Active tickets (Max priority {maxPriority.toFixed(1)})</span>
                ) : (
                  <span>No active tickets • {zone.fixtureCount} fixtures clear</span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};



