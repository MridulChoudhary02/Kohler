'use client';

// frontend/src/app/page.tsx — Overview Dashboard Landing Page

import React from 'react';
import { FacilityHeatmap } from '../components/FacilityHeatmap';
import { CompactTicketsList } from '../components/CompactTicketsList';
import { CompactAlertsList } from '../components/CompactAlertsList';
import { useDashboard } from '../lib/DashboardContext';

export default function DashboardOverviewPage() {
  const {
    tickets,
    events,
    selectedZoneId,
    setSelectedZoneId,
    handleOpenTicketModal,
    handleOpenEventModal,
  } = useDashboard();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* View 1: Facility Criticality Heatmap Matrix */}
      <FacilityHeatmap
        tickets={tickets}
        selectedZoneId={selectedZoneId}
        onSelectZone={setSelectedZoneId}
      />

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
