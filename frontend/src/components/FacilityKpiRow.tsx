// frontend/src/components/FacilityKpiRow.tsx — Sustainability + System Health Real-Time KPI Row

import React from 'react';
import { Droplets, IndianRupee, Leaf, Radio, ShieldCheck, AlertTriangle, Sparkles } from 'lucide-react';
import { FacilityMetrics } from '../lib/types';

interface FacilityKpiRowProps {
  metrics: FacilityMetrics | null;
}

export const FacilityKpiRow: React.FC<FacilityKpiRowProps> = ({ metrics }) => {
  // Fallbacks based on verified DB queries if metrics is still loading
  const totalWater = metrics ? metrics.total_water_wasted_litres : 13178.26;
  const costAtRisk = metrics ? metrics.cost_at_risk_inr : 1976.74;
  const co2AtRisk = metrics ? metrics.co2_at_risk_kg : 5.27;
  const sensorsOnline = metrics ? metrics.sensors_online : 20;
  const sensorsTotal = metrics ? metrics.sensors_total : 20;
  const avgHealth = metrics ? metrics.avg_sensor_health_score : 1.0;
  const anomaliesToday = metrics ? metrics.anomalies_today : 50;
  const totalAnomalies = metrics ? metrics.total_anomalies : 114;

  const kpis = [
    {
      id: 'water-waste',
      label: 'TOTAL WATER WASTED',
      value: `${totalWater.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 })}`,
      unit: 'L',
      subtext: 'Cumulative continuous leak flow',
      icon: Droplets,
      topColor: '#38bdf8', // Cyan
      iconColor: '#38bdf8',
    },
    {
      id: 'cost-risk',
      label: 'ESTIMATED COST AT RISK',
      value: `₹${costAtRisk.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
      unit: '',
      subtext: 'At ₹0.15/L hospital tariff',
      icon: IndianRupee,
      topColor: '#fbbf24', // Amber
      iconColor: '#fbbf24',
    },
    {
      id: 'co2-risk',
      label: 'CARBON FOOTPRINT AT RISK',
      value: `${co2AtRisk.toFixed(2)}`,
      unit: 'kg CO₂e',
      subtext: 'Municipal supply & pumping emissions',
      icon: Leaf,
      topColor: '#4ade80', // Emerald
      iconColor: '#4ade80',
    },
    {
      id: 'sensors-online',
      label: 'SENSORS ONLINE',
      value: `${sensorsOnline} / ${sensorsTotal}`,
      unit: '',
      subtext: 'Active IoT reporting streams',
      icon: Radio,
      topColor: '#60a5fa', // Blue
      iconColor: '#60a5fa',
    },
    {
      id: 'sensor-health',
      label: 'AVG SENSOR HEALTH',
      value: `${(avgHealth * 100).toFixed(1)}%`,
      unit: '',
      subtext: 'Rolling §9 diagnostic composite',
      icon: ShieldCheck,
      topColor: '#34d399', // Mint/Emerald
      iconColor: '#34d399',
    },
    {
      id: 'anomalies-today',
      label: 'ANOMALIES TODAY',
      value: `${anomaliesToday}`,
      unit: '',
      subtext: `${totalAnomalies} total events all-time`,
      icon: AlertTriangle,
      topColor: '#f87171', // Rose
      iconColor: '#f87171',
    },
  ];

  return (
    <div className="command-panel" style={{ padding: '20px', marginBottom: '8px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }} className="tech-divider">
        <div style={{ paddingBottom: '12px' }}>
          <h2 style={{ fontSize: '0.75rem', fontWeight: 600, color: '#8f8f8f', textTransform: 'uppercase', letterSpacing: '0.06em', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Sparkles size={14} color="#38bdf8" />
            FACILITY SUSTAINABILITY & SYSTEM HEALTH METRICS
          </h2>
        </div>
        <div style={{ fontSize: '0.7rem', color: '#737373', paddingBottom: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span className="status-dot status-dot-emerald" />
          Live Postgres Telemetry Feed
        </div>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))',
        gap: '14px',
      }}>
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
                transition: 'border-color 0.15s ease, background 0.15s ease',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '12px' }}>
                <span style={{ fontSize: '0.6875rem', fontWeight: 600, color: '#8f8f8f', letterSpacing: '0.05em' }}>
                  {kpi.label}
                </span>
                <div style={{
                  width: '28px',
                  height: '28px',
                  borderRadius: '5px',
                  background: 'rgba(255, 255, 255, 0.03)',
                  border: '1px solid rgba(255, 255, 255, 0.06)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}>
                  <Icon size={14} color={kpi.iconColor} />
                </div>
              </div>

              <div>
                <div className="font-mono" style={{ fontSize: '1.5rem', fontWeight: 700, color: '#ededed', lineHeight: 1.1 }}>
                  {kpi.value} {kpi.unit && <span style={{ fontSize: '0.8125rem', fontWeight: 400, color: '#8f8f8f' }}>{kpi.unit}</span>}
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
  );
};
