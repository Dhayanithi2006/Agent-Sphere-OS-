'use client';

import { useEffect, useState, useRef } from 'react';
import AppShell from '@/components/AppShell';

const API = 'http://localhost:8000';

interface Process {
  pid: string;
  agent: string;
  task_id: string;
  current_state: string;
  current_task: string;
  created_time: string;
  updated_time: string;
}

interface LiveItem {
  time: string;
  pid: string;
  agent: string;
  task: string;
  state: string;
}

const STATE = {
  running:   { color: '#22D3EE', label: 'Running' },
  completed: { color: '#34D399', label: 'Done'    },
  stopped:   { color: '#34D399', label: 'Done'    },
  failed:    { color: '#F87171', label: 'Failed'  },
  pending:   { color: '#FBBF24', label: 'Pending' },
  created:   { color: '#8B5CF6', label: 'Created' },
} as Record<string, { color: string; label: string }>;

function stateOf(s: string) {
  return STATE[s?.toLowerCase()] ?? { color: '#5C5880', label: s || '—' };
}

export default function DashboardPage() {
  const [supervisor, setSupervisor] = useState<any>({});
  const [processes, setProcesses] = useState<Process[]>([]);
  const [metrics, setMetrics] = useState<any>({});
  const [activityFeed, setActivityFeed] = useState<LiveItem[]>([]);
  const [taskHistory, setTaskHistory] = useState<any[]>([]);
  const seenPids = useRef(new Set<string>());
  const activityEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const [sv, ps, mx, tk] = await Promise.all([
          fetch(`${API}/supervisor`).then(r => r.json()),
          fetch(`${API}/processes`).then(r => r.json()),
          fetch(`${API}/api/metrics`).then(r => r.json()),
          fetch(`${API}/tasks`).then(r => r.json()).catch(() => []),
        ]);
        setSupervisor(sv || {});
        setMetrics(mx || {});
        setTaskHistory(Array.isArray(tk) ? tk.slice().reverse().slice(0, 30) : []);
        const procs: Process[] = Array.isArray(ps) ? ps : [];
        setProcesses(procs);

        const now = new Date().toLocaleTimeString('en-US', { hour12: false });
        const newItems: LiveItem[] = [];
        procs.forEach(p => {
          const key = `${p.pid}-${p.current_state}`;
          if (!seenPids.current.has(key)) {
            seenPids.current.add(key);
            newItems.push({ time: now, pid: p.pid, agent: p.agent || '—', task: p.current_task || '—', state: p.current_state || 'pending' });
          }
        });
        if (newItems.length > 0) {
          setActivityFeed(prev => [...newItems.reverse(), ...prev].slice(0, 100));
        }
      } catch {}
    };
    load();
    const t = setInterval(load, 2000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => { activityEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [activityFeed]);

  const running   = processes.filter(p => p.current_state === 'running').length;
  const completed = processes.filter(p => ['completed','stopped'].includes(p.current_state || '')).length;
  const failed    = processes.filter(p => p.current_state === 'failed').length;

  const kpis = [
    { label: 'Agents',     value: supervisor.agent_count ?? '—', accent: '#8B5CF6', cls: 'violet', sub: 'registered',   icon: '🤖' },
    { label: 'Total Tasks',value: supervisor.task_count  ?? '—', accent: '#F472B6', cls: 'rose',   sub: 'all time',     icon: '📋' },
    { label: 'Running',    value: running,                        accent: '#22D3EE', cls: 'cyan',   sub: 'active now',   icon: '▶', pulse: running > 0 },
    { label: 'Completed',  value: completed,                      accent: '#34D399', cls: 'emerald',sub: 'finished',     icon: '✔' },
    { label: 'Failed',     value: failed,                         accent: '#F87171', cls: 'red',    sub: 'need recovery',icon: '✖' },
    { label: 'API Spend',  value: metrics.total_cost != null ? `$${Number(metrics.total_cost).toFixed(3)}` : '$0.000', accent: '#FBBF24', cls: 'amber', sub: 'tokens used', icon: '💰' },
  ];

  return (
    <AppShell>
      <div style={{ padding: '28px 32px', display: 'flex', flexDirection: 'column', gap: 20 }}>

        {/* ── Page header ──────────────────────── */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1 className="page-title" style={{ marginBottom: 6 }}>
              <span className="gradient-text">Mission Control</span>
            </h1>
            <p style={{ color: 'var(--text-muted)', fontSize: 13, fontFamily: 'Sora, sans-serif' }}>
              Real-time system overview · auto-refreshing every 2s
            </p>
          </div>

          {/* Live indicator */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: 8,
            padding: '7px 16px',
            background: running > 0 ? 'rgba(34,211,238,0.08)' : 'rgba(52,211,153,0.06)',
            border: `1px solid ${running > 0 ? 'rgba(34,211,238,0.25)' : 'rgba(52,211,153,0.2)'}`,
            borderRadius: 100,
          }}>
            <span className={`status-dot ${running > 0 ? 'running' : 'completed'}`} />
            <span style={{
              fontSize: 11,
              fontFamily: 'JetBrains Mono, monospace',
              color: running > 0 ? '#22D3EE' : '#34D399',
              letterSpacing: '0.08em',
            }}>
              {running > 0 ? `${running} RUNNING` : 'IDLE'}
            </span>
          </div>
        </div>

        {/* ── KPI cards ────────────────────────── */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: 14 }}>
          {kpis.map(({ label, value, accent, sub, icon, pulse }) => (
            <div
              key={label}
              className={`metric-card ${pulse ? 'violet' : ''} fade-up`}
              style={{
                borderColor: pulse ? `rgba(34,211,238,0.25)` : undefined,
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
                <span style={{ fontSize: 9, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em', fontFamily: 'Outfit, sans-serif', fontWeight: 600 }}>
                  {label}
                </span>
                <span style={{ fontSize: 18, filter: pulse ? 'drop-shadow(0 0 6px ' + accent + ')' : 'none' }}>{icon}</span>
              </div>
              <div style={{
                fontSize: 30,
                fontFamily: 'Outfit, sans-serif',
                fontWeight: 800,
                color: accent,
                letterSpacing: '-0.03em',
                marginBottom: 4,
                textShadow: pulse ? `0 0 20px ${accent}66` : 'none',
              }}>
                {value}
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-subtle)', fontFamily: 'Sora, sans-serif' }}>{sub}</div>
            </div>
          ))}
        </div>

        {/* ── Running agent pills ───────────────── */}
        {running > 0 && (
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {processes.filter(p => p.current_state === 'running').map(p => (
              <div key={p.pid} style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '6px 14px',
                borderRadius: 100,
                background: 'rgba(34,211,238,0.08)',
                border: '1px solid rgba(34,211,238,0.22)',
              }}>
                <span className="status-dot running" />
                <span style={{ fontSize: 12, color: '#22D3EE', fontFamily: 'Outfit, sans-serif', fontWeight: 600 }}>{p.agent}</span>
                <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>·</span>
                <span style={{ fontSize: 11, color: 'var(--text-secondary)', maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.current_task}</span>
              </div>
            ))}
          </div>
        )}

        {/* ── 2-col layout ─────────────────────── */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: 16 }}>

          {/* Processes table */}
          <div className="glass-card" style={{ overflow: 'hidden' }}>
            <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border-soft)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontFamily: 'Outfit, sans-serif', fontWeight: 700, fontSize: 14, color: 'var(--text-primary)' }}>⚙ Processes</span>
              <span className="badge badge-violet">{processes.length} total</span>
            </div>

            {/* Table head */}
            <div style={{ display: 'grid', gridTemplateColumns: '100px 110px 1fr 90px', padding: '8px 20px', borderBottom: '1px solid rgba(255,255,255,0.04)', gap: 12 }}>
              {['PID', 'AGENT', 'TASK', 'STATUS'].map(h => (
                <span key={h} className="section-title" style={{ fontSize: 10 }}>{h}</span>
              ))}
            </div>

            <div style={{ maxHeight: 360, overflowY: 'auto' }}>
              {processes.slice(0, 50).map((p, i) => {
                const s = stateOf(p.current_state);
                return (
                  <div
                    key={p.pid || i}
                    style={{
                      display: 'grid', gridTemplateColumns: '100px 110px 1fr 90px',
                      padding: '10px 20px', borderBottom: '1px solid rgba(255,255,255,0.03)',
                      gap: 12, alignItems: 'center', transition: 'background 0.15s',
                    }}
                    onMouseEnter={e => (e.currentTarget.style.background = 'rgba(139,92,246,0.04)')}
                    onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                  >
                    <span style={{ fontSize: 11, fontFamily: 'JetBrains Mono, monospace', color: '#A78BFA' }}>{p.pid}</span>
                    <span style={{ fontSize: 12, color: 'var(--text-secondary)', fontFamily: 'Outfit, sans-serif' }}>{p.agent}</span>
                    <span style={{ fontSize: 11, color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontFamily: 'Sora, sans-serif' }}>{p.current_task || '—'}</span>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                      <span className={`status-dot ${p.current_state || 'idle'}`} />
                      <span style={{ fontSize: 10, fontFamily: 'JetBrains Mono, monospace', color: s.color, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{s.label}</span>
                    </div>
                  </div>
                );
              })}
              {processes.length === 0 && (
                <div style={{ padding: 48, textAlign: 'center', color: 'var(--text-subtle)', fontSize: 13, fontFamily: 'Sora, sans-serif' }}>
                  No processes yet
                </div>
              )}
            </div>
          </div>

          {/* Live activity feed */}
          <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden', maxHeight: 480 }}>
            <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--border-soft)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0 }}>
              <span style={{ fontFamily: 'Outfit, sans-serif', fontWeight: 700, fontSize: 14, color: 'var(--text-primary)' }}>⚡ Live Feed</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#34D399', boxShadow: '0 0 6px #34D399', display: 'inline-block', animation: 'pulse-cyan 2s infinite' }} />
                <span style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.08em' }}>LIVE</span>
              </div>
            </div>
            <div style={{ flex: 1, overflowY: 'auto', padding: '4px 0' }}>
              {activityFeed.length === 0 && (
                <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-subtle)', fontSize: 13, fontFamily: 'Sora, sans-serif' }}>
                  Waiting for activity...
                </div>
              )}
              {activityFeed.map((item, i) => {
                const s = stateOf(item.state);
                return (
                  <div key={i} className="feed-row" style={{ padding: '8px 16px', borderBottom: '1px solid rgba(255,255,255,0.03)', display: 'flex', flexDirection: 'column', gap: 3 }}>
                    <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                      <span style={{ fontSize: 9, color: 'var(--text-subtle)', fontFamily: 'JetBrains Mono, monospace' }}>{item.time}</span>
                      <span style={{ fontSize: 10, color: '#A78BFA', fontFamily: 'JetBrains Mono, monospace' }}>{item.pid}</span>
                      <span style={{ fontSize: 10, color: s.color, fontFamily: 'JetBrains Mono, monospace', textTransform: 'uppercase', fontWeight: 600 }}>{s.label}</span>
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      <span style={{ color: 'var(--text-muted)' }}>{item.agent}: </span>{item.task}
                    </div>
                  </div>
                );
              })}
              <div ref={activityEndRef} />
            </div>
          </div>
        </div>

        {/* ── Task history ──────────────────────── */}
        <div className="glass-card" style={{ overflow: 'hidden' }}>
          <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border-soft)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontFamily: 'Outfit, sans-serif', fontWeight: 700, fontSize: 14, color: 'var(--text-primary)' }}>🕐 Task History</span>
            <span className="badge badge-violet">{taskHistory.length} recent</span>
          </div>
          <div style={{ maxHeight: 240, overflowY: 'auto' }}>
            {taskHistory.length === 0 && (
              <div style={{ padding: 36, textAlign: 'center', color: 'var(--text-subtle)', fontSize: 13, fontFamily: 'Sora, sans-serif' }}>
                No tasks yet — run a workflow from Home
              </div>
            )}
            {taskHistory.map((t: any, i: number) => {
              const s = stateOf(t.status);
              return (
                <div
                  key={t.task_id || i}
                  style={{ display: 'grid', gridTemplateColumns: '10px 1fr auto 90px', padding: '10px 20px', borderBottom: '1px solid rgba(255,255,255,0.03)', gap: 14, alignItems: 'center', transition: 'background 0.15s' }}
                  onMouseEnter={e => (e.currentTarget.style.background = 'rgba(139,92,246,0.04)')}
                  onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                >
                  <div className={`status-dot ${t.status || 'idle'}`} />
                  <div>
                    <div style={{ fontSize: 13, color: 'var(--text-primary)', fontFamily: 'Outfit, sans-serif', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {t.name || t.task_id || 'Unknown task'}
                    </div>
                    <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2, fontFamily: 'Sora, sans-serif' }}>
                      Agent: {t.agent_id || '—'}
                    </div>
                  </div>
                  <span className={`badge badge-${t.status === 'completed' || t.status === 'stopped' ? 'emerald' : t.status === 'failed' ? 'red' : t.status === 'running' ? 'cyan' : 'amber'}`}>
                    {s.label}
                  </span>
                  <div style={{ fontSize: 10, color: 'var(--text-subtle)', textAlign: 'right', fontFamily: 'JetBrains Mono, monospace' }}>
                    {t.task_id ? `#${String(t.task_id).slice(-8)}` : '—'}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

      </div>
    </AppShell>
  );
}
