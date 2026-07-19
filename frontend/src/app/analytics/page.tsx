'use client';

import { useEffect, useState } from 'react';
import AppShell from '@/components/AppShell';
import { api } from '@/lib/api';

interface Metric {
  total_tasks?: number;
  completed_tasks?: number;
  failed_tasks?: number;
  success_rate?: number;
  total_cost?: number;
  avg_latency_ms?: number;
  provider_usage?: Record<string, number>;
  workflow_distribution?: Record<string, number>;
}

// ── Animated SVG Donut Chart ───────────────────────────────────────────────────
function DonutChart({ pct, color, label, value }: { pct: number; color: string; label: string; value: string }) {
  const r = 54;
  const circ = 2 * Math.PI * r;
  const dash = (pct / 100) * circ;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
      <div style={{ position: 'relative', width: 140, height: 140 }}>
        <svg width="140" height="140" viewBox="0 0 140 140" style={{ transform: 'rotate(-90deg)' }}>
          <circle cx="70" cy="70" r={r} fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="12" />
          <circle cx="70" cy="70" r={r} fill="none" stroke={color} strokeWidth="12"
            strokeDasharray={`${dash} ${circ}`} strokeLinecap="round"
            style={{ transition: 'stroke-dasharray 1s ease', filter: `drop-shadow(0 0 6px ${color}80)` }}
          />
        </svg>
        <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ fontSize: 26, fontFamily: 'Space Grotesk', fontWeight: 700, color }}>{value}</div>
          <div style={{ fontSize: 10, color: '#4A5280', textTransform: 'uppercase', letterSpacing: '0.08em' }}>{label}</div>
        </div>
      </div>
    </div>
  );
}

// ── Horizontal Bar Chart ───────────────────────────────────────────────────────
function BarChart({ data, color }: { data: { label: string; value: number }[]; color: string }) {
  const max = Math.max(...data.map((d) => d.value), 1);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {data.map(({ label, value }) => (
        <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ width: 110, fontSize: 12, color: '#8892B0', textAlign: 'right', flexShrink: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{label}</div>
          <div style={{ flex: 1, height: 8, borderRadius: 4, background: 'rgba(255,255,255,0.05)', overflow: 'hidden' }}>
            <div style={{
              height: '100%', width: `${(value / max) * 100}%`,
              background: `linear-gradient(90deg, ${color}, ${color}80)`,
              borderRadius: 4, transition: 'width 0.8s ease',
              boxShadow: `0 0 6px ${color}60`,
            }} />
          </div>
          <div style={{ width: 32, fontSize: 12, color: '#4A5280', fontFamily: 'JetBrains Mono, monospace', textAlign: 'right' }}>{value}</div>
        </div>
      ))}
      {data.length === 0 && <div style={{ color: '#4A5280', fontSize: 13, padding: '16px 0', textAlign: 'center' }}>No data yet</div>}
    </div>
  );
}

// ── KPI Card ──────────────────────────────────────────────────────────────────
function KpiCard({ label, value, sub, color }: { label: string; value: string | number; sub: string; color: string }) {
  return (
    <div style={{ borderRadius: 16, padding: '20px 24px', border: `1px solid ${color}18`, background: `${color}06`, transition: 'all 0.2s' }}
      onMouseEnter={e => { (e.currentTarget as HTMLElement).style.borderColor = `${color}35`; (e.currentTarget as HTMLElement).style.transform = 'translateY(-2px)'; }}
      onMouseLeave={e => { (e.currentTarget as HTMLElement).style.borderColor = `${color}18`; (e.currentTarget as HTMLElement).style.transform = 'none'; }}
    >
      <div style={{ fontSize: 10, color: '#4A5280', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 8 }}>{label}</div>
      <div style={{ fontSize: 32, fontFamily: 'Space Grotesk, sans-serif', fontWeight: 700, color, marginBottom: 4 }}>{value}</div>
      <div style={{ fontSize: 12, color: '#4A5280' }}>{sub}</div>
    </div>
  );
}

// ── System Health tile ─────────────────────────────────────────────────────────
function HealthTile({ label, status, color }: { label: string; status: string; color: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 14px', background: 'rgba(255,255,255,0.02)', borderRadius: 10, border: '1px solid rgba(255,255,255,0.05)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ width: 6, height: 6, borderRadius: '50%', background: color, boxShadow: `0 0 5px ${color}`, display: 'inline-block' }} />
        <span style={{ fontSize: 12, color: '#8892B0' }}>{label}</span>
      </div>
      <span style={{ fontSize: 10, color, fontFamily: 'JetBrains Mono, monospace', fontWeight: 600 }}>{status}</span>
    </div>
  );
}

export default function AnalyticsPage() {
  const [metrics, setMetrics] = useState<Metric>({});
  const [supervisor, setSupervisor] = useState<any>({});
  const [taskHistory, setTaskHistory] = useState<any[]>([]);

  useEffect(() => {
    const load = async () => {
      try {
        const [m, sv, tk] = await Promise.all([
          api.getMetrics(),
          api.getSupervisor(),
          fetch('http://localhost:8000/tasks').then(r => r.json()).catch(() => []),
        ]);
        setMetrics(m || {});
        setSupervisor(sv || {});
        setTaskHistory(Array.isArray(tk) ? tk : []);
      } catch {}
    };
    load();
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, []);

  const providerData = Object.entries(metrics.provider_usage || {}).map(([label, value]) => ({ label, value: value as number }));
  const workflowData = Object.entries(metrics.workflow_distribution || {}).map(([label, value]) => ({ label, value: value as number }));

  const total = metrics.total_tasks ?? supervisor.task_count ?? 0;
  const completed = metrics.completed_tasks ?? 0;
  const failed = metrics.failed_tasks ?? 0;
  const successPct = total > 0 ? Math.round((completed / total) * 100) : 0;
  const failPct = total > 0 ? Math.round((failed / total) * 100) : 0;

  // Agent leaderboard from task history
  const agentCounts: Record<string, { total: number; completed: number }> = {};
  taskHistory.forEach((t: any) => {
    const ag = t.agent_id || 'unknown';
    if (!agentCounts[ag]) agentCounts[ag] = { total: 0, completed: 0 };
    agentCounts[ag].total++;
    if ((t.status || '').toLowerCase() === 'completed') agentCounts[ag].completed++;
  });
  const leaderboard = Object.entries(agentCounts)
    .map(([name, stats]) => ({ name, ...stats }))
    .sort((a, b) => b.total - a.total)
    .slice(0, 8);

  return (
    <AppShell>
      <div style={{ padding: '28px 32px' }}>
        {/* Header */}
        <div style={{ marginBottom: 28 }}>
          <h1 style={{ fontFamily: 'Space Grotesk, sans-serif', fontSize: 28, fontWeight: 700, color: '#F0F4FF', marginBottom: 6 }}>
            Analytics
          </h1>
          <p style={{ color: '#4A5280', fontSize: 14 }}>System-wide performance metrics · live data</p>
        </div>

        {/* KPIs */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 14, marginBottom: 28 }}>
          <KpiCard label="Total Tasks"  value={total || '—'}                                                             sub="all time"          color="#00D4FF" />
          <KpiCard label="Completed"    value={completed || '—'}                                                         sub="successful"        color="#00FF9D" />
          <KpiCard label="Failed"       value={failed || '—'}                                                            sub="need recovery"     color="#FF3D71" />
          <KpiCard label="Success Rate" value={successPct ? `${successPct}%` : '—'}                                     sub="kernel executions" color="#FFB800" />
          <KpiCard label="Total Cost"   value={metrics.total_cost != null ? `$${Number(metrics.total_cost).toFixed(4)}` : '$0.0000'} sub="API spend" color="#7B2FFF" />
          <KpiCard label="Avg Latency"  value={metrics.avg_latency_ms != null ? `${Math.round(Number(metrics.avg_latency_ms))}ms` : '—'} sub="per execution" color="#00D4FF" />
        </div>

        {/* Donut charts row */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 24 }}>
          <div style={{ borderRadius: 16, padding: '24px', border: '1px solid rgba(255,255,255,0.07)', background: 'rgba(255,255,255,0.01)', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: '#F0F4FF', alignSelf: 'flex-start' }}>✅ Success Rate</div>
            <DonutChart pct={successPct} color="#00FF9D" label="success" value={successPct ? `${successPct}%` : '0%'} />
            <div style={{ fontSize: 12, color: '#4A5280' }}>{completed} of {total} tasks succeeded</div>
          </div>

          <div style={{ borderRadius: 16, padding: '24px', border: '1px solid rgba(255,255,255,0.07)', background: 'rgba(255,255,255,0.01)', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: '#F0F4FF', alignSelf: 'flex-start' }}>❌ Failure Rate</div>
            <DonutChart pct={failPct} color="#FF3D71" label="failed" value={failPct ? `${failPct}%` : '0%'} />
            <div style={{ fontSize: 12, color: '#4A5280' }}>{failed} tasks required recovery</div>
          </div>

          <div style={{ borderRadius: 16, padding: '24px', border: '1px solid rgba(255,255,255,0.07)', background: 'rgba(255,255,255,0.01)', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: '#F0F4FF', alignSelf: 'flex-start' }}>🤖 Agent Coverage</div>
            <DonutChart pct={leaderboard.length > 0 ? Math.min(100, leaderboard.length * 5) : 0} color="#7B2FFF" label="agents" value={String(leaderboard.length)} />
            <div style={{ fontSize: 12, color: '#4A5280' }}>{leaderboard.length} agents used in tasks</div>
          </div>
        </div>

        {/* Charts + Leaderboard row */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16, marginBottom: 24 }}>
          <div style={{ borderRadius: 16, padding: '24px', border: '1px solid rgba(255,255,255,0.07)', background: 'rgba(255,255,255,0.01)' }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#F0F4FF', marginBottom: 20 }}>LLM Provider Usage</div>
            <BarChart data={providerData} color="#7B2FFF" />
          </div>

          <div style={{ borderRadius: 16, padding: '24px', border: '1px solid rgba(255,255,255,0.07)', background: 'rgba(255,255,255,0.01)' }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#F0F4FF', marginBottom: 20 }}>Workflow Distribution</div>
            <BarChart data={workflowData} color="#00D4FF" />
          </div>

          {/* Agent Leaderboard */}
          <div style={{ borderRadius: 16, padding: '24px', border: '1px solid rgba(255,255,255,0.07)', background: 'rgba(255,255,255,0.01)' }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#F0F4FF', marginBottom: 16 }}>🏆 Agent Leaderboard</div>
            {leaderboard.length === 0 ? (
              <div style={{ color: '#4A5280', fontSize: 13, textAlign: 'center', padding: '20px 0' }}>Run some tasks to see rankings</div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {leaderboard.map((ag, i) => (
                  <div key={ag.name} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <span style={{ fontSize: 11, color: i < 3 ? '#FFB800' : '#4A5280', fontFamily: 'JetBrains Mono', width: 18, textAlign: 'center' }}>
                      {i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : `${i + 1}.`}
                    </span>
                    <div style={{ flex: 1, overflow: 'hidden' }}>
                      <div style={{ fontSize: 11, color: '#F0F4FF', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{ag.name}</div>
                      <div style={{ fontSize: 9, color: '#4A5280' }}>{ag.completed}/{ag.total} completed</div>
                    </div>
                    <span style={{ fontSize: 11, fontFamily: 'JetBrains Mono', color: '#00D4FF', fontWeight: 700 }}>{ag.total}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* System Health */}
        <div style={{ borderRadius: 16, padding: '24px', border: '1px solid rgba(255,255,255,0.07)', background: 'rgba(255,255,255,0.01)' }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: '#F0F4FF', marginBottom: 16 }}>System Health</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 10 }}>
            {[
              { label: 'Kernel',            status: 'OPERATIONAL', color: '#00FF9D' },
              { label: 'Supervisor',        status: 'OPERATIONAL', color: '#00FF9D' },
              { label: 'Scheduler',         status: 'OPERATIONAL', color: '#00FF9D' },
              { label: 'Execution Engine',  status: 'OPERATIONAL', color: '#00FF9D' },
              { label: 'Memory Manager',    status: 'OPERATIONAL', color: '#00FF9D' },
              { label: 'Recovery Engine',   status: 'OPERATIONAL', color: '#00FF9D' },
              { label: 'Checkpoint Mgr',    status: 'OPERATIONAL', color: '#00FF9D' },
              { label: 'Model Router',      status: 'OPERATIONAL', color: '#00FF9D' },
              { label: 'Event Bus',         status: 'OPERATIONAL', color: '#00FF9D' },
              { label: 'Plugin Manager',    status: 'OPERATIONAL', color: '#00FF9D' },
              { label: 'API Budget',        status: supervisor.task_count > 0 ? 'ACTIVE' : 'IDLE', color: supervisor.task_count > 0 ? '#00D4FF' : '#4A5280' },
              { label: 'Process Manager',   status: `${supervisor.process_count ?? 0} TRACKED`, color: '#FFB800' },
            ].map(({ label, status, color }) => (
              <HealthTile key={label} label={label} status={status} color={color} />
            ))}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
