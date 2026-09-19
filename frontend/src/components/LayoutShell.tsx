'use client';

import React from 'react';
import { DashboardProvider, useDashboard } from '../lib/DashboardContext';
import { Header } from './Header';
import { FixtureDrillDownModal } from './FixtureDrillDownModal';
import { CopilotDrawer } from './CopilotDrawer';
import { CopilotFloatingTrigger } from './CopilotFloatingTrigger';

function ShellInner({ children }: { children: React.ReactNode }) {
  const { selectedEvent, selectedTicket, handleCloseModal } = useDashboard();

  return (
    <div style={{ minHeight: '100vh', background: 'var(--console-bg)', paddingBottom: '40px' }}>
      <Header />
      <main style={{ maxWidth: '1600px', margin: '24px auto', padding: '0 24px' }}>
        {children}
      </main>
      <FixtureDrillDownModal
        event={selectedEvent}
        ticket={selectedTicket}
        onClose={handleCloseModal}
      />
      <CopilotFloatingTrigger />
      <CopilotDrawer />
    </div>
  );
}

export function LayoutShell({ children }: { children: React.ReactNode }) {
  return (
    <DashboardProvider>
      <ShellInner>{children}</ShellInner>
    </DashboardProvider>
  );
}
