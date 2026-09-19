// frontend/src/components/TicketKanbanBoard.tsx — View 3: Operations Dispatch Kanban Board

import React from 'react';
import { Kanban, Clock, AlertTriangle, CheckCircle, Play, Eye } from 'lucide-react';
import { Ticket } from '../lib/types';
import { acknowledgeTicket, startTicket, resolveTicket } from '../lib/api';
import { Card } from './ui/card';
import { Badge } from './ui/badge';

interface TicketKanbanBoardProps {
  tickets: Ticket[];
  selectedZoneId: string | null;
  onTicketUpdated: () => void;
  onSelectTicket: (ticket: Ticket) => void;
}

export const TicketKanbanBoard: React.FC<TicketKanbanBoardProps> = ({
  tickets,
  selectedZoneId,
  onTicketUpdated,
  onSelectTicket,
}) => {
  const filteredTickets = selectedZoneId
    ? tickets.filter((t) => t.zone_id === selectedZoneId)
    : tickets;

  const columns = [
    { id: 'open', label: 'OPEN', dotClass: 'status-dot-rose', topStrip: '#f87171' },
    { id: 'acknowledged', label: 'ACKNOWLEDGED', dotClass: 'status-dot-amber', topStrip: '#fbbf24' },
    { id: 'in_progress', label: 'IN PROGRESS', dotClass: 'status-dot-blue', topStrip: '#60a5fa' },
    { id: 'resolved', label: 'RESOLVED', dotClass: 'status-dot-emerald', topStrip: '#4ade80' },
  ];

  const handleAcknowledge = async (e: React.MouseEvent, ticketId: string) => {
    e.stopPropagation();
    try {
      await acknowledgeTicket(ticketId);
      onTicketUpdated();
    } catch (err) {
      console.error('Error acknowledging ticket:', err);
    }
  };

  const handleStart = async (e: React.MouseEvent, ticketId: string) => {
    e.stopPropagation();
    try {
      await startTicket(ticketId);
      onTicketUpdated();
    } catch (err) {
      console.error('Error starting ticket:', err);
    }
  };

  const handleResolve = async (e: React.MouseEvent, ticketId: string) => {
    e.stopPropagation();
    try {
      await resolveTicket(ticketId);
      onTicketUpdated();
    } catch (err) {
      console.error('Error resolving ticket:', err);
    }
  };

  return (
    <div className="command-panel" style={{ padding: '20px', marginBottom: '24px' }}>
      {/* 4. Section header: small-caps muted label */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }} className="tech-divider">
        <div style={{ paddingBottom: '12px' }}>
          <h2 style={{ fontSize: '0.75rem', fontWeight: 600, color: '#8f8f8f', textTransform: 'uppercase', letterSpacing: '0.06em', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Kanban size={14} color="#8f8f8f" />
            OPERATIONS DISPATCH KANBAN BOARD
          </h2>
        </div>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(270px, 1fr))',
        gap: '14px',
        alignItems: 'start'
      }}>
        {columns.map((col) => {
          const colTickets = filteredTickets
            .filter((t) => t.status === col.id)
            .sort((a, b) => b.priority_score - a.priority_score);

          return (
            <div
              key={col.id}
              style={{
                background: '#121212',
                border: '1px solid #262626',
                borderTop: `4px solid ${col.topStrip}`,
                borderRadius: '6px',
                padding: '14px',
                minHeight: '450px'
              }}
            >
              {/* 1. Stat / Column Header with small-caps label + large bold count */}
              <div style={{
                paddingBottom: '12px',
                marginBottom: '14px',
                borderBottom: '1px solid #1e1e1e'
              }}>
                <div style={{ fontSize: '0.68rem', fontWeight: 600, color: '#8f8f8f', textTransform: 'uppercase', letterSpacing: '0.06em', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span className={`status-dot ${col.dotClass}`} />
                  {col.label}
                </div>
                <div className="font-mono" style={{ fontSize: '1.75rem', fontWeight: 700, color: col.topStrip, marginTop: '2px', lineHeight: 1.1 }}>
                  {colTickets.length}
                </div>
              </div>

              {/* Column Cards */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {colTickets.length === 0 ? (
                  <div style={{ padding: '24px 0', textAlign: 'center', color: '#525252', fontSize: '0.78rem' }}>
                    No {col.label.toLowerCase()} tickets
                  </div>
                ) : (
                  colTickets.map((ticket) => {
                    const isTier1 = ticket.zone_id === 'zone-icu' || ticket.zone_id === 'zone-ot';
                    const isTier2 = ticket.zone_id === 'zone-ward';
                    const cardTopStrip = isTier1 ? '#f87171' : isTier2 ? '#fbbf24' : '#262626';

                    return (
                      <Card
                        key={ticket.ticket_id}
                        onClick={() => onSelectTicket(ticket)}
                        className="p-3.5 cursor-pointer transition-all duration-150 hover:bg-[#181818]"
                        style={{
                          background: '#161616',
                          border: `1px solid ${ticket.is_escalated ? 'rgba(248, 113, 113, 0.4)' : '#262626'}`,
                          borderTop: `3px solid ${cardTopStrip}`,
                          borderRadius: '6px',
                        }}
                      >
                        {/* Top row */}
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                          <span className="font-mono" style={{ fontSize: '0.72rem', fontWeight: 500, color: '#8f8f8f' }}>
                            #{ticket.ticket_id.slice(0, 8)}
                          </span>
                          <Badge
                            variant="outline"
                            className="font-mono text-[0.72rem] font-semibold px-2 py-0.5 rounded-[9999px]"
                            style={{
                              background: '#1c1c1c',
                              color: ticket.priority_score >= 80 ? '#f87171' : '#ededed',
                              borderColor: '#262626',
                            }}
                          >
                            Score {ticket.priority_score.toFixed(1)}
                          </Badge>
                        </div>

                        {/* Zone & Escalation */}
                        <div style={{ fontSize: '0.875rem', fontWeight: 600, color: '#ededed', marginBottom: '4px' }}>
                          {ticket.zone_id}
                        </div>

                        {ticket.is_escalated && (
                          <Badge
                            variant="destructive"
                            className="tag-tech tag-tier1 font-mono text-[0.65rem] gap-1 mb-2"
                          >
                            <AlertTriangle size={10} color="#f87171" /> AUTO-ESCALATED (+25)
                          </Badge>
                        )}

                        {/* Team & Summary */}
                        <div style={{ fontSize: '0.75rem', color: '#8f8f8f', marginBottom: '8px' }}>
                          Team: <span style={{ color: '#ededed' }}>{ticket.assigned_team || 'General Facilities'}</span>
                        </div>

                        {ticket.summary_text && (
                          <div
                            title={ticket.summary_text}
                            style={{
                              fontSize: '0.75rem',
                              color: '#8f8f8f',
                              background: '#121212',
                              border: '1px solid #1e1e1e',
                              padding: '6px 8px',
                              borderRadius: '4px',
                              marginBottom: '10px',
                              whiteSpace: 'nowrap',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                            }}
                          >
                            {ticket.summary_text.length > 80
                              ? `${ticket.summary_text.slice(0, 80)}...`
                              : ticket.summary_text}
                          </div>
                        )}

                        {/* SLA timer */}
                        {ticket.sla_due && (
                          <div className="font-mono" style={{ fontSize: '0.7rem', color: '#525252', display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '10px' }}>
                            <Clock size={11} color="#525252" /> SLA: {new Date(ticket.sla_due).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </div>
                        )}

                        {/* 3. Action Buttons as Pill-Shaped Buttons */}
                        <div style={{ display: 'flex', gap: '6px', paddingTop: '8px', borderTop: '1px solid #1e1e1e' }}>
                          {ticket.status === 'open' && (
                            <button
                              onClick={(e) => handleAcknowledge(e, ticket.ticket_id)}
                              className="btn-pill-primary"
                              style={{ flex: 1, justifyContent: 'center' }}
                            >
                              Ack
                            </button>
                          )}

                          {(ticket.status === 'open' || ticket.status === 'acknowledged') && (
                            <button
                              onClick={(e) => handleStart(e, ticket.ticket_id)}
                              className="btn-pill-outline"
                              style={{ flex: 1, justifyContent: 'center' }}
                            >
                              <Play size={10} /> Start
                            </button>
                          )}

                          {(ticket.status === 'acknowledged' || ticket.status === 'in_progress') && (
                            <button
                              onClick={(e) => handleResolve(e, ticket.ticket_id)}
                              className="btn-pill-outline"
                              style={{ flex: 1, justifyContent: 'center' }}
                            >
                              <CheckCircle size={10} /> Resolve
                            </button>
                          )}

                          <button
                            onClick={(e) => { e.stopPropagation(); onSelectTicket(ticket); }}
                            className="btn-pill-outline"
                            style={{ padding: '4px 10px' }}
                            title="View evidence"
                          >
                            <Eye size={12} color="#8f8f8f" />
                          </button>
                        </div>
                      </Card>
                    );
                  })
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};


