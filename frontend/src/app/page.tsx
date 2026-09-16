'use client';

// frontend/src/app/page.tsx — Main Kohler Hospital Facility Manager Dashboard

import React, { useState, useEffect, useCallback } from 'react';
import { Header } from '../components/Header';
import { FacilityHeatmap } from '../components/FacilityHeatmap';
import { LiveAlertFeed } from '../components/LiveAlertFeed';
import { TicketKanbanBoard } from '../components/TicketKanbanBoard';
import { FixtureDrillDownModal } from '../components/FixtureDrillDownModal';
import { DetectionEvent, Ticket } from '../lib/types';
import { fetchEvents, fetchTickets } from '../lib/api';

export default function DashboardPage() {
  const [events, setEvents] = useState<DetectionEvent[]>([]);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [selectedZoneId, setSelectedZoneId] = useState<string | null>(null);

  // Modal drill-down state
  const [selectedEvent, setSelectedEvent] = useState<DetectionEvent | null>(null);
  const [selectedTicket, setSelectedTicket] = useState<Ticket | null>(null);

  const loadData = useCallback(async () => {
    try {
      const [fetchedEvents, fetchedTickets] = await Promise.all([
        fetchEvents({ limit: 100 }),
        fetchTickets({ limit: 100 }),
      ]);
      setEvents(fetchedEvents);
      setTickets(fetchedTickets);
    } catch (err) {
      console.error('Error polling dashboard data:', err);
    }
  }, []);

  // Poll data every 10s per PRD spec
  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 10000);
    return () => clearInterval(interval);
  }, [loadData]);

  const handleOpenEventModal = (event: DetectionEvent) => {
    setSelectedEvent(event);
    // Find matching ticket if present
    const matchingTicket = tickets.find((t) => t.event_id === event.event_id) || null;
    setSelectedTicket(matchingTicket);
  };

  const handleOpenTicketModal = (ticket: Ticket) => {
    setSelectedTicket(ticket);
    const matchingEvent = events.find((e) => e.event_id === ticket.event_id) || null;
    setSelectedEvent(matchingEvent);
  };

  const handleCloseModal = () => {
    setSelectedEvent(null);
    setSelectedTicket(null);
  };

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-dark)', paddingBottom: '40px' }}>
      {/* Top Navigation Header & Sustainability Counter */}
      <Header events={events} tickets={tickets} />

      {/* Main Command Dashboard Layout */}
      <main style={{ maxWidth: '1600px', margin: '24px auto', padding: '0 24px' }}>
        {/* View 1: Facility Criticality Heatmap */}
        <FacilityHeatmap
          tickets={tickets}
          selectedZoneId={selectedZoneId}
          onSelectZone={setSelectedZoneId}
        />

        {/* View 3: Operations Kanban Ticket Board */}
        <TicketKanbanBoard
          tickets={tickets}
          selectedZoneId={selectedZoneId}
          onTicketUpdated={loadData}
          onSelectTicket={handleOpenTicketModal}
        />

        {/* View 2: Live Alert Feed Stream */}
        <LiveAlertFeed
          events={events}
          selectedZoneId={selectedZoneId}
          onSelectEvent={handleOpenEventModal}
        />
      </main>

      {/* View 4: Per-Fixture Evidence Drill-Down Modal */}
      <FixtureDrillDownModal
        event={selectedEvent}
        ticket={selectedTicket}
        onClose={handleCloseModal}
      />
    </div>
  );
}
