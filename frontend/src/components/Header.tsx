// frontend/src/components/Header.tsx — Hospital Facility Command Center Header

import React from 'react';
import { Activity, Droplets, ShieldAlert, CheckCircle2 } from 'lucide-react';
import { DetectionEvent, Ticket } from '../lib/types';

interface HeaderProps {
  events: DetectionEvent[];
  tickets: Ticket[];
}

export const Header: React.FC<HeaderProps> = ({ events, tickets }) => {
  // Aggregate estimated waste across active dispatched leak tickets (litres/hour)
  const totalLeakWasteLph = events
    .filter((e) => e.event_type === 'leak' && e.status === 'dispatched')
    .reduce((sum, e) => sum + (e.evidence_value || 0), 0);

  const openCount = tickets.filter((t) => t.status === 'open').length;
  const inProgressCount = tickets.filter((t) => t.status === 'in_progress' || t.status === 'acknowledged').length;
  const resolvedCount = tickets.filter((t) => t.status === 'resolved').length;

  return (
    <header style={{
      background: 'var(--panel-bg)',
      borderBottom: '1px solid var(--panel-border)',
      padding: '12px 24px',
      position: 'sticky',
      top: 0,
      zIndex: 40,
    }}>
      <div style={{
        maxWidth: '1600px',
        margin: '0 auto',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '16px'
      }}>
        {/* Brand Title */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{
            width: '36px',
            height: '36px',
            borderRadius: '4px',
            background: 'rgba(6, 182, 212, 0.15)',
            border: '1px solid rgba(6, 182, 212, 0.4)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <Droplets size={20} color="#06b6d4" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <h1 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#f8fafc', letterSpacing: '-0.01em', fontFamily: 'var(--font-sans)' }}>
                KOHLER <span style={{ color: '#06b6d4', fontWeight: 600 }}>Command Center</span>
              </h1>
              <span className="tag-tech tag-tier1">
                HOSPITAL CLINICAL OPERATIONAL FEED
              </span>
            </div>
            <p style={{ fontSize: '0.78rem', color: '#64748b', marginTop: '1px' }}>
              City General Hospital — Building Automation & Hydraulic Telemetry Matrix
            </p>
          </div>
        </div>

        {/* Sustainability Waste Instrumentation Readout */}
        <div style={{
          background: 'rgba(6, 182, 212, 0.06)',
          border: '1px solid rgba(6, 182, 212, 0.25)',
          borderRadius: '4px',
          padding: '8px 16px',
          display: 'flex',
          alignItems: 'center',
          gap: '14px',
        }}>
          <div className="beacon-cyan" />
          <div>
            <div style={{ fontSize: '0.65rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 600 }}>
              Flagged Hydraulic Waste Rate
            </div>
            <div className="font-mono" style={{ fontSize: '1.2rem', fontWeight: 800, color: '#22d3ee', marginTop: '1px' }}>
              {totalLeakWasteLph.toFixed(1)} <span style={{ fontSize: '0.75rem', fontWeight: 500, color: '#94a3b8' }}>L/hr</span>
            </div>
          </div>
        </div>

        {/* Technical Status Counters */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            background: 'rgba(225, 29, 72, 0.08)',
            border: '1px solid rgba(225, 29, 72, 0.3)',
            padding: '6px 14px',
            borderRadius: '4px'
          }}>
            <ShieldAlert size={14} color="#e11d48" />
            <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>OPEN:</span>
            <span className="font-mono" style={{ fontSize: '0.95rem', fontWeight: 800, color: '#fda4af' }}>{openCount}</span>
          </div>

          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            background: 'rgba(37, 99, 235, 0.08)',
            border: '1px solid rgba(37, 99, 235, 0.3)',
            padding: '6px 14px',
            borderRadius: '4px'
          }}>
            <Activity size={14} color="#2563eb" />
            <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>ACTIVE:</span>
            <span className="font-mono" style={{ fontSize: '0.95rem', fontWeight: 800, color: '#93c5fd' }}>{inProgressCount}</span>
          </div>

          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            background: 'rgba(5, 150, 105, 0.08)',
            border: '1px solid rgba(5, 150, 105, 0.3)',
            padding: '6px 14px',
            borderRadius: '4px'
          }}>
            <CheckCircle2 size={14} color="#059669" />
            <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>RESOLVED:</span>
            <span className="font-mono" style={{ fontSize: '0.95rem', fontWeight: 800, color: '#6ee7b7' }}>{resolvedCount}</span>
          </div>
        </div>
      </div>
    </header>
  );
};

