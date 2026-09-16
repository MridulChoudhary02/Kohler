'use client';

// frontend/src/app/tickets/page.tsx — Full Operations Ticket Dispatch Kanban Board

import React from 'react';
import { TicketKanbanBoard } from '../../components/TicketKanbanBoard';
import { useDashboard } from '../../lib/DashboardContext';

export default function TicketsPage() {
  const {
    tickets,
    selectedZoneId,
    loadData,
    handleOpenTicketModal,
  } = useDashboard();

  return (
    <TicketKanbanBoard
      tickets={tickets}
      selectedZoneId={selectedZoneId}
      onTicketUpdated={loadData}
      onSelectTicket={handleOpenTicketModal}
    />
  );
}
