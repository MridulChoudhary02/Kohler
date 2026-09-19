'use client';

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { DetectionEvent, Ticket } from './types';
import { fetchEvents, fetchTickets } from './api';

interface DashboardContextType {
  events: DetectionEvent[];
  tickets: Ticket[];
  selectedZoneId: string | null;
  selectedEvent: DetectionEvent | null;
  selectedTicket: Ticket | null;
  loadData: () => Promise<void>;
  setSelectedZoneId: (zoneId: string | null) => void;
  handleOpenEventModal: (event: DetectionEvent) => void;
  handleOpenTicketModal: (ticket: Ticket) => void;
  handleCloseModal: () => void;
  isCopilotOpen: boolean;
  setIsCopilotOpen: (open: boolean) => void;
  openCopilot: () => void;
  closeCopilot: () => void;
  toggleCopilot: () => void;
}

const DashboardContext = createContext<DashboardContextType | undefined>(undefined);

export const DashboardProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [events, setEvents] = useState<DetectionEvent[]>([]);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [selectedZoneId, setSelectedZoneId] = useState<string | null>(null);

  // Modal drill-down state
  const [selectedEvent, setSelectedEvent] = useState<DetectionEvent | null>(null);
  const [selectedTicket, setSelectedTicket] = useState<Ticket | null>(null);

  // Copilot drawer state
  const [isCopilotOpen, setIsCopilotOpen] = useState<boolean>(false);
  const openCopilot = useCallback(() => setIsCopilotOpen(true), []);
  const closeCopilot = useCallback(() => setIsCopilotOpen(false), []);
  const toggleCopilot = useCallback(() => setIsCopilotOpen((prev) => !prev), []);

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
    <DashboardContext.Provider
      value={{
        events,
        tickets,
        selectedZoneId,
        selectedEvent,
        selectedTicket,
        loadData,
        setSelectedZoneId,
        handleOpenEventModal,
        handleOpenTicketModal,
        handleCloseModal,
        isCopilotOpen,
        setIsCopilotOpen,
        openCopilot,
        closeCopilot,
        toggleCopilot,
      }}
    >
      {children}
    </DashboardContext.Provider>
  );
};

export function useDashboard(): DashboardContextType {
  const context = useContext(DashboardContext);
  if (!context) {
    return {
      events: [],
      tickets: [],
      selectedZoneId: null,
      selectedEvent: null,
      selectedTicket: null,
      loadData: async () => {},
      setSelectedZoneId: () => {},
      handleOpenEventModal: () => {},
      handleOpenTicketModal: () => {},
      handleCloseModal: () => {},
      isCopilotOpen: false,
      setIsCopilotOpen: () => {},
      openCopilot: () => {},
      closeCopilot: () => {},
      toggleCopilot: () => {},
    };
  }
  return context;
}


