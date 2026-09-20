// frontend/src/components/Header.tsx — Hospital Facility Command Center Header & Navigation

'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Droplets, LayoutDashboard, Ticket as TicketIcon, Bell, Sparkles, Activity } from 'lucide-react';
import { useDashboard } from '../lib/DashboardContext';
import { DetectionEvent, Ticket } from '../lib/types';

interface HeaderProps {
  events?: DetectionEvent[];
  tickets?: Ticket[];
}

export const Header: React.FC<HeaderProps> = (props) => {
  const dashboard = useDashboard();
  const events = props.events || dashboard?.events || [];
  const tickets = props.tickets || dashboard?.tickets || [];

  const pathname = usePathname();

  // Aggregate estimated waste across active dispatched leak tickets (litres/hour)
  const totalLeakWasteLph = events
    .filter((e) => e.event_type === 'leak' && e.status === 'dispatched')
    .reduce((sum, e) => sum + (e.evidence_value || 0), 0);

  const openCount = tickets.filter((t) => t.status === 'open').length;
  const inProgressCount = tickets.filter((t) => t.status === 'in_progress' || t.status === 'acknowledged').length;
  const resolvedCount = tickets.filter((t) => t.status === 'resolved').length;

  const navItems = [
    { href: '/', label: 'Dashboard', icon: LayoutDashboard },
    { href: '/tickets', label: 'Tickets', icon: TicketIcon },
    { href: '/alerts', label: 'Alerts', icon: Bell },
    { href: '/fixtures/health', label: 'Fixture Health', icon: Activity },
  ];


  return (
    <header style={{
      background: '#0a0a0a',
      borderBottom: '1px solid #1e1e1e',
      position: 'sticky',
      top: 0,
      zIndex: 40,
    }}>
      <div style={{
        maxWidth: '1600px',
        margin: '0 auto',
        padding: '16px 24px 0 24px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '20px'
      }}>
        {/* Brand & Hero Title — Vercel Style Confident Typography Moment */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{
            width: '40px',
            height: '40px',
            borderRadius: '6px',
            background: '#141414',
            border: '1px solid #262626',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <Droplets size={20} color="#ededed" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <h1 style={{ fontSize: '1.75rem', fontWeight: 700, color: '#ededed', letterSpacing: '-0.03em', fontFamily: 'var(--font-sans)', lineHeight: 1.1 }}>
                KOHLER <span style={{ color: '#737373', fontWeight: 400 }}>Command Center</span>
              </h1>
              <span className="tag-tech tag-tier1">
                <span className="status-dot status-dot-rose" />
                HOSPITAL CLINICAL FEED
              </span>
            </div>
            <p style={{ fontSize: '0.8125rem', color: '#737373', marginTop: '4px' }}>
              City General Hospital — Building Automation & Hydraulic Telemetry Matrix
            </p>
          </div>
        </div>

        {/* Sustainability Waste Instrumentation Readout */}
        <div style={{
          background: '#121212',
          border: '1px solid #262626',
          borderRadius: '6px',
          padding: '10px 18px',
          display: 'flex',
          alignItems: 'center',
          gap: '14px',
        }}>
          <div className="beacon-cyan" />
          <div>
            <div style={{ fontSize: '0.7rem', color: '#8f8f8f', letterSpacing: '0.01em', fontWeight: 500 }}>
              Flagged Hydraulic Waste Rate
            </div>
            <div className="font-mono" style={{ fontSize: '1.25rem', fontWeight: 700, color: '#ededed', marginTop: '1px' }}>
              {totalLeakWasteLph.toFixed(1)} <span style={{ fontSize: '0.75rem', fontWeight: 400, color: '#8f8f8f' }}>L/hr</span>
            </div>
          </div>
        </div>

        {/* Technical Status Counters */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            background: '#121212',
            border: '1px solid #262626',
            padding: '6px 14px',
            borderRadius: '6px'
          }}>
            <span className="status-dot status-dot-rose" />
            <span style={{ fontSize: '0.75rem', color: '#8f8f8f', fontWeight: 500 }}>Open:</span>
            <span className="font-mono" style={{ fontSize: '0.875rem', fontWeight: 600, color: '#f87171' }}>{openCount}</span>
          </div>

          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            background: '#121212',
            border: '1px solid #262626',
            padding: '6px 14px',
            borderRadius: '6px'
          }}>
            <span className="status-dot status-dot-blue" />
            <span style={{ fontSize: '0.75rem', color: '#8f8f8f', fontWeight: 500 }}>Active:</span>
            <span className="font-mono" style={{ fontSize: '0.875rem', fontWeight: 600, color: '#60a5fa' }}>{inProgressCount}</span>
          </div>

          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            background: '#121212',
            border: '1px solid #262626',
            padding: '6px 14px',
            borderRadius: '6px'
          }}>
            <span className="status-dot status-dot-emerald" />
            <span style={{ fontSize: '0.75rem', color: '#8f8f8f', fontWeight: 500 }}>Resolved:</span>
            <span className="font-mono" style={{ fontSize: '0.875rem', fontWeight: 600, color: '#4ade80' }}>{resolvedCount}</span>
          </div>
        </div>
      </div>

      {/* Persistent Navigation Bar — Linear / Vercel Style Navigation Tabs */}
      <div style={{
        maxWidth: '1600px',
        margin: '16px auto 0 auto',
        padding: '0 24px',
        display: 'flex',
        alignItems: 'center',
        gap: '4px',
      }}>
        {navItems.map((item) => {
          const isActive = item.href === '/' ? pathname === '/' : pathname.startsWith(item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                padding: '8px 16px',
                fontSize: '0.8125rem',
                fontWeight: isActive ? 600 : 500,
                color: isActive ? '#ffffff' : '#8f8f8f',
                background: isActive ? '#1c1c1c' : 'transparent',
                borderTopLeftRadius: '6px',
                borderTopRightRadius: '6px',
                border: isActive ? '1px solid #262626' : '1px solid transparent',
                borderBottom: isActive ? '1px solid #1c1c1c' : '1px solid transparent',
                marginBottom: '-1px',
                textDecoration: 'none',
                transition: 'all 0.12s ease',
              }}
            >
              <Icon size={14} color={isActive ? '#ffffff' : '#8f8f8f'} />
              {item.label}
            </Link>
          );
        })}

        {/* Copilot Drawer Trigger Tab in Nav */}
        <button
          onClick={dashboard.toggleCopilot}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            padding: '8px 16px',
            fontSize: '0.8125rem',
            fontWeight: dashboard.isCopilotOpen ? 600 : 500,
            color: dashboard.isCopilotOpen ? '#4ade80' : '#8f8f8f',
            background: dashboard.isCopilotOpen ? '#1c1c1c' : 'transparent',
            borderTopLeftRadius: '6px',
            borderTopRightRadius: '6px',
            border: dashboard.isCopilotOpen ? '1px solid #262626' : '1px solid transparent',
            borderBottom: dashboard.isCopilotOpen ? '1px solid #1c1c1c' : '1px solid transparent',
            marginBottom: '-1px',
            cursor: 'pointer',
            transition: 'all 0.12s ease',
          }}
          onMouseEnter={(e) => {
            if (!dashboard.isCopilotOpen) e.currentTarget.style.color = '#ededed';
          }}
          onMouseLeave={(e) => {
            if (!dashboard.isCopilotOpen) e.currentTarget.style.color = '#8f8f8f';
          }}
        >
          <Sparkles size={14} color={dashboard.isCopilotOpen ? '#4ade80' : '#8f8f8f'} />
          Copilot
          <span
            style={{
              fontSize: '0.62rem',
              fontFamily: 'var(--font-mono)',
              padding: '1px 5px',
              borderRadius: '4px',
              background: 'rgba(74, 222, 128, 0.1)',
              color: '#4ade80',
              border: '1px solid rgba(74, 222, 128, 0.2)',
            }}
          >
            AI
          </span>
        </button>
      </div>
    </header>
  );
};



