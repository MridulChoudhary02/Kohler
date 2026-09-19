'use client';

// frontend/src/app/page.tsx — Overview Dashboard Landing Page

import React from 'react';
import { FacilityKpiRow } from '../components/FacilityKpiRow';
import { CompactTicketsList } from '../components/CompactTicketsList';
import { CompactAlertsList } from '../components/CompactAlertsList';
import { useDashboard } from '../lib/DashboardContext';

export default function DashboardOverviewPage() {
  const {
    tickets,
    events,
    metrics,
    selectedZoneId,
    handleOpenTicketModal,
    handleOpenEventModal,
  } = useDashboard();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Real-time Sustainability & System Health KPI Row */}
      <FacilityKpiRow metrics={metrics} />

      {/* Overview Grid: Compact Top 5 Tickets & Compact Recent 5 Alerts */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(480px, 1fr))', gap: '24px' }}>
        <CompactTicketsList
          tickets={tickets}
          selectedZoneId={selectedZoneId}
          onSelectTicket={handleOpenTicketModal}
        />

        <CompactAlertsList
          events={events}
          selectedZoneId={selectedZoneId}
          onSelectEvent={handleOpenEventModal}
        />
      </div>
    </div>
  );
}
