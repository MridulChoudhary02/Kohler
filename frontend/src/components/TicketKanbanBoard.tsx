// frontend/src/components/TicketKanbanBoard.tsx — View 3: Kanban Ticket Board with Action Transitions

import React from 'react';
import { Kanban, Clock, AlertTriangle, CheckCircle, Play, Eye } from 'lucide-react';
import { Ticket } from '../lib/types';
import { acknowledgeTicket, startTicket, resolveTicket } from '../lib/api';

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
    { id: 'open', label: 'OPEN', color: '#e11d48', bg: 'rgba(225, 29, 72, 0.04)' },
    { id: 'acknowledged', label: 'ACKNOWLEDGED', color: '#d97706', bg: 'rgba(217, 119, 6, 0.04)' },
    { id: 'in_progress', label: 'IN PROGRESS', color: '#2563eb', bg: 'rgba(37, 99, 235, 0.04)' },
    { id: 'resolved', label: 'RESOLVED', color: '#059669', bg: 'rgba(5, 150, 105, 0.04)' },
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
    <div className="command-panel" style={{ padding: '20px', marginBottom: '20px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }} className="tech-divider">
        <div style={{ paddingBottom: '12px' }}>
          <h2 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Kanban size={18} color="#06b6d4" />
            Operations Ticket Dispatch Board (Kanban)
          </h2>
          <p style={{ fontSize: '0.78rem', color: '#64748b', marginTop: '2px' }}>
            Prioritized tickets sorted by priority_score (PRD §10 formula). Click any card for evidence drill-down.
          </p>
        </div>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(270px, 1fr))',
        gap: '12px',
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
                background: col.bg,
                border: `1px solid ${col.color}25`,
                borderRadius: '3px',
                padding: '14px',
                minHeight: '450px'
              }}
            >
              {/* Column Header */}
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                paddingBottom: '10px',
                marginBottom: '14px',
                borderBottom: `2px solid ${col.color}`
              }}>
                <span style={{ fontSize: '0.82rem', fontWeight: 700, color: '#f8fafc', letterSpacing: '0.04em' }}>{col.label}</span>
                <span className="font-mono" style={{
                  background: `${col.color}20`,
                  color: col.color,
                  padding: '2px 7px',
                  borderRadius: '2px',
                  fontSize: '0.72rem',
                  fontWeight: 700
                }}>
                  {colTickets.length}
                </span>
              </div>

              {/* Column Cards */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {colTickets.length === 0 ? (
                  <div style={{ padding: '24px 0', textAlign: 'center', color: '#64748b', fontSize: '0.78rem' }}>
                    NO {col.label} TICKETS
                  </div>
                ) : (
                  colTickets.map((ticket) => {
                    const isTier1 = ticket.zone_id === 'zone-icu' || ticket.zone_id === 'zone-ot';
                    const isTier2 = ticket.zone_id === 'zone-ward';

                    const borderAccent = isTier1 ? '#e11d48' : isTier2 ? '#d97706' : 'var(--panel-border)';

                    return (
                      <div
                        key={ticket.ticket_id}
                        onClick={() => onSelectTicket(ticket)}
                        style={{
                          background: 'var(--panel-bg)',
                          border: `1px solid ${ticket.is_escalated ? '#e11d48' : 'var(--panel-border)'}`,
                          borderLeft: `3px solid ${borderAccent}`,
                          borderRadius: '3px',
                          padding: '12px',
                          cursor: 'pointer',
                          transition: 'background 0.12s ease'
                        }}
                      >
                        {/* Top row */}
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                          <span className="font-mono" style={{ fontSize: '0.7rem', fontWeight: 600, color: '#64748b' }}>
                            #{ticket.ticket_id.slice(0, 8)}
                          </span>
                          <span className="font-mono" style={{
                            background: ticket.priority_score >= 80 ? 'rgba(225, 29, 72, 0.15)' : 'rgba(6, 182, 212, 0.15)',
                            color: ticket.priority_score >= 80 ? '#fda4af' : '#22d3ee',
                            border: `1px solid ${ticket.priority_score >= 80 ? 'rgba(225, 29, 72, 0.3)' : 'rgba(6, 182, 212, 0.3)'}`,
                            padding: '1px 6px',
                            borderRadius: '2px',
                            fontSize: '0.72rem',
                            fontWeight: 700
                          }}>
                            {ticket.priority_score.toFixed(1)}
                          </span>
                        </div>

                        {/* Zone & Escalation */}
                        <div style={{ fontSize: '0.82rem', fontWeight: 600, color: '#f8fafc', marginBottom: '3px' }}>
                          {ticket.zone_id}
                        </div>

                        {ticket.is_escalated && (
                          <div className="tag-tech tag-tier1" style={{ marginBottom: '6px', fontSize: '0.62rem' }}>
                            <AlertTriangle size={10} /> AUTO-ESCALATED (+25)
                          </div>
                        )}

                        {/* Team & Summary */}
                        <div style={{ fontSize: '0.72rem', color: '#64748b', marginBottom: '6px' }}>
                          Team: <span style={{ color: '#cbd5e1' }}>{ticket.assigned_team || 'General Facilities'}</span>
                        </div>

                        {ticket.summary_text && (
                          <div style={{
                            fontSize: '0.72rem',
                            color: '#cbd5e1',
                            background: 'rgba(0,0,0,0.25)',
                            border: '1px solid var(--panel-border-subtle)',
                            padding: '5px 7px',
                            borderRadius: '2px',
                            marginBottom: '10px'
                          }}>
                            {ticket.summary_text}
                          </div>
                        )}

                        {/* SLA timer */}
                        {ticket.sla_due && (
                          <div className="font-mono" style={{ fontSize: '0.68rem', color: '#64748b', display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '10px' }}>
                            <Clock size={11} color="#64748b" /> SLA: {new Date(ticket.sla_due).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </div>
                        )}

                        {/* Action buttons */}
                        <div style={{ display: 'flex', gap: '6px', paddingTop: '8px', borderTop: '1px solid var(--panel-border-subtle)' }}>
                          {ticket.status === 'open' && (
                            <button
                              onClick={(e) => handleAcknowledge(e, ticket.ticket_id)}
                              className="btn-action btn-ack"
                              style={{ flex: 1 }}
                            >
                              ACK
                            </button>
                          )}

                          {(ticket.status === 'open' || ticket.status === 'acknowledged') && (
                            <button
                              onClick={(e) => handleStart(e, ticket.ticket_id)}
                              className="btn-action btn-start"
                              style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '3px' }}
                            >
                              <Play size={10} /> START
                            </button>
                          )}

                          {(ticket.status === 'acknowledged' || ticket.status === 'in_progress') && (
                            <button
                              onClick={(e) => handleResolve(e, ticket.ticket_id)}
                              className="btn-action btn-resolve"
                              style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '3px' }}
                            >
                              <CheckCircle size={10} /> RESOLVE
                            </button>
                          )}

                          <button
                            onClick={(e) => { e.stopPropagation(); onSelectTicket(ticket); }}
                            className="btn-action"
                            style={{ padding: '4px 8px' }}
                          >
                            <Eye size={12} color="#94a3b8" />
                          </button>
                        </div>
                      </div>
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

