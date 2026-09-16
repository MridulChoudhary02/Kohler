// frontend/src/components/CompactTicketsList.tsx — Overview Dashboard Compact Top 5 Tickets

import React from 'react';
import Link from 'next/link';
import { Kanban, ArrowRight } from 'lucide-react';
import { Ticket } from '../lib/types';

interface CompactTicketsListProps {
  tickets: Ticket[];
  selectedZoneId: string | null;
  onSelectTicket: (ticket: Ticket) => void;
}

export const CompactTicketsList: React.FC<CompactTicketsListProps> = ({
  tickets,
  selectedZoneId,
  onSelectTicket,
}) => {
  const filtered = selectedZoneId
    ? tickets.filter((t) => t.zone_id === selectedZoneId)
    : tickets;

  const top5 = [...filtered]
    .sort((a, b) => b.priority_score - a.priority_score)
    .slice(0, 5);

  return (
    <div className="command-panel" style={{ padding: '20px' }}>
      {/* 4. Section Header: small-caps muted label + View all -> link pattern in top-right */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }} className="tech-divider">
        <div style={{ paddingBottom: '12px' }}>
          <h2 style={{ fontSize: '0.75rem', fontWeight: 600, color: '#8f8f8f', textTransform: 'uppercase', letterSpacing: '0.06em', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Kanban size={14} color="#8f8f8f" />
            TOP DISPATCH TICKETS
          </h2>
        </div>

        {/* 3. Solid pill-shaped primary action button */}
        <Link href="/tickets" className="btn-pill-primary" style={{ marginBottom: '12px' }}>
          View all <ArrowRight size={13} />
        </Link>
      </div>

      {/* 2. List rows: clean horizontal rows separated by subtle 1px divider */}
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        {top5.length === 0 ? (
          <div style={{ padding: '24px 0', textAlign: 'center', color: '#525252', fontSize: '0.8125rem' }}>
            No active tickets match the selected criteria.
          </div>
        ) : (
          top5.map((t, idx) => {
            const statusDot = t.status === 'open' ? 'status-dot-rose' : t.status === 'acknowledged' ? 'status-dot-amber' : t.status === 'in_progress' ? 'status-dot-blue' : 'status-dot-emerald';
            const zoneInitials = t.zone_id.replace('zone-', '').toUpperCase().slice(0, 3);

            return (
              <div
                key={t.ticket_id}
                onClick={() => onSelectTicket(t)}
                style={{
                  padding: '12px 4px',
                  borderBottom: idx === top5.length - 1 ? 'none' : '1px solid #1e1e1e',
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
                    {zoneInitials}
                  </div>

                  <div style={{ overflow: 'hidden' }}>
                    <div style={{ fontSize: '0.875rem', fontWeight: 600, color: '#ededed', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {t.zone_id}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: '#8f8f8f', marginTop: '2px' }}>
                      Ticket #{t.ticket_id.slice(0, 8)} • Team: {t.assigned_team || 'Facilities'}
                    </div>
                  </div>
                </div>

                {/* Far Right: Status badge/pill stacked above priority score value */}
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px', flexShrink: 0 }}>
                  <span className="tag-tech" style={{ textTransform: 'uppercase' }}>
                    <span className={`status-dot ${statusDot}`} />
                    {t.status}
                  </span>
                  <span className="font-mono" style={{ fontSize: '0.75rem', fontWeight: 600, color: t.priority_score >= 80 ? '#f87171' : '#ededed' }}>
                    Score {t.priority_score.toFixed(1)}
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

