'use client';

// frontend/src/app/alerts/page.tsx — Full Telemetry Anomaly Ledger Stream

import React from 'react';
import { LiveAlertFeed } from '../../components/LiveAlertFeed';
import { useDashboard } from '../../lib/DashboardContext';

export default function AlertsPage() {
  const {
    events,
    selectedZoneId,
    handleOpenEventModal,
  } = useDashboard();

  return (
    <LiveAlertFeed
      events={events}
      selectedZoneId={selectedZoneId}
      onSelectEvent={handleOpenEventModal}
    />
  );
}
