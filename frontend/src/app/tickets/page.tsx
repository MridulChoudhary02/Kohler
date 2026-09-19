'use client';

// frontend/src/app/tickets/page.tsx — Full Operations Ticket Dispatch Kanban Board

import React from 'react';
import { FacilityHeatmap } from '../../components/FacilityHeatmap';
import { TicketKanbanBoard } from '../../components/TicketKanbanBoard';
import { useDashboard } from '../../lib/DashboardContext';

export default function TicketsPage() {
  const {
    tickets,
    selectedZoneId,
    setSelectedZoneId,
    loadData,
    handleOpenTicketModal,
  } = useDashboard();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Zone / Tier Criticality Breakdown Summary (Above Kanban Board) */}
      <FacilityHeatmap
        tickets={tickets}
        selectedZoneId={selectedZoneId}
        onSelectZone={setSelectedZoneId}
      />

      {/* Operations Dispatch Kanban Board */}
      <TicketKanbanBoard
        tickets={tickets}
        selectedZoneId={selectedZoneId}
        onTicketUpdated={loadData}
        onSelectTicket={handleOpenTicketModal}
      />
    </div>
  );
}
