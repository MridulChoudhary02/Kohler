// frontend/src/app/fixtures/health/page.tsx — Predictive Fixture Health & Failure Risk Command Center

'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  Activity,
  ShieldAlert,
  AlertTriangle,
  Wrench,
  CheckCircle2,
  TrendingDown,
  TrendingUp,
  Minus,
  Filter,
  ArrowUpDown,
  Sparkles,
  ChevronRight,
  RefreshCw,
  Search,
} from 'lucide-react';
import { FixtureHealthListResponse, FixtureHealthItem } from '../../../lib/types';
import { fetchFixtureHealthList } from '../../../lib/api';
import { FixtureHealthDetailModal } from '../../../components/FixtureHealthDetailModal';

function getStatusBadgeStyle(status: string) {
  switch (status) {
    case 'high_risk':
      return {
        bg: 'rgba(244, 63, 94, 0.15)',
        border: 'rgba(244, 63, 94, 0.35)',
        color: '#fb7185',
        dot: '#f43f5e',
        label: 'HIGH RISK',
      };
    case 'degrading':
      return {
        bg: 'rgba(249, 115, 22, 0.15)',
        border: 'rgba(249, 115, 22, 0.35)',
        color: '#fb923c',
        dot: '#f97316',
        label: 'DEGRADING',
      };
    case 'watch':
      return {
        bg: 'rgba(234, 179, 8, 0.15)',
        border: 'rgba(234, 179, 8, 0.35)',
        color: '#facc15',
        dot: '#eab308',
        label: 'WATCH',
      };
    case 'healthy':
    default:
      return {
        bg: 'rgba(34, 197, 94, 0.15)',
        border: 'rgba(34, 197, 94, 0.35)',
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

export default function FixtureHealthPage() {
  const [data, setData] = useState<FixtureHealthListResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [zoneFilter, setZoneFilter] = useState<string>('');
  const [sortBy, setSortBy] = useState<string>('risk_desc');
  const [selectedFixtureId, setSelectedFixtureId] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetchFixtureHealthList({
        status: statusFilter || undefined,
        zone_id: zoneFilter || undefined,
        sort_by: sortBy,
      });
      setData(res);
    } catch (err) {
      console.error('Failed to load fixture health:', err);
    } finally {
      setLoading(false);
    }
  }, [statusFilter, zoneFilter, sortBy]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Top KPI tiles reusing FacilityKpiRow styling
  const kpis = data
    ? [
        {
          id: 'facility-health',
          label: 'FACILITY HEALTH SCORE',
          value: `${data.facility_health_score.toFixed(1)}%`,
          unit: '',
          subtext: 'Mean across all 20 hospital fixtures',
          icon: Activity,
          topColor: getHealthScoreColor(data.facility_health_score),
          iconColor: getHealthScoreColor(data.facility_health_score),
        },
        {
          id: 'high-risk-fixtures',
          label: 'HIGH RISK FIXTURES',
          value: `${data.high_risk_count}`,
          unit: 'fixtures',
          subtext: 'Score < 40 — immediate intervention',
          icon: ShieldAlert,
          topColor: '#f43f5e',
          iconColor: '#f43f5e',
        },
        {
          id: 'degrading-fixtures',
          label: 'DEGRADING FIXTURES',
          value: `${data.degrading_count}`,
          unit: 'fixtures',
          subtext: 'Score 40–59 — elevated incident rate',
          icon: AlertTriangle,
          topColor: '#fb923c',
          iconColor: '#fb923c',
        },
        {
          id: 'watch-fixtures',
          label: 'WATCHLIST FIXTURES',
          value: `${data.watch_count}`,
          unit: 'fixtures',
          subtext: 'Score 60–79 — sensor & drift monitoring',
          icon: Wrench,
          topColor: '#facc15',
          iconColor: '#facc15',
        },
        {
          id: 'healthy-fixtures',
          label: 'HEALTHY FIXTURES',
          value: `${data.healthy_count}`,
          unit: 'fixtures',
          subtext: 'Score 80–100 — standard maintenance',
          icon: CheckCircle2,
          topColor: '#4ade80',
          iconColor: '#4ade80',
        },
      ]
    : [];

  return (
    <div style={{ maxWidth: '1600px', margin: '0 auto', padding: '24px' }}>
      {/* Top Facility KPI Row — Reusing exact FacilityKpiRow styling */}
      <div className="command-panel" style={{ padding: '20px', marginBottom: '20px' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: '16px',
          }}
          className="tech-divider"
        >
          <div style={{ paddingBottom: '12px' }}>
            <h2
              style={{
                fontSize: '0.75rem',
                fontWeight: 600,
                color: '#8f8f8f',
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                margin: 0,
              }}
            >
              <Sparkles size={14} color="#38bdf8" />
              FACILITY PREDICTIVE HEALTH & FAILURE RISK METRICS
            </h2>
          </div>
          <div
            style={{
              fontSize: '0.7rem',
              color: '#737373',
              paddingBottom: '12px',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <span className="status-dot status-dot-emerald" />
            Live Statistical Scoring Engine
          </div>
        </div>

        <div
          data-testid="facility-health-kpi-row"
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))',
            gap: '14px',
          }}
        >
          {kpis.map((kpi) => {
            const Icon = kpi.icon;
            return (
              <div
                key={kpi.id}
                style={{
                  background: '#121212',
                  border: '1px solid #262626',
                  borderTop: `3px solid ${kpi.topColor}`,
                  borderRadius: '6px',
                  padding: '16px 14px',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    justifyContent: 'space-between',
                    marginBottom: '12px',
                  }}
                >
                  <span
                    style={{
                      fontSize: '0.6875rem',
                      fontWeight: 600,
                      color: '#8f8f8f',
                      letterSpacing: '0.05em',
                    }}
                  >
                    {kpi.label}
                  </span>
                  <div
                    style={{
                      width: '28px',
                      height: '28px',
                      borderRadius: '5px',
                      background: 'rgba(255, 255, 255, 0.03)',
                      border: '1px solid rgba(255, 255, 255, 0.06)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    <Icon size={14} color={kpi.iconColor} />
                  </div>
                </div>

                <div>
                  <div
                    className="font-mono"
                    style={{ fontSize: '1.5rem', fontWeight: 700, color: '#ededed', lineHeight: 1.1 }}
                  >
                    {kpi.value}{' '}
                    {kpi.unit && (
                      <span style={{ fontSize: '0.8125rem', fontWeight: 400, color: '#8f8f8f' }}>
                        {kpi.unit}
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: '0.6875rem', color: '#737373', marginTop: '6px' }}>
                    {kpi.subtext}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Filter and Sort Toolbar */}
      <div
        className="command-panel"
        style={{
          padding: '14px 18px',
          marginBottom: '18px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '14px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#8f8f8f', fontSize: '0.75rem' }}>
            <Filter size={14} />
            <span>Filter Status:</span>
          </div>

          <div style={{ display: 'flex', gap: '4px' }}>
            {[
              { label: 'All', val: '' },
              { label: 'High Risk', val: 'high_risk' },
              { label: 'Degrading', val: 'degrading' },
              { label: 'Watch', val: 'watch' },
              { label: 'Healthy', val: 'healthy' },
            ].map((st) => (
              <button
                key={st.val}
                onClick={() => setStatusFilter(st.val)}
                data-testid={`filter-status-${st.val || 'all'}`}
                style={{
                  background: statusFilter === st.val ? '#262626' : '#141414',
                  border: statusFilter === st.val ? '1px solid #404040' : '1px solid #222',
                  borderRadius: '4px',
                  padding: '4px 10px',
                  fontSize: '0.75rem',
                  fontWeight: statusFilter === st.val ? 600 : 400,
                  color: statusFilter === st.val ? '#ffffff' : '#8f8f8f',
                  cursor: 'pointer',
                  transition: 'all 0.12s ease',
                }}
              >
                {st.label}
              </button>
            ))}
          </div>

          <div style={{ width: '1px', height: '20px', background: '#262626', margin: '0 4px' }} />

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#8f8f8f', fontSize: '0.75rem' }}>
            <span>Zone:</span>
            <select
              value={zoneFilter}
              onChange={(e) => setZoneFilter(e.target.value)}
              data-testid="select-zone-filter"
              style={{
                background: '#141414',
                border: '1px solid #262626',
                borderRadius: '4px',
                padding: '4px 10px',
                fontSize: '0.75rem',
                color: '#ededed',
                cursor: 'pointer',
              }}
            >
              <option value="">All Hospital Zones</option>
              <option value="zone-icu">ICU (Tier 1)</option>
              <option value="zone-ot">Operating Theatre (Tier 1)</option>
              <option value="zone-ward">General Ward (Tier 2)</option>
              <option value="zone-lab">Laboratory (Tier 3)</option>
              <option value="zone-lobby">Public Lobby (Tier 4)</option>
            </select>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <ArrowUpDown size={14} color="#8f8f8f" />
          <span style={{ fontSize: '0.75rem', color: '#8f8f8f' }}>Sort:</span>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            data-testid="select-sort-by"
            style={{
              background: '#141414',
              border: '1px solid #262626',
              borderRadius: '4px',
              padding: '4px 10px',
              fontSize: '0.75rem',
              color: '#ededed',
              cursor: 'pointer',
            }}
          >
            <option value="risk_desc">Risk: High → Low</option>
            <option value="health_asc">Health: Low → High</option>
            <option value="health_desc">Health: High → Low</option>
            <option value="incidents_desc">Incidents: High → Low</option>
          </select>
          <button
            onClick={() => loadData()}
            title="Refresh"
            style={{
              background: '#141414',
              border: '1px solid #262626',
              borderRadius: '4px',
              padding: '6px',
              color: '#8f8f8f',
              cursor: 'pointer',
            }}
          >
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {/* Fixtures List Section */}
      <div className="command-panel" style={{ padding: '0', overflow: 'hidden' }}>
        <div
          style={{
            padding: '14px 20px',
            background: '#141414',
            borderBottom: '1px solid #222',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#ededed', letterSpacing: '0.04em' }}>
            FIXTURE HEALTH MATRIX ({data?.fixtures.length || 0} fixtures)
          </div>
          <div style={{ fontSize: '0.6875rem', color: '#737373' }}>
            Click any row for six-factor diagnostic breakdown & telemetry history
          </div>
        </div>

        {loading && !data && (
          <div style={{ padding: '60px 0', textAlign: 'center', color: '#737373' }}>
            <Activity size={24} className="animate-spin" style={{ margin: '0 auto 8px auto', color: '#38bdf8' }} />
            <div style={{ fontSize: '0.8125rem' }}>Loading fixture health telemetry...</div>
          </div>
        )}

        {data && (
          <div style={{ display: 'flex', flexDirection: 'column' }} data-testid="fixture-health-list">
            {data.fixtures.map((fixture) => {
              const statusStyle = getStatusBadgeStyle(fixture.health_status);
              const scoreColor = getHealthScoreColor(fixture.health_score);

              return (
                <div
                  key={fixture.fixture_id}
                  data-testid={`fixture-health-row-${fixture.fixture_id}`}
                  onClick={() => setSelectedFixtureId(fixture.fixture_id)}
                  style={{
                    padding: '16px 20px',
                    borderBottom: '1px solid #1a1a1a',
                    display: 'grid',
                    gridTemplateColumns: 'minmax(180px, 1.2fr) minmax(130px, 0.9fr) minmax(160px, 1fr) minmax(110px, 0.7fr) minmax(280px, 2.5fr) 40px',
                    alignItems: 'center',
                    gap: '16px',
                    cursor: 'pointer',
                    transition: 'background 0.12s ease',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = '#141414')}
                  onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                >
                  {/* Fixture ID & Zone */}
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span
                        className="font-mono"
                        style={{ fontSize: '0.875rem', fontWeight: 700, color: '#ededed' }}
                      >
                        {fixture.fixture_id}
                      </span>
                      <span
                        style={{
                          fontSize: '0.625rem',
                          padding: '1px 6px',
                          borderRadius: '3px',
                          background: '#1c1c1c',
                          border: '1px solid #2b2b2b',
                          color: '#a3a3a3',
                          textTransform: 'uppercase',
                          fontWeight: 600,
                        }}
                      >
                        {fixture.fixture_type.replace('_', ' ')}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.6875rem', color: '#737373', marginTop: '2px' }}>
                      {fixture.zone_tier} • {fixture.zone_id}
                    </div>
                  </div>

                  {/* Health Score & Visual Gauge Bar */}
                  <div>
                    <div style={{ display: 'flex', alignItems: 'baseline', gap: '4px' }}>
                      <span
                        className="font-mono"
                        style={{ fontSize: '1.125rem', fontWeight: 700, color: scoreColor }}
                      >
                        {fixture.health_score.toFixed(1)}
                      </span>
                      <span style={{ fontSize: '0.6875rem', color: '#737373' }}>/ 100</span>
                    </div>
                    {/* Visual bar */}
                    <div
                      style={{
                        height: '4px',
                        background: '#262626',
                        borderRadius: '2px',
                        overflow: 'hidden',
                        marginTop: '4px',
                        width: '100px',
                      }}
                    >
                      <div
                        style={{
                          height: '100%',
                          width: `${Math.max(3, Math.min(100, fixture.health_score))}%`,
                          background: scoreColor,
                          borderRadius: '2px',
                        }}
                      />
                    </div>
                  </div>

                  {/* Status Badge & Trend */}
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span
                        style={{
                          fontSize: '0.6875rem',
                          fontWeight: 700,
                          padding: '2px 8px',
                          borderRadius: '4px',
                          background: statusStyle.bg,
                          border: `1px solid ${statusStyle.border}`,
                          color: statusStyle.color,
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '5px',
                        }}
                      >
                        <span
                          style={{
                            width: '5px',
                            height: '5px',
                            borderRadius: '50%',
                            background: statusStyle.dot,
                          }}
                        />
                        {statusStyle.label}
                      </span>

                      {/* Trend Indicator */}
                      <span
                        style={{
                          fontSize: '0.6875rem',
                          color:
                            fixture.trend === 'deteriorating'
                              ? '#f43f5e'
                              : fixture.trend === 'improving'
                              ? '#4ade80'
                              : '#8f8f8f',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '2px',
                          fontWeight: 600,
                        }}
                      >
                        {fixture.trend === 'deteriorating' && <TrendingDown size={12} />}
                        {fixture.trend === 'improving' && <TrendingUp size={12} />}
                        {fixture.trend === 'stable' && <Minus size={12} />}
                        {fixture.trend.charAt(0).toUpperCase() + fixture.trend.slice(1)}
                      </span>
                    </div>
                  </div>

                  {/* Incidents Count */}
                  <div>
                    <div className="font-mono" style={{ fontSize: '0.8125rem', color: '#d4d4d4', fontWeight: 600 }}>
                      {fixture.total_incidents} {fixture.total_incidents === 1 ? 'event' : 'events'}
                    </div>
                    <div style={{ fontSize: '0.6875rem', color: '#737373', marginTop: '1px' }}>
                      {fixture.active_tickets_count} open ticket{fixture.active_tickets_count === 1 ? '' : 's'}
                    </div>
                  </div>

                  {/* Recommendation Text */}
                  <div style={{ fontSize: '0.75rem', color: '#a3a3a3', lineHeight: 1.3 }}>
                    <span style={{ color: '#d4d4d4', fontWeight: 500 }}>{fixture.recommendation}</span>
                  </div>

                  {/* Drilldown Arrow */}
                  <div style={{ display: 'flex', justifyContent: 'flex-end', color: '#737373' }}>
                    <ChevronRight size={16} />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Fixture Health Detail Modal */}
      {selectedFixtureId && (
        <FixtureHealthDetailModal
          fixtureId={selectedFixtureId}
          onClose={() => setSelectedFixtureId(null)}
        />
      )}
    </div>
  );
}
