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

const STATE_COLOR: Record<string, string> = {
  running: '#00D4FF', stopped: '#00FF9D', completed: '#00FF9D',
  failed: '#FF3D71', created: '#7B2FFF', pending: '#FFB800',
};

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

        // Build live feed from new/changed processes
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

  const running = processes.filter(p => p.current_state === 'running').length;
  const completed = processes.filter(p => ['completed', 'stopped'].includes(p.current_state || '')).length;
  const failed = processes.filter(p => p.current_state === 'failed').length;

  const kpis = [
    { label: 'Agents',     value: supervisor.agent_count ?? '—', color: '#00D4FF', sub: 'registered' },
    { label: 'Total Tasks',value: supervisor.task_count   ?? '—', color: '#7B2FFF', sub: 'all time' },
    { label: 'Running',    value: running,                        color: '#00D4FF', sub: 'active now', pulse: running > 0 },
    { label: 'Completed',  value: completed,                      color: '#00FF9D', sub: 'finished' },
    { label: 'Failed',     value: failed,                         color: '#FF3D71', sub: 'need recovery' },
    { label: 'Cost',       value: metrics.total_cost != null ? `$${Number(metrics.total_cost).toFixed(3)}` : '$0.000', color: '#FFB800', sub: 'API spend' },
  ];

  return (
    <AppShell>
      <div style={{ padding: '24px 28px', display: 'flex', flexDirection: 'column', gap: 16 }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1 style={{ fontFamily: 'Space Grotesk, sans-serif', fontSize: 26, fontWeight: 700, color: '#F0F4FF', margin: 0, marginBottom: 4 }}>Mission Control</h1>
            <p style={{ color: '#4A5280', fontSize: 13, margin: 0 }}>Real-time system overview · auto-refreshing every 2s</p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 14px', background: running > 0 ? 'rgba(0,212,255,0.08)' : 'rgba(255,255,255,0.03)', border: `1px solid ${running > 0 ? 'rgba(0,212,255,0.2)' : 'rgba(255,255,255,0.07)'}`, borderRadius: 100 }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: running > 0 ? '#00D4FF' : '#00FF9D', boxShadow: running > 0 ? '0 0 6px #00D4FF' : 'none', display: 'inline-block' }} />
            <span style={{ fontSize: 11, color: running > 0 ? '#00D4FF' : '#4A5280', fontFamily: 'JetBrains Mono' }}>
              {running > 0 ? `${running} RUNNING` : 'IDLE'}
            </span>
          </div>
        </div>

        {/* KPIs */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: 12 }}>
          {kpis.map(({ label, value, color, sub, pulse }) => (
            <div key={label} style={{ borderRadius: 14, padding: '16px 18px', border: `1px solid ${pulse ? `${color}25` : 'rgba(255,255,255,0.07)'}`, background: pulse ? `${color}06` : 'rgba(255,255,255,0.02)', transition: 'all 0.3s' }}>
              <div style={{ fontSize: 10, color: '#4A5280', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 6 }}>{label}</div>
              <div style={{ fontSize: 26, fontFamily: 'Space Grotesk', fontWeight: 700, color, marginBottom: 2 }}>{value}</div>
              <div style={{ fontSize: 10, color: '#4A5280' }}>{sub}</div>
            </div>
          ))}
        </div>

        {/* Main 2-column layout */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: 16 }}>

          {/* Left: Live processes */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>

            {/* Running agents highlight */}
            {running > 0 && (
              <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                {processes.filter(p => p.current_state === 'running').map(p => (
                  <div key={p.pid} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 14px', borderRadius: 100, background: 'rgba(0,212,255,0.08)', border: '1px solid rgba(0,212,255,0.25)' }}>
                    <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#00D4FF', boxShadow: '0 0 6px #00D4FF', display: 'inline-block' }} />
                    <span style={{ fontSize: 12, color: '#00D4FF', fontFamily: 'JetBrains Mono' }}>{p.agent}</span>
                    <span style={{ fontSize: 11, color: '#4A5280' }}>·</span>
                    <span style={{ fontSize: 11, color: '#8892B0', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.current_task}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Process table */}
            <div style={{ borderRadius: 14, border: '1px solid rgba(255,255,255,0.07)', background: 'rgba(255,255,255,0.01)', overflow: 'hidden' }}>
              <div style={{ padding: '12px 18px', borderBottom: '1px solid rgba(255,255,255,0.06)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: 13, fontWeight: 600, color: '#F0F4FF' }}>Processes</span>
                <span style={{ fontSize: 11, color: '#4A5280' }}>{processes.length} total</span>
              </div>

              {/* Table header */}
              <div style={{ display: 'grid', gridTemplateColumns: '90px 110px 1fr 90px', padding: '8px 18px', borderBottom: '1px solid rgba(255,255,255,0.05)', gap: 12 }}>
                {['PID', 'AGENT', 'TASK', 'STATUS'].map(h => (
                  <span key={h} style={{ fontSize: 9, color: '#2A3060', textTransform: 'uppercase', letterSpacing: '0.12em', fontWeight: 600 }}>{h}</span>
                ))}
              </div>

              <div style={{ maxHeight: 340, overflowY: 'auto' }}>
                {processes.slice(0, 50).map((p, i) => {
                  const state = (p.current_state || 'pending').toLowerCase();
                  const color = STATE_COLOR[state] || '#4A5280';
                  return (
                    <div key={p.pid || i} style={{ display: 'grid', gridTemplateColumns: '90px 110px 1fr 90px', padding: '9px 18px', borderBottom: '1px solid rgba(255,255,255,0.03)', gap: 12, alignItems: 'center', transition: 'background 0.1s' }}
                      onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.02)') }
                      onMouseLeave={e => (e.currentTarget.style.background = 'transparent') }>
                      <span style={{ fontSize: 11, fontFamily: 'JetBrains Mono', color: '#00D4FF' }}>{p.pid}</span>
                      <span style={{ fontSize: 12, color: '#8892B0' }}>{p.agent}</span>
                      <span style={{ fontSize: 11, color: '#F0F4FF', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.current_task || '—'}</span>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                        {state === 'running' && <span style={{ width: 5, height: 5, borderRadius: '50%', background: color, boxShadow: `0 0 4px ${color}`, display: 'inline-block' }} />}
                        <span style={{ fontSize: 10, fontFamily: 'JetBrains Mono', color, textTransform: 'uppercase' }}>
                          {state === 'stopped' ? 'done' : state}
                        </span>
                      </div>
                    </div>
                  );
                })}
                {processes.length === 0 && (
                  <div style={{ padding: 40, textAlign: 'center', color: '#4A5280', fontSize: 13 }}>No processes yet</div>
                )}
              </div>
            </div>
          </div>

          {/* Right: Live activity feed */}
          <div style={{ borderRadius: 14, border: '1px solid rgba(255,255,255,0.07)', background: 'rgba(255,255,255,0.01)', display: 'flex', flexDirection: 'column', overflow: 'hidden', maxHeight: 480 }}>
            <div style={{ padding: '12px 16px', borderBottom: '1px solid rgba(255,255,255,0.06)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0 }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: '#F0F4FF' }}>Live Activity</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ width: 5, height: 5, borderRadius: '50%', background: '#00FF9D', boxShadow: '0 0 5px #00FF9D', display: 'inline-block' }} />
                <span style={{ fontSize: 10, color: '#4A5280', fontFamily: 'JetBrains Mono' }}>LIVE</span>
              </div>
            </div>

            <div style={{ flex: 1, overflowY: 'auto', padding: '4px 0' }}>
              {activityFeed.length === 0 && (
                <div style={{ padding: 40, textAlign: 'center', color: '#4A5280', fontSize: 13 }}>Waiting for activity...</div>
              )}
              {activityFeed.map((item, i) => {
                const color = STATE_COLOR[item.state] || '#4A5280';
                return (
                  <div key={i} style={{ padding: '7px 14px', borderBottom: '1px solid rgba(255,255,255,0.03)', display: 'flex', flexDirection: 'column', gap: 2 }}>
                    <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                      <span style={{ fontSize: 9, color: '#2A3060', fontFamily: 'JetBrains Mono', flexShrink: 0 }}>{item.time}</span>
                      <span style={{ fontSize: 10, color: '#00D4FF', fontFamily: 'JetBrains Mono', flexShrink: 0 }}>{item.pid}</span>
                      <span style={{ fontSize: 10, color, fontFamily: 'JetBrains Mono', textTransform: 'uppercase', flexShrink: 0 }}>
                        {item.state === 'stopped' ? 'DONE' : item.state.toUpperCase()}
                      </span>
                    </div>
                    <div style={{ fontSize: 11, color: '#8892B0', paddingLeft: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      <span style={{ color: '#4A5280' }}>{item.agent}: </span>{item.task}
                    </div>
                  </div>
                );
              })}
              <div ref={activityEndRef} />
            </div>
          </div>
        </div>

        {/* Task History Timeline */}
        <div style={{ borderRadius: 14, border: '1px solid rgba(255,255,255,0.07)', background: 'rgba(255,255,255,0.01)', overflow: 'hidden' }}>
          <div style={{ padding: '12px 18px', borderBottom: '1px solid rgba(255,255,255,0.06)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: '#F0F4FF' }}>🕐 Task History</span>
            <span style={{ fontSize: 11, color: '#4A5280' }}>{taskHistory.length} recent tasks</span>
          </div>
          <div style={{ maxHeight: 220, overflowY: 'auto' }}>
            {taskHistory.length === 0 && (
              <div style={{ padding: 30, textAlign: 'center', color: '#4A5280', fontSize: 13 }}>No tasks yet — run a build from Home</div>
            )}
            {taskHistory.map((t: any, i: number) => {
              const status = (t.status || '').toLowerCase();
              const statusColor = status === 'completed' ? '#00FF9D' : status === 'failed' ? '#FF3D71' : status === 'running' ? '#00D4FF' : '#FFB800';
              return (
                <div key={t.task_id || i} style={{
                  display: 'grid', gridTemplateColumns: '12px 1fr auto 80px',
                  padding: '9px 18px', borderBottom: '1px solid rgba(255,255,255,0.03)',
                  gap: 12, alignItems: 'center',
                }}
                  onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.02)')}
                  onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                >
                  <div style={{ width: 8, height: 8, borderRadius: '50%', background: statusColor, boxShadow: `0 0 5px ${statusColor}`, flexShrink: 0 }} />
                  <div>
                    <div style={{ fontSize: 12, color: '#F0F4FF', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {t.name || t.task_id || 'Unknown task'}
                    </div>
                    <div style={{ fontSize: 10, color: '#4A5280', marginTop: 1 }}>
                      Agent: {t.agent_id || '—'}
                    </div>
                  </div>
                  <div style={{ fontSize: 10, fontFamily: 'JetBrains Mono', color: statusColor, textTransform: 'uppercase', fontWeight: 700 }}>
                    {status === 'stopped' ? 'DONE' : status || 'QUEUED'}
                  </div>
                  <div style={{ fontSize: 10, color: '#4A5280', textAlign: 'right', fontFamily: 'JetBrains Mono' }}>
                    {t.task_id ? `#${String(t.task_id).slice(-6)}` : '—'}
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
