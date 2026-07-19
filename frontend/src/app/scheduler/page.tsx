'use client';

import { useEffect, useState, useRef } from 'react';
import AppShell from '@/components/AppShell';

const API = 'http://localhost:8000';

interface ProcessorTask {
  pid: string;
  task_id: string;
  agent_id: string;
  agent_label: string;
  task: string;
  state: string;
  started: string;
  updated: string;
}

interface ProcessorStatus {
  summary: {
    total: number;
    running: number;
    queued: number;
    completed: number;
    failed: number;
    scheduler_queue_depth: number;
    scheduler_active: number;
    concurrency_limit: number;
  };
  running: ProcessorTask[];
  queued: ProcessorTask[];
  recent_completed: ProcessorTask[];
  recent_failed: ProcessorTask[];
}

function dur(started: string, updated: string): string {
  try {
    const ms = new Date(updated).getTime() - new Date(started).getTime();
    if (ms < 0) return '—';
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
  } catch { return '—'; }
}

function ago(ts: string): string {
  try {
    const ms = Date.now() - new Date(ts).getTime();
    if (ms < 1000) return 'just now';
    if (ms < 60000) return `${Math.floor(ms / 1000)}s ago`;
    if (ms < 3600000) return `${Math.floor(ms / 60000)}m ago`;
    return `${Math.floor(ms / 3600000)}h ago`;
  } catch { return '—'; }
}

// Animated running task card
function RunningCard({ task, index }: { task: ProcessorTask; index: number }) {
  const [dots, setDots] = useState('');
  useEffect(() => {
    const t = setInterval(() => setDots(d => d.length >= 3 ? '' : d + '.'), 500);
    return () => clearInterval(t);
  }, []);

  return (
    <div style={{
      borderRadius: 14, padding: '16px 20px',
      background: 'rgba(0,212,255,0.04)',
      border: '1px solid rgba(0,212,255,0.2)',
      boxShadow: '0 0 20px rgba(0,212,255,0.04)',
      animation: `fadeIn 0.3s ease ${index * 0.05}s both`,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#00D4FF', boxShadow: '0 0 8px #00D4FF', display: 'inline-block' }} />
          <span style={{ fontSize: 13, fontWeight: 600, color: '#00D4FF' }}>{task.agent_label}</span>
        </div>
        <span style={{ fontSize: 10, color: '#4A5280', fontFamily: 'JetBrains Mono' }}>{task.pid}</span>
      </div>

      <div style={{ fontSize: 12, color: '#F0F4FF', marginBottom: 8, lineHeight: 1.5 }}>
        {task.task}<span style={{ color: '#00D4FF' }}>{dots}</span>
      </div>

      <div style={{ display: 'flex', gap: 16 }}>
        <span style={{ fontSize: 10, color: '#4A5280' }}>Running for {dur(task.started, new Date().toISOString())}</span>
        <span style={{ fontSize: 10, color: '#4A5280' }}>Started {ago(task.started)}</span>
      </div>

      {/* Progress pulse bar */}
      <div style={{ marginTop: 10, height: 2, background: 'rgba(255,255,255,0.05)', borderRadius: 1, overflow: 'hidden' }}>
        <div style={{ height: '100%', background: 'linear-gradient(90deg, transparent, #00D4FF, transparent)', animation: 'scan 2s ease-in-out infinite', width: '40%' }} />
      </div>
    </div>
  );
}

// Compact task row
function TaskRow({ task, color }: { task: ProcessorTask; color: string }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '90px 140px 1fr 70px', gap: 12, padding: '9px 16px', borderBottom: '1px solid rgba(255,255,255,0.03)', alignItems: 'center' }}>
      <span style={{ fontFamily: 'JetBrains Mono', fontSize: 10, color: '#4A5280' }}>{task.pid}</span>
      <span style={{ fontSize: 11, color }}>
        {task.agent_label}
      </span>
      <span style={{ fontSize: 11, color: '#8892B0', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{task.task}</span>
      <span style={{ fontSize: 10, color: '#4A5280', fontFamily: 'JetBrains Mono', textAlign: 'right' }}>{ago(task.updated)}</span>
    </div>
  );
}

export default function ProcessorPage() {
  const [status, setStatus] = useState<ProcessorStatus | null>(null);
  const [history, setHistory] = useState<string[]>([]);
  const prevRunning = useRef(0);

  useEffect(() => {
    const load = async () => {
      try {
        const r = await fetch(`${API}/api/processor/status`);
        const data: ProcessorStatus = await r.json();
        setStatus(data);

        // Build history log
        const now = new Date().toLocaleTimeString('en-US', { hour12: false });
        const cur = data.summary.running;
        if (cur !== prevRunning.current) {
          if (cur > prevRunning.current) {
            setHistory(h => [`${now}  +${cur - prevRunning.current} task(s) started — ${cur} running`, ...h].slice(0, 50));
          } else {
            setHistory(h => [`${now}  ${prevRunning.current - cur} task(s) finished — ${cur} running`, ...h].slice(0, 50));
          }
          prevRunning.current = cur;
        }
      } catch {}
    };
    load();
    const t = setInterval(load, 1500);
    return () => clearInterval(t);
  }, []);

  const s = status?.summary;

  return (
    <AppShell>
      <style>{`
        @keyframes fadeIn { from { opacity:0; transform: translateY(6px); } to { opacity:1; transform:none; } }
        @keyframes scan { 0% { transform: translateX(-100%); } 100% { transform: translateX(350%); } }
      `}</style>

      <div style={{ padding: '24px 28px', display: 'flex', flexDirection: 'column', gap: 16 }}>

        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1 style={{ fontFamily: 'Space Grotesk, sans-serif', fontSize: 26, fontWeight: 700, color: '#F0F4FF', margin: 0, marginBottom: 4 }}>
              Background Processor
            </h1>
            <p style={{ color: '#4A5280', fontSize: 13, margin: 0 }}>
              Real-time view of every agent task — queued, running, completed, failed
            </p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 14px', background: (s?.running ?? 0) > 0 ? 'rgba(0,212,255,0.08)' : 'rgba(255,255,255,0.03)', border: '1px solid rgba(0,212,255,0.15)', borderRadius: 100 }}>
            {(s?.running ?? 0) > 0 && <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#00D4FF', boxShadow: '0 0 6px #00D4FF', display: 'inline-block' }} />}
            <span style={{ fontSize: 11, fontFamily: 'JetBrains Mono', color: (s?.running ?? 0) > 0 ? '#00D4FF' : '#4A5280' }}>
              {(s?.running ?? 0) > 0 ? `${s?.running} EXECUTING` : 'IDLE'}
            </span>
          </div>
        </div>

        {/* Scheduler stats */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12 }}>
          {[
            { label: 'Queue Depth',    value: s?.scheduler_queue_depth ?? '—', color: '#FFB800', sub: 'tasks waiting' },
            { label: 'Active',         value: s?.running ?? '—',              color: '#00D4FF', sub: 'executing now' },
            { label: 'Completed',      value: s?.completed ?? '—',            color: '#00FF9D', sub: 'all time' },
            { label: 'Failed',         value: s?.failed ?? '—',               color: '#FF3D71', sub: 'need attention' },
            { label: 'Max Concurrent', value: s?.concurrency_limit ?? '—',    color: '#7B2FFF', sub: 'scheduler limit' },
          ].map(({ label, value, color, sub }) => (
            <div key={label} style={{ borderRadius: 14, padding: '16px 18px', border: '1px solid rgba(255,255,255,0.07)', background: 'rgba(255,255,255,0.02)' }}>
              <div style={{ fontSize: 10, color: '#4A5280', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 6 }}>{label}</div>
              <div style={{ fontSize: 28, fontFamily: 'Space Grotesk', fontWeight: 700, color, marginBottom: 2 }}>{value}</div>
              <div style={{ fontSize: 10, color: '#4A5280' }}>{sub}</div>
            </div>
          ))}
        </div>

        {/* 3-column layout */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 300px', gap: 16 }}>

          {/* Running now */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ fontSize: 11, color: '#4A5280', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
              Running Now ({status?.running.length ?? 0})
            </div>
            {!status?.running.length && (
              <div style={{ padding: '40px 20px', textAlign: 'center', borderRadius: 14, border: '1px solid rgba(255,255,255,0.07)', color: '#4A5280', fontSize: 13 }}>
                <div style={{ fontSize: 28, marginBottom: 8 }}>○</div>
                No active executions
              </div>
            )}
            {status?.running.map((t, i) => <RunningCard key={t.pid} task={t} index={i} />)}

            {/* Queued */}
            {(status?.queued.length ?? 0) > 0 && (
              <>
                <div style={{ fontSize: 11, color: '#4A5280', textTransform: 'uppercase', letterSpacing: '0.1em', marginTop: 4 }}>
                  Queued ({status?.queued.length})
                </div>
                <div style={{ borderRadius: 14, border: '1px solid rgba(255,184,0,0.15)', overflow: 'hidden' }}>
                  {status?.queued.map(t => <TaskRow key={t.pid} task={t} color="#FFB800" />)}
                </div>
              </>
            )}
          </div>

          {/* Recent completed + failed */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ fontSize: 11, color: '#4A5280', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
              Recently Completed ({status?.recent_completed.length ?? 0})
            </div>
            <div style={{ borderRadius: 14, border: '1px solid rgba(255,255,255,0.07)', overflow: 'hidden', background: 'rgba(255,255,255,0.01)', flex: 1 }}>
              {!status?.recent_completed.length && (
                <div style={{ padding: 40, textAlign: 'center', color: '#4A5280', fontSize: 13 }}>No completed tasks yet</div>
              )}
              {status?.recent_completed.slice().reverse().map(t => <TaskRow key={t.pid} task={t} color="#00FF9D" />)}
            </div>

            {(status?.recent_failed.length ?? 0) > 0 && (
              <>
                <div style={{ fontSize: 11, color: '#FF3D71', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                  Failed ({status?.recent_failed.length})
                </div>
                <div style={{ borderRadius: 14, border: '1px solid rgba(255,61,113,0.15)', overflow: 'hidden' }}>
                  {status?.recent_failed.map(t => <TaskRow key={t.pid} task={t} color="#FF3D71" />)}
                </div>
              </>
            )}
          </div>

          {/* Event log */}
          <div style={{ borderRadius: 14, border: '1px solid rgba(255,255,255,0.07)', background: 'rgba(255,255,255,0.01)', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            <div style={{ padding: '12px 16px', borderBottom: '1px solid rgba(255,255,255,0.06)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0 }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: '#F0F4FF' }}>Change Log</span>
              <span style={{ fontSize: 10, color: '#4A5280', fontFamily: 'JetBrains Mono' }}>1.5s poll</span>
            </div>
            <div style={{ flex: 1, overflowY: 'auto', fontFamily: 'JetBrains Mono', fontSize: 11 }}>
              {history.length === 0 && (
                <div style={{ padding: 30, textAlign: 'center', color: '#2A3060' }}>Watching for changes...</div>
              )}
              {history.map((line, i) => (
                <div key={i} style={{ padding: '7px 14px', borderBottom: '1px solid rgba(255,255,255,0.03)', color: i === 0 ? '#00D4FF' : '#4A5280', fontSize: 10, opacity: 1 - (i * 0.08) }}>
                  {line}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
