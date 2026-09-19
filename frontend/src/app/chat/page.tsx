'use client';

// frontend/src/app/chat/page.tsx — Redirect to Copilot Side Panel
// Automatically opens the Copilot side panel drawer over the main dashboard.

import React, { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useDashboard } from '../../lib/DashboardContext';
import { Sparkles, ArrowRight } from 'lucide-react';

export default function ChatPage() {
  const router = useRouter();
  const { openCopilot } = useDashboard();

  useEffect(() => {
    openCopilot();
    router.replace('/');
  }, [openCopilot, router]);

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '450px',
        textAlign: 'center',
        gap: '16px',
      }}
    >
      <div
        style={{
          width: '52px',
          height: '52px',
          borderRadius: '50%',
          background: 'rgba(74, 222, 128, 0.1)',
          border: '1px solid rgba(74, 222, 128, 0.25)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Sparkles size={26} color="#4ade80" />
      </div>
      <div>
        <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: '#ededed' }}>
          Opening Facility Copilot...
        </h2>
        <p style={{ fontSize: '0.875rem', color: '#8f8f8f', maxWidth: '420px', marginTop: '6px', lineHeight: 1.5 }}>
          Chat has transitioned into the slide-out <strong>Copilot</strong> side panel, available anywhere in the application without interrupting your view.
        </p>
      </div>
      <button
        onClick={() => {
          openCopilot();
          router.replace('/');
        }}
        className="btn-pill-primary"
        style={{ marginTop: '8px' }}
      >
        Launch Copilot <ArrowRight size={14} />
      </button>
    </div>
  );
}
