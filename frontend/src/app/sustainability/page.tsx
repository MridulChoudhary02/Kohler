// frontend/src/app/sustainability/page.tsx — Water-Savings & Sustainability Impact Command Center

'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  Droplets,
  ShieldAlert,
  AlertTriangle,
  TrendingDown,
  TrendingUp,
  Clock,
  Sparkles,
  ArrowRight,
  RefreshCw,
  Info,
  CheckCircle2,
  Calendar,
  Building2,
} from 'lucide-react';
import { SustainabilitySummary } from '../../lib/types';
import { fetchSustainabilitySummary } from '../../lib/api';

export default function SustainabilityPage() {
  const [data, setData] = useState<SustainabilitySummary | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchSustainabilitySummary(6.0);
      setData(res);
    } catch (err: any) {
      console.error('Failed to load sustainability summary:', err);
      setError(err?.message || 'Failed to load sustainability metrics');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const kpiTiles = data
    ? [
        {
          id: 'kpi-water-wasted',
          label: 'CURRENT WATER WASTED',
          value: `${data.water_waste_liters.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 })} L`,
          subtext: `Cost impact ₹${data.cost_impact.toFixed(2)} at ₹0.15/L`,
          icon: Droplets,
          topColor: '#f43f5e',
          iconColor: '#f43f5e',
        },
        {
          id: 'kpi-water-saved',
          label: 'ESTIMATED WATER SAVED',
          value: `${data.estimated_water_saved_liters.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 })} L`,
          subtext: `Avoided ₹${data.avoided_cost.toFixed(2)} (6h baseline)`,
          icon: CheckCircle2,
          topColor: '#4ade80',
          iconColor: '#4ade80',
        },
        {
          id: 'kpi-cost-impact',
          label: 'COST AT RISK / IMPACT',
          value: `₹${data.cost_impact.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
          subtext: `Commercial tariff ₹0.15 / L`,
          icon: AlertTriangle,
          topColor: '#f59e0b',
          iconColor: '#f59e0b',
        },
        {
          id: 'kpi-avoided-cost',
          label: 'ESTIMATED AVOIDED COST',
          value: `₹${data.avoided_cost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
          subtext: `From ${data.resolved_leaks_with_impact_count} resolved leak interventions`,
          icon: TrendingDown,
          topColor: '#38bdf8',
          iconColor: '#38bdf8',
        },
        {
          id: 'kpi-projected-loss',
          label: 'PROJECTED UNRESOLVED LOSS (+24H)',
          value: `${data.projected_unresolved_loss_liters.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 })} L`,
          subtext: `Across ${data.active_leak_tickets_count} active leak incidents`,
          icon: Clock,
          topColor: '#fb923c',
          iconColor: '#fb923c',
        },
      ]
    : [];

  return (
    <div style={{ maxWidth: '1600px', margin: '0 auto', padding: '24px' }}>
      {/* Top Header & Refresh Control */}
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
            <h1
              style={{
                fontSize: '0.85rem',
                fontWeight: 700,
                color: '#f4f4f5',
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                margin: 0,
              }}
            >
              <Droplets size={16} color="#38bdf8" />
              SUSTAINABILITY & WATER-SAVINGS IMPACT COMMAND CENTER
            </h1>
            <div style={{ fontSize: '0.72rem', color: '#71717a', marginTop: '4px' }}>
              Real-time water loss telemetry, counterfactual prevented waste, and active incident projection modeling
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', paddingBottom: '12px' }}>
            <div
              style={{
                fontSize: '0.7rem',
                color: '#737373',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              <span className="status-dot status-dot-emerald" />
              ₹0.15/L Commercial Tariff Active
            </div>
            <button
              onClick={loadData}
              disabled={loading}
              className="btn-pill"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 14px',
                background: '#18181b',
                border: '1px solid #27272a',
                color: '#e4e4e7',
                fontSize: '0.75rem',
                borderRadius: '6px',
                cursor: loading ? 'not-allowed' : 'pointer',
              }}
            >
              <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
              {loading ? 'Refreshing...' : 'Refresh'}
            </button>
          </div>
        </div>

        {/* Top KPI Row */}
        {loading && !data ? (
          <div style={{ padding: '30px', textAlign: 'center', color: '#71717a', fontSize: '0.85rem' }}>
            Loading live facility sustainability metrics...
          </div>
        ) : error ? (
          <div style={{ padding: '20px', background: '#261b17', border: '1px solid #b45309', borderRadius: '6px', color: '#fef3c7', fontSize: '0.82rem' }}>
            {error}
          </div>
        ) : (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
              gap: '14px',
            }}
          >
            {kpiTiles.map((kpi) => {
              const IconComp = kpi.icon;
              return (
                <div
                  key={kpi.id}
                  id={kpi.id}
                  className="kpi-tile"
                  style={{
                    borderTop: `2px solid ${kpi.topColor}`,
                    background: '#141417',
                    padding: '14px 16px',
                    borderRadius: '6px',
                    border: '1px solid #222225',
                    borderTopColor: kpi.topColor,
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                    <span style={{ fontSize: '0.68rem', fontWeight: 600, color: '#828288', letterSpacing: '0.04em' }}>
                      {kpi.label}
                    </span>
                    <IconComp size={15} color={kpi.iconColor} />
                  </div>
                  <div>
                    <div className="font-mono" style={{ fontSize: '1.45rem', fontWeight: 700, color: '#f4f4f5', lineHeight: 1.2 }}>
                      {kpi.value}
                    </div>
                    <div style={{ fontSize: '0.68rem', color: '#71717a', marginTop: '4px' }}>
                      {kpi.subtext}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Incident Loss Projection Horizons Matrix */}
      {data && (
        <div className="command-panel" style={{ padding: '20px', marginBottom: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Clock size={16} color="#38bdf8" />
              <div>
                <h2 style={{ fontSize: '0.78rem', fontWeight: 700, color: '#f4f4f5', letterSpacing: '0.04em', textTransform: 'uppercase', margin: 0 }}>
                  ACTIVE INCIDENT LOSS PROJECTION HORIZONS
                </h2>
                <div style={{ fontSize: '0.68rem', color: '#71717a', marginTop: '2px' }}>
                  Forward-looking loss projection across {data.active_leak_tickets_count} active leak incidents: projected_loss = observed_flow_lpm × horizon_minutes
                </div>
              </div>
            </div>
            <div style={{ fontSize: '0.68rem', color: '#a1a1aa', background: '#18181b', padding: '4px 10px', borderRadius: '4px', border: '1px solid #27272a' }}>
              Active Exposure Rate: {((data.facility_projections.plus_1hr_liters / 60)).toFixed(2)} LPM
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '14px' }}>
            {/* +1 HOUR */}
            <div style={{ background: '#111113', border: '1px solid #27272a', borderRadius: '6px', padding: '14px 16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                <span style={{ fontSize: '0.7rem', color: '#a1a1aa', fontWeight: 600 }}>+1 HOUR HORIZON</span>
                <span style={{ fontSize: '0.65rem', background: '#27272a', color: '#d4d4d8', padding: '2px 6px', borderRadius: '4px' }}>Immediate</span>
              </div>
              <div className="font-mono" style={{ fontSize: '1.3rem', fontWeight: 700, color: '#f43f5e' }}>
                {data.facility_projections.plus_1hr_liters.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 })} L
              </div>
              <div style={{ fontSize: '0.72rem', color: '#f59e0b', marginTop: '4px', fontWeight: 500 }} className="font-mono">
                ₹{data.facility_projections.plus_1hr_cost_inr.toFixed(2)} at risk
              </div>
              <div style={{ fontSize: '0.65rem', color: '#71717a', marginTop: '4px' }}>
                Short-term response SLA window
              </div>
            </div>

            {/* +6 HOURS */}
            <div style={{ background: '#111113', border: '1px solid #27272a', borderRadius: '6px', padding: '14px 16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                <span style={{ fontSize: '0.7rem', color: '#a1a1aa', fontWeight: 600 }}>+6 HOURS HORIZON</span>
                <span style={{ fontSize: '0.65rem', background: '#3f3f46', color: '#e4e4e7', padding: '2px 6px', borderRadius: '4px' }}>Shift Window</span>
              </div>
              <div className="font-mono" style={{ fontSize: '1.3rem', fontWeight: 700, color: '#f43f5e' }}>
                {data.facility_projections.plus_6hr_liters.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 })} L
              </div>
              <div style={{ fontSize: '0.72rem', color: '#f59e0b', marginTop: '4px', fontWeight: 500 }} className="font-mono">
                ₹{data.facility_projections.plus_6hr_cost_inr.toFixed(2)} at risk
              </div>
              <div style={{ fontSize: '0.65rem', color: '#71717a', marginTop: '4px' }}>
                One operational technician shift
              </div>
            </div>

            {/* +24 HOURS */}
            <div style={{ background: '#181114', border: '1px solid #4c1d24', borderRadius: '6px', padding: '14px 16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                <span style={{ fontSize: '0.7rem', color: '#fca5a5', fontWeight: 600 }}>+24 HOURS HORIZON</span>
                <span style={{ fontSize: '0.65rem', background: '#7f1d1d', color: '#fecaca', padding: '2px 6px', borderRadius: '4px', fontWeight: 600 }}>Unresolved</span>
              </div>
              <div className="font-mono" style={{ fontSize: '1.3rem', fontWeight: 700, color: '#f87171' }}>
                {data.facility_projections.plus_24hr_liters.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 })} L
              </div>
              <div style={{ fontSize: '0.72rem', color: '#f59e0b', marginTop: '4px', fontWeight: 500 }} className="font-mono">
                ₹{data.facility_projections.plus_24hr_cost_inr.toFixed(2)} at risk
              </div>
              <div style={{ fontSize: '0.65rem', color: '#a1a1aa', marginTop: '4px' }}>
                Full-day cumulative unmitigated exposure
              </div>
            </div>

            {/* +7 DAYS */}
            <div style={{ background: '#1c1917', border: '1px solid #44403c', borderRadius: '6px', padding: '14px 16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                <span style={{ fontSize: '0.7rem', color: '#fdba74', fontWeight: 600 }}>+7 DAYS HORIZON</span>
                <span style={{ fontSize: '0.65rem', background: '#7c2d12', color: '#ffedd5', padding: '2px 6px', borderRadius: '4px' }}>Weekly</span>
              </div>
              <div className="font-mono" style={{ fontSize: '1.3rem', fontWeight: 700, color: '#fb923c' }}>
                {data.facility_projections.plus_7days_liters.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 })} L
              </div>
              <div style={{ fontSize: '0.72rem', color: '#f59e0b', marginTop: '4px', fontWeight: 500 }} className="font-mono">
                ₹{data.facility_projections.plus_7days_cost_inr.toFixed(2)} at risk
              </div>
              <div style={{ fontSize: '0.65rem', color: '#71717a', marginTop: '4px' }}>
                Persistent unattended leakage impact
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Two-Column Breakdown: Top 5 Highest-Waste Fixtures & Top Zones */}
      {data && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(480px, 1fr))', gap: '20px', marginBottom: '20px' }}>
          {/* Top 5 Highest-Waste Fixtures */}
          <div className="command-panel" style={{ padding: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <AlertTriangle size={15} color="#f43f5e" />
                <h2 style={{ fontSize: '0.78rem', fontWeight: 700, color: '#f4f4f5', letterSpacing: '0.04em', textTransform: 'uppercase', margin: 0 }}>
                  TOP 5 HIGHEST-WASTE FIXTURES
                </h2>
              </div>
              <span style={{ fontSize: '0.68rem', color: '#71717a' }} className="font-mono">
                Ranked by Liters
              </span>
            </div>

            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.75rem' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #27272a', color: '#71717a', textAlign: 'left' }}>
                    <th style={{ padding: '8px 10px', fontWeight: 600 }}>FIXTURE ID</th>
                    <th style={{ padding: '8px 10px', fontWeight: 600 }}>TYPE</th>
                    <th style={{ padding: '8px 10px', fontWeight: 600 }}>ZONE</th>
                    <th style={{ padding: '8px 10px', fontWeight: 600, textAlign: 'right' }}>WASTE (L)</th>
                    <th style={{ padding: '8px 10px', fontWeight: 600, textAlign: 'right' }}>COST IMPACT</th>
                  </tr>
                </thead>
                <tbody>
                  {data.top_waste_fixtures.map((fix, idx) => (
                    <tr
                      key={fix.fixture_id}
                      style={{
                        borderBottom: idx === data.top_waste_fixtures.length - 1 ? 'none' : '1px solid #1c1c1f',
                        background: idx === 0 ? 'rgba(244, 63, 94, 0.05)' : 'transparent',
                      }}
                    >
                      <td style={{ padding: '10px', fontWeight: 600, color: '#f4f4f5' }} className="font-mono">
                        {fix.fixture_id}
                        {idx === 0 && (
                          <span style={{ marginLeft: '6px', fontSize: '0.6rem', color: '#f43f5e', background: 'rgba(244, 63, 94, 0.15)', padding: '1px 5px', borderRadius: '3px' }}>
                            TOP
                          </span>
                        )}
                      </td>
                      <td style={{ padding: '10px', color: '#a1a1aa' }}>
                        {fix.fixture_type}
                      </td>
                      <td style={{ padding: '10px', color: '#d4d4d8' }}>
                        {fix.zone_name}
                      </td>
                      <td style={{ padding: '10px', textAlign: 'right', fontWeight: 700, color: '#f43f5e' }} className="font-mono">
                        {fix.waste_liters.toFixed(1)} L
                      </td>
                      <td style={{ padding: '10px', textAlign: 'right', fontWeight: 600, color: '#f59e0b' }} className="font-mono">
                        ₹{fix.cost_impact_inr.toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Top Water-Waste Zones */}
          <div className="command-panel" style={{ padding: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Building2 size={15} color="#38bdf8" />
                <h2 style={{ fontSize: '0.78rem', fontWeight: 700, color: '#f4f4f5', letterSpacing: '0.04em', textTransform: 'uppercase', margin: 0 }}>
                  WATER-WASTE BY FACILITY ZONE
                </h2>
              </div>
              <span style={{ fontSize: '0.68rem', color: '#71717a' }} className="font-mono">
                Facility Tiers
              </span>
            </div>

            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.75rem' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #27272a', color: '#71717a', textAlign: 'left' }}>
                    <th style={{ padding: '8px 10px', fontWeight: 600 }}>ZONE</th>
                    <th style={{ padding: '8px 10px', fontWeight: 600 }}>TIER</th>
                    <th style={{ padding: '8px 10px', fontWeight: 600, textAlign: 'center' }}>INCIDENTS</th>
                    <th style={{ padding: '8px 10px', fontWeight: 600, textAlign: 'right' }}>WASTE (L)</th>
                    <th style={{ padding: '8px 10px', fontWeight: 600, textAlign: 'right' }}>COST IMPACT</th>
                  </tr>
                </thead>
                <tbody>
                  {data.top_waste_zones.map((zone, idx) => (
                    <tr
                      key={zone.zone_id}
                      style={{
                        borderBottom: idx === data.top_waste_zones.length - 1 ? 'none' : '1px solid #1c1c1f',
                      }}
                    >
                      <td style={{ padding: '10px', fontWeight: 600, color: '#f4f4f5' }}>
                        {zone.zone_name}
                      </td>
                      <td style={{ padding: '10px' }}>
                        <span
                          style={{
                            fontSize: '0.65rem',
                            padding: '2px 6px',
                            borderRadius: '4px',
                            fontWeight: 600,
                            background: zone.criticality_tier === 'Tier 1' ? 'rgba(244, 63, 94, 0.15)' : 'rgba(56, 189, 248, 0.15)',
                            color: zone.criticality_tier === 'Tier 1' ? '#fb7185' : '#38bdf8',
                            border: zone.criticality_tier === 'Tier 1' ? '1px solid rgba(244, 63, 94, 0.3)' : '1px solid rgba(56, 189, 248, 0.3)',
                          }}
                        >
                          {zone.criticality_tier}
                        </span>
                      </td>
                      <td style={{ padding: '10px', textAlign: 'center', color: '#a1a1aa' }} className="font-mono">
                        {zone.incident_count}
                      </td>
                      <td style={{ padding: '10px', textAlign: 'right', fontWeight: 700, color: '#f43f5e' }} className="font-mono">
                        {zone.waste_liters.toFixed(1)} L
                      </td>
                      <td style={{ padding: '10px', textAlign: 'right', fontWeight: 600, color: '#f59e0b' }} className="font-mono">
                        ₹{zone.cost_impact_inr.toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Methodology & Estimation Grounding Banner */}
      {data && (
        <div
          style={{
            background: 'linear-gradient(180deg, #121214 0%, #0d0d10 100%)',
            border: '1px solid #27272a',
            borderRadius: '8px',
            padding: '16px 20px',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '14px',
          }}
        >
          <Info size={18} color="#38bdf8" style={{ flexShrink: 0, marginTop: '2px' }} />
          <div>
            <div style={{ fontSize: '0.78rem', fontWeight: 700, color: '#f4f4f5', letterSpacing: '0.03em', textTransform: 'uppercase' }}>
              SUSTAINABILITY ESTIMATION GROUNDING & METHODOLOGY
            </div>
            <div style={{ fontSize: '0.74rem', color: '#a1a1aa', marginTop: '4px', lineHeight: 1.5 }}>
              • <strong>Tariff Constant:</strong> Grounded in municipal commercial water tariff rate of <strong>₹0.15 / Litre</strong>.
              <br />
              • <strong>Incident Projection:</strong> Active incidents project forward water loss as <code>projected_loss = observed_flow_lpm × horizon_minutes</code> at +1hr, +6hr, +24hr, and +7days.
              <br />
              • <strong>Prevented Waste:</strong> For resolved tickets, <code>estimated_water_saved = potential_loss_without_intervention - actual_loss_before_resolution</code> using a <strong>6-hour unaddressed baseline reference horizon</strong>.
              <br />
              • <strong>Disclosure:</strong> {data.estimate_disclosure}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
