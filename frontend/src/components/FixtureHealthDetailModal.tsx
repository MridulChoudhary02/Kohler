// frontend/src/components/FixtureHealthDetailModal.tsx — Fixture Predictive Health Detail & Sub-score Breakdown Modal

'use client';

import React, { useState, useEffect } from 'react';
import {
  X,
  Activity,
  AlertTriangle,
  CheckCircle2,
  TrendingDown,
  TrendingUp,
  Minus,
  ShieldAlert,
  Clock,
  Wrench,
  Droplets,
  Radio,
  Sliders,
  Sparkles,
  Info,
  Layers,
} from 'lucide-react';
import { FixtureHealthDetailResponse } from '../lib/types';
import { fetchFixtureHealthDetail } from '../lib/api';

interface FixtureHealthDetailModalProps {
  fixtureId: string | null;
  onClose: () => void;
}

function getStatusBadgeStyle(status: string) {
  switch (status) {
    case 'high_risk':
      return {
        bg: 'rgba(244, 63, 94, 0.15)',
        border: 'rgba(244, 63, 94, 0.3)',
        color: '#fb7185',
        dot: '#f43f5e',
        label: 'HIGH RISK',
      };
    case 'degrading':
      return {
        bg: 'rgba(249, 115, 22, 0.15)',
        border: 'rgba(249, 115, 22, 0.3)',
        color: '#fb923c',
        dot: '#f97316',
        label: 'DEGRADING',
      };
    case 'watch':
      return {
        bg: 'rgba(234, 179, 8, 0.15)',
        border: 'rgba(234, 179, 8, 0.3)',
        color: '#facc15',
        dot: '#eab308',
        label: 'WATCHLIST',
      };
    case 'healthy':
    default:
      return {
        bg: 'rgba(34, 197, 94, 0.15)',
        border: 'rgba(34, 197, 94, 0.3)',
        color: '#4ade80',
        dot: '#22c55e',
        label: 'HEALTHY',
      };
  }
}

function getHealthScoreColor(score: number): string {
  if (score >= 80) return '#4ade80'; // Emerald
  if (score >= 60) return '#facc15'; // Amber
  if (score >= 40) return '#fb923c'; // Orange
  return '#f43f5e'; // Rose
}

function getPenaltyColor(penalty: number): string {
  if (penalty >= 75) return '#f43f5e';
  if (penalty >= 40) return '#fb923c';
  if (penalty >= 15) return '#facc15';
  return '#4ade80';
}

function formatTimestamp(ts: string | null | undefined): string {
  if (!ts) return 'N/A';
  try {
    const d = new Date(ts);
    return d.toLocaleString([], {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    });
  } catch {
    return String(ts);
  }
}

export const FixtureHealthDetailModal: React.FC<FixtureHealthDetailModalProps> = ({
  fixtureId,
  onClose,
}) => {
  const [data, setData] = useState<FixtureHealthDetailResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!fixtureId) return;

    let isMounted = true;
    setLoading(true);
    setError(null);

    fetchFixtureHealthDetail(fixtureId)
      .then((res) => {
        if (isMounted) {
          setData(res);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err.message || 'Failed to load fixture health detail');
          setLoading(false);
        }
      });

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);

    return () => {
      isMounted = false;
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [fixtureId, onClose]);

  if (!fixtureId) return null;

  const statusStyle = data ? getStatusBadgeStyle(data.health_status) : null;
  const scoreColor = data ? getHealthScoreColor(data.health_score) : '#8f8f8f';

  return (
    <div
      className="modal-overlay"
      data-testid="fixture-health-modal-overlay"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0, 0, 0, 0.85)',
        backdropFilter: 'blur(8px)',
        zIndex: 50,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px',
      }}
    >
      <div
        className="command-panel"
        data-testid="fixture-health-modal-panel"
        style={{
          width: '100%',
          maxWidth: '920px',
          maxHeight: '92vh',
          overflowY: 'auto',
          borderRadius: '8px',
          border: '1px solid #262626',
          background: '#0d0d0d',
          boxShadow: '0 24px 64px rgba(0, 0, 0, 0.8)',
          position: 'relative',
        }}
      >
        {/* Header Bar */}
        <div
          style={{
            padding: '16px 20px',
            borderBottom: '1px solid #1f1f1f',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: '#121212',
            position: 'sticky',
            top: 0,
            zIndex: 10,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '6px',
                background: 'rgba(56, 189, 248, 0.1)',
                border: '1px solid rgba(56, 189, 248, 0.25)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Activity size={16} color="#38bdf8" />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h2
                  className="font-mono"
                  style={{ fontSize: '1.125rem', fontWeight: 700, color: '#ededed', margin: 0 }}
                >
                  {fixtureId}
                </h2>
                {data && (
                  <>
                    <span
                      style={{
                        fontSize: '0.6875rem',
                        padding: '2px 8px',
                        borderRadius: '4px',
                        background: '#1a1a1a',
                        border: '1px solid #2d2d2d',
                        color: '#a3a3a3',
                        textTransform: 'uppercase',
                        fontWeight: 600,
                      }}
                    >
                      {data.fixture_type.replace('_', ' ')}
                    </span>
                    <span className="tag-tech tag-tier1" style={{ fontSize: '0.6875rem' }}>
                      {data.zone_tier} • {data.zone_id}
                    </span>
                  </>
                )}
              </div>
              <p style={{ fontSize: '0.75rem', color: '#737373', margin: '2px 0 0 0' }}>
                Comprehensive Hydraulic Diagnostic & Failure Risk Profile
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            data-testid="btn-close-modal"
            style={{
              background: '#1a1a1a',
              border: '1px solid #2d2d2d',
              borderRadius: '6px',
              padding: '6px',
              color: '#a3a3a3',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all 0.15s ease',
            }}
          >
            <X size={16} />
          </button>
        </div>

        {/* Modal Content */}
        <div style={{ padding: '20px' }}>
          {loading && (
            <div style={{ padding: '60px 0', textAlign: 'center', color: '#737373' }}>
              <Activity size={28} className="animate-spin" style={{ margin: '0 auto 12px auto', color: '#38bdf8' }} />
              <div style={{ fontSize: '0.875rem' }}>Computing live fixture health diagnostic...</div>
            </div>
          )}

          {error && (
            <div
              style={{
                padding: '16px',
                borderRadius: '6px',
                background: 'rgba(244, 63, 94, 0.1)',
                border: '1px solid rgba(244, 63, 94, 0.25)',
                color: '#fb7185',
                fontSize: '0.8125rem',
              }}
            >
              {error}
            </div>
          )}

          {data && (
            <>
              {/* Hero Status & Health Score Card */}
              <div
                style={{
                  background: '#121212',
                  border: '1px solid #262626',
                  borderRadius: '8px',
                  padding: '18px 20px',
                  marginBottom: '18px',
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                  gap: '16px',
                  alignItems: 'center',
                }}
              >
                {/* Health Score Gauge */}
                <div>
                  <span style={{ fontSize: '0.6875rem', fontWeight: 600, color: '#8f8f8f', letterSpacing: '0.05em' }}>
                    PREDICTIVE HEALTH SCORE
                  </span>
                  <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginTop: '4px' }}>
                    <span
                      className="font-mono"
                      style={{ fontSize: '2.25rem', fontWeight: 800, color: scoreColor, lineHeight: 1 }}
                    >
                      {data.health_score.toFixed(1)}
                    </span>
                    <span style={{ fontSize: '0.875rem', color: '#737373', fontWeight: 500 }}>/ 100.0</span>
                  </div>
                  {/* Visual Bar Gauge */}
                  <div
                    style={{
                      height: '6px',
                      background: '#262626',
                      borderRadius: '3px',
                      overflow: 'hidden',
                      marginTop: '8px',
                    }}
                  >
                    <div
                      style={{
                        height: '100%',
                        width: `${Math.max(3, Math.min(100, data.health_score))}%`,
                        background: scoreColor,
                        borderRadius: '3px',
                        transition: 'width 0.4s ease',
                      }}
                    />
                  </div>
                </div>

                {/* Risk Score */}
                <div>
                  <span style={{ fontSize: '0.6875rem', fontWeight: 600, color: '#8f8f8f', letterSpacing: '0.05em' }}>
                    COMPOSITE FAILURE RISK
                  </span>
                  <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px', marginTop: '4px' }}>
                    <span
                      className="font-mono"
                      style={{ fontSize: '1.75rem', fontWeight: 700, color: '#ededed', lineHeight: 1 }}
                    >
                      {data.risk_score.toFixed(1)}
                    </span>
                    <span style={{ fontSize: '0.8125rem', color: '#737373' }}>pts penalty</span>
                  </div>
                  <div style={{ fontSize: '0.6875rem', color: '#737373', marginTop: '6px' }}>
                    Formula: 100.0 − Failure Risk
                  </div>
                </div>

                {/* Status Badge & Trend */}
                <div>
                  <span style={{ fontSize: '0.6875rem', fontWeight: 600, color: '#8f8f8f', letterSpacing: '0.05em' }}>
                    STATUS & 24H TREND
                  </span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '6px' }}>
                    {statusStyle && (
                      <span
                        style={{
                          fontSize: '0.75rem',
                          fontWeight: 700,
                          padding: '4px 10px',
                          borderRadius: '4px',
                          background: statusStyle.bg,
                          border: `1px solid ${statusStyle.border}`,
                          color: statusStyle.color,
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '6px',
                        }}
                      >
                        <span
                          style={{
                            width: '6px',
                            height: '6px',
                            borderRadius: '50%',
                            background: statusStyle.dot,
                          }}
                        />
                        {statusStyle.label}
                      </span>
                    )}

                    <span
                      style={{
                        fontSize: '0.75rem',
                        color:
                          data.trend === 'deteriorating'
                            ? '#f43f5e'
                            : data.trend === 'improving'
                            ? '#4ade80'
                            : '#8f8f8f',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '4px',
                        fontWeight: 600,
                      }}
                    >
                      {data.trend === 'deteriorating' && <TrendingDown size={14} />}
                      {data.trend === 'improving' && <TrendingUp size={14} />}
                      {data.trend === 'stable' && <Minus size={14} />}
                      {data.trend.toUpperCase()}
                    </span>
                  </div>
                </div>
              </div>

              {/* Operational Guidance Recommendation Banner */}
              <div
                style={{
                  background:
                    data.health_status === 'high_risk'
                      ? 'rgba(244, 63, 94, 0.08)'
                      : data.health_status === 'degrading'
                      ? 'rgba(249, 115, 22, 0.08)'
                      : data.health_status === 'watch'
                      ? 'rgba(234, 179, 8, 0.08)'
                      : 'rgba(34, 197, 94, 0.08)',
                  border: `1px solid ${
                    data.health_status === 'high_risk'
                      ? 'rgba(244, 63, 94, 0.25)'
                      : data.health_status === 'degrading'
                      ? 'rgba(249, 115, 22, 0.25)'
                      : data.health_status === 'watch'
                      ? 'rgba(234, 179, 8, 0.25)'
                      : 'rgba(34, 197, 94, 0.25)'
                  }`,
                  borderRadius: '6px',
                  padding: '14px 16px',
                  marginBottom: '20px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                }}
              >
                {data.health_status === 'high_risk' ? (
                  <ShieldAlert size={20} color="#f43f5e" style={{ flexShrink: 0 }} />
                ) : data.health_status === 'degrading' ? (
                  <AlertTriangle size={20} color="#f97316" style={{ flexShrink: 0 }} />
                ) : data.health_status === 'watch' ? (
                  <Wrench size={20} color="#eab308" style={{ flexShrink: 0 }} />
                ) : (
                  <CheckCircle2 size={20} color="#22c55e" style={{ flexShrink: 0 }} />
                )}
                <div>
                  <div style={{ fontSize: '0.6875rem', fontWeight: 600, color: '#8f8f8f', letterSpacing: '0.04em' }}>
                    OPERATIONAL DIRECTIVE & RECOMMENDATION
                  </div>
                  <div style={{ fontSize: '0.875rem', fontWeight: 600, color: '#ededed', marginTop: '2px' }}>
                    {data.recommendation}
                  </div>
                </div>
              </div>

              {/* Sub-scores Diagnostic Breakdown */}
              <div style={{ marginBottom: '24px' }}>
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    marginBottom: '12px',
                    paddingBottom: '8px',
                    borderBottom: '1px solid #1f1f1f',
                  }}
                >
                  <h3
                    style={{
                      fontSize: '0.75rem',
                      fontWeight: 700,
                      color: '#ededed',
                      letterSpacing: '0.06em',
                      textTransform: 'uppercase',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      margin: 0,
                    }}
                  >
                    <Sliders size={14} color="#38bdf8" />
                    Six-Factor Failure Risk Decomposition
                  </h3>
                  <span style={{ fontSize: '0.6875rem', color: '#737373' }}>
                    Weighted Risk Composition (0–100 Penalty Scale)
                  </span>
                </div>

                <div
                  data-testid="subscores-breakdown-grid"
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                    gap: '12px',
                  }}
                >
                  {[
                    {
                      label: 'Anomaly Frequency Risk',
                      score: data.sub_scores.frequency_score,
                      weight: '30%',
                      contribution: (data.sub_scores.frequency_score * 0.3).toFixed(1),
                      desc: `${data.total_incidents} dispatched events (norm: 8.0)`,
                    },
                    {
                      label: 'Recurrence Acceleration Risk',
                      score: data.sub_scores.recurrence_score,
                      weight: '20%',
                      contribution: (data.sub_scores.recurrence_score * 0.2).toFixed(1),
                      desc: 'Repeated breaches within <= 24h gap (norm: 6.0)',
                    },
                    {
                      label: 'Idle Flow Drift Penalty',
                      score: data.sub_scores.flow_drift_score,
                      weight: '20%',
                      contribution: (data.sub_scores.flow_drift_score * 0.2).toFixed(1),
                      desc: 'Evaluated vs. active time-of-day baseline segment',
                    },
                    {
                      label: 'Slow Ramp Leak Risk',
                      score: data.sub_scores.slow_leak_score,
                      weight: '15%',
                      contribution: (data.sub_scores.slow_leak_score * 0.15).toFixed(1),
                      desc: 'Gradual linear leak growth persistence',
                    },
                    {
                      label: 'Sensor Diagnostics Penalty',
                      score: data.sub_scores.sensor_health_score,
                      weight: '10%',
                      contribution: (data.sub_scores.sensor_health_score * 0.1).toFixed(1),
                      desc: `${data.sensor_faults_count} sensor fault/flatline anomalies`,
                    },
                    {
                      label: 'Unresolved Tickets Penalty',
                      score: data.sub_scores.unresolved_score,
                      weight: '5%',
                      contribution: (data.sub_scores.unresolved_score * 0.05).toFixed(1),
                      desc: `${data.active_tickets_count} unclosed active maintenance tickets`,
                    },
                  ].map((item, idx) => {
                    const barColor = getPenaltyColor(item.score);
                    return (
                      <div
                        key={idx}
                        style={{
                          background: '#141414',
                          border: '1px solid #242424',
                          borderRadius: '6px',
                          padding: '12px 14px',
                        }}
                      >
                        <div
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            marginBottom: '4px',
                          }}
                        >
                          <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#d4d4d4' }}>
                            {item.label}
                          </span>
                          <span
                            className="font-mono"
                            style={{ fontSize: '0.8125rem', fontWeight: 700, color: barColor }}
                          >
                            {item.score.toFixed(1)}
                          </span>
                        </div>

                        {/* Visual Progress Bar */}
                        <div
                          style={{
                            height: '5px',
                            background: '#262626',
                            borderRadius: '3px',
                            overflow: 'hidden',
                            margin: '6px 0',
                          }}
                        >
                          <div
                            style={{
                              height: '100%',
                              width: `${Math.max(2, Math.min(100, item.score))}%`,
                              background: barColor,
                              borderRadius: '3px',
                            }}
                          />
                        </div>

                        <div
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            fontSize: '0.6875rem',
                            color: '#737373',
                          }}
                        >
                          <span>{item.desc}</span>
                          <span style={{ color: '#8f8f8f' }}>
                            w: {item.weight} (+{item.contribution} pts)
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Chronological Recent Incidents Table */}
              <div>
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    marginBottom: '12px',
                    paddingBottom: '8px',
                    borderBottom: '1px solid #1f1f1f',
                  }}
                >
                  <h3
                    style={{
                      fontSize: '0.75rem',
                      fontWeight: 700,
                      color: '#ededed',
                      letterSpacing: '0.06em',
                      textTransform: 'uppercase',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      margin: 0,
                    }}
                  >
                    <Layers size={14} color="#38bdf8" />
                    Chronological Detection History ({data.recent_incidents.length} recent)
                  </h3>
                  <span style={{ fontSize: '0.6875rem', color: '#737373' }}>
                    Resolved via Live Detection Events & Dispatch Engine
                  </span>
                </div>

                {data.recent_incidents.length === 0 ? (
                  <div
                    style={{
                      padding: '30px',
                      textAlign: 'center',
                      background: '#121212',
                      border: '1px solid #242424',
                      borderRadius: '6px',
                      color: '#737373',
                      fontSize: '0.8125rem',
                    }}
                  >
                    <CheckCircle2 size={20} color="#22c55e" style={{ margin: '0 auto 8px auto' }} />
                    No detection events logged for this fixture. Normal hydraulic operation.
                  </div>
                ) : (
                  <div
                    style={{
                      borderRadius: '6px',
                      border: '1px solid #242424',
                      overflow: 'hidden',
                      background: '#121212',
                    }}
                  >
                    <table
                      style={{
                        width: '100%',
                        borderCollapse: 'collapse',
                        fontSize: '0.75rem',
                        textAlign: 'left',
                      }}
                    >
                      <thead>
                        <tr style={{ background: '#171717', borderBottom: '1px solid #262626' }}>
                          <th style={{ padding: '10px 12px', color: '#8f8f8f', fontWeight: 600 }}>DETECTED AT</th>
                          <th style={{ padding: '10px 12px', color: '#8f8f8f', fontWeight: 600 }}>TYPE & RULE</th>
                          <th style={{ padding: '10px 12px', color: '#8f8f8f', fontWeight: 600 }}>CONFIDENCE</th>
                          <th style={{ padding: '10px 12px', color: '#8f8f8f', fontWeight: 600 }}>EVIDENCE / IMPACT</th>
                          <th style={{ padding: '10px 12px', color: '#8f8f8f', fontWeight: 600 }}>TICKET STATUS</th>
                          <th style={{ padding: '10px 12px', color: '#8f8f8f', fontWeight: 600 }}>PRIORITY</th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.recent_incidents.map((inc, i) => (
                          <tr
                            key={inc.event_id || i}
                            style={{
                              borderBottom: i < data.recent_incidents.length - 1 ? '1px solid #1c1c1c' : 'none',
                              transition: 'background 0.12s ease',
                            }}
                          >
                            <td className="font-mono" style={{ padding: '10px 12px', color: '#a3a3a3' }}>
                              {formatTimestamp(inc.detected_at)}
                            </td>
                            <td style={{ padding: '10px 12px' }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                <span
                                  style={{
                                    fontSize: '0.6875rem',
                                    padding: '1px 6px',
                                    borderRadius: '3px',
                                    background:
                                      inc.event_type === 'leak'
                                        ? 'rgba(244, 63, 94, 0.15)'
                                        : inc.event_type === 'sensor_fault'
                                        ? 'rgba(234, 179, 8, 0.15)'
                                        : 'rgba(56, 189, 248, 0.15)',
                                    color:
                                      inc.event_type === 'leak'
                                        ? '#fb7185'
                                        : inc.event_type === 'sensor_fault'
                                        ? '#facc15'
                                        : '#38bdf8',
                                    fontWeight: 600,
                                    textTransform: 'uppercase',
                                  }}
                                >
                                  {inc.event_type}
                                </span>
                                <span style={{ color: '#e5e5e5', fontWeight: 500 }}>{inc.rule_label}</span>
                              </div>
                            </td>
                            <td className="font-mono" style={{ padding: '10px 12px', color: '#ededed' }}>
                              {(inc.confidence_score * 100).toFixed(1)}%
                            </td>
                            <td className="font-mono" style={{ padding: '10px 12px', color: '#ededed' }}>
                              {inc.evidence_value !== null ? (
                                inc.event_type === 'leak' ? (
                                  `${inc.evidence_value} L/h`
                                ) : inc.event_type === 'hygiene' ? (
                                  `${inc.evidence_value} min`
                                ) : (
                                  inc.evidence_value
                                )
                              ) : (
                                '—'
                              )}
                            </td>
                            <td style={{ padding: '10px 12px' }}>
                              {inc.ticket_status ? (
                                <span
                                  style={{
                                    fontSize: '0.6875rem',
                                    padding: '2px 8px',
                                    borderRadius: '4px',
                                    fontWeight: 600,
                                    textTransform: 'uppercase',
                                    background:
                                      inc.ticket_status === 'resolved'
                                        ? 'rgba(34, 197, 94, 0.15)'
                                        : inc.ticket_status === 'in_progress'
                                        ? 'rgba(56, 189, 248, 0.15)'
                                        : 'rgba(244, 63, 94, 0.15)',
                                    color:
                                      inc.ticket_status === 'resolved'
                                        ? '#4ade80'
                                        : inc.ticket_status === 'in_progress'
                                        ? '#38bdf8'
                                        : '#fb7185',
                                  }}
                                >
                                  {inc.ticket_status.replace('_', ' ')}
                                </span>
                              ) : (
                                <span style={{ color: '#737373' }}>None</span>
                              )}
                            </td>
                            <td className="font-mono" style={{ padding: '10px 12px', color: '#ededed' }}>
                              {inc.priority_score !== null ? inc.priority_score.toFixed(1) : '—'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
