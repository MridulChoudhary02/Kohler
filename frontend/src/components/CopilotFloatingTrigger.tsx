'use client';

// frontend/src/components/CopilotFloatingTrigger.tsx — Floating Copilot Button
// Floating bottom-right action button to trigger the Copilot side panel from any page.

import React from 'react';
import { Sparkles, MessageSquare } from 'lucide-react';
import { useDashboard } from '../lib/DashboardContext';

export const CopilotFloatingTrigger: React.FC = () => {
  const { isCopilotOpen, toggleCopilot } = useDashboard();

  return (
    <button
      onClick={toggleCopilot}
      aria-label="Toggle Facility Copilot"
      title="Open Facility Copilot (⌘K)"
      style={{
        position: 'fixed',
        bottom: '24px',
        right: '24px',
        zIndex: 80,
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        background: '#141414',
        color: '#ededed',
        border: '1px solid #2e2e2e',
        borderRadius: '9999px',
        padding: '10px 18px',
        boxShadow: '0 4px 24px rgba(0, 0, 0, 0.75), 0 0 12px rgba(74, 222, 128, 0.12)',
        cursor: 'pointer',
        transition: 'all 0.18s ease-in-out',
        opacity: isCopilotOpen ? 0 : 1,
        pointerEvents: isCopilotOpen ? 'none' : 'auto',
        transform: isCopilotOpen ? 'translateY(12px) scale(0.95)' : 'translateY(0) scale(1)',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = '#4ade80';
        e.currentTarget.style.boxShadow = '0 6px 28px rgba(0, 0, 0, 0.85), 0 0 16px rgba(74, 222, 128, 0.25)';
        e.currentTarget.style.transform = 'translateY(-2px) scale(1.02)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = '#2e2e2e';
        e.currentTarget.style.boxShadow = '0 4px 24px rgba(0, 0, 0, 0.75), 0 0 12px rgba(74, 222, 128, 0.12)';
        e.currentTarget.style.transform = 'translateY(0) scale(1)';
      }}
    >
      <div
        style={{
          width: '20px',
          height: '20px',
          borderRadius: '50%',
          background: 'rgba(74, 222, 128, 0.12)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Sparkles size={12} color="#4ade80" />
      </div>
      <span style={{ fontSize: '0.8125rem', fontWeight: 600, letterSpacing: '-0.01em' }}>
        Copilot
      </span>
      <span
        style={{
          fontSize: '0.65rem',
          fontFamily: 'var(--font-mono)',
          color: '#737373',
          background: '#1f1f1f',
          padding: '2px 6px',
          borderRadius: '4px',
          border: '1px solid #2a2a2a',
          marginLeft: '2px',
        }}
      >
        ⌘K
      </span>
    </button>
  );
};
