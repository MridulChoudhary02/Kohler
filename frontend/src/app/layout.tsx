// frontend/src/app/layout.tsx — Next.js 14 Root Layout

import './globals.css';
import React from 'react';

export const metadata = {
  title: 'Kohler Smart Facility & Sustainability Manager — Hospital Command Center',
  description: 'Real-time telemetry, layered leak detection, hygiene prediction, and ticket dispatch dashboard.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body>{children}</body>
    </html>
  );
}
