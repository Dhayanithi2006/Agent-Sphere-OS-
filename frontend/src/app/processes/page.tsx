'use client';

import { useEffect, useState, useCallback } from 'react';
import AppShell from '@/components/AppShell';

const API = 'http://localhost:8000';

interface ProcessRow {
  pid: string;
  agent: string;
  task_id: string;
  current_state: string;
  current_task: string;
  created_time: string;
  updated_time: string;
}

const AGENT_LABELS: Record<string, string> = {
  planner: 'Planner Agent',
  researcher: 'Researcher Agent',
  developer: 'Developer Agent',
  tester: 'Tester Agent',
  reviewer: 'Reviewer Agent',
  showrunner_planner: 'Movie Planner',
  showrunner_script: 'Scriptwriter',
  showrunner_storyboard: 'Storyboard Artist',
  showrunner_scene: 'Scene Generator',
  showrunner_video: 'Video Producer',
  showrunner_voice: 'Voice Selector',
  showrunner_editor: 'Video Editor',
  showrunner_reviewer: 'Quality Reviewer',
  showrunner_reporter: 'Report Writer',
  showrunner_poster: 'Poster Designer',
};

const STATE_META: Record<string, { color: string; bg: string; label: string; desc: string }> = {
  running:   { color: '#00D4FF', bg: 'rgba(0,212,255,0.08)',   label: '● Running',   desc: 'Agent is actively working' },
  stopped:   { color: '#00FF9D', bg: 'rgba(0,255,157,0.06)',   label: '✓ Done',      desc: 'Task completed successfully' },
  completed: { color: '#00FF9D', bg: 'rgba(0,255,157,0.06)',   label: '✓ Done',      desc: 'Task completed successfully' },
  failed:    { color: '#FF3D71', bg: 'rgba(255,61,113,0.07)',  label: '✗ Failed',    desc: 'Error — recovery triggered' },
  created:   { color: '#7B2FFF', bg: 'rgba(123,47,255,0.06)', label: '◈ Created',   desc: 'Waiting to start' },
  pending:   { color: '#FFB800', bg: 'rgba(255,184,0,0.06)',   label: '○ Pending',   desc: 'Queued for execution' },
};

function dur(created: string, updated: string): string {
  try {
    const ms = new Date(updated).getTime() - new Date(created).getTime();
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
  } catch { return '—'; }
}

export default function ProcessesPage() {
  const [processes, setProcesses] = useState<ProcessRow[]>([]);
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('all');
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const r = await fetch(`${API}/processes`);
      const data = await r.json();
      setProcesses(Array.isArray(data) ? data : []);
    } catch {
      setProcesses([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 1500);
    return () => clearInterval(t);
  }, [load]);

  const filtered = processes.filter(p => {
    const state = (p.current_state || '').toLowerCase();
    if (filter === 'running' && state !== 'running') return false;
    if (filter === 'done' && !['stopped', 'completed'].includes(state)) return false;
    if (filter === 'failed' && state !== 'failed') return false;
    if (search) {
      const q = search.toLowerCase();
      return (p.pid || '').toLowerCase().includes(q)
        || (p.agent || '').toLowerCase().includes(q)
        || (p.current_task || '').toLowerCase().includes(q);
    }
    return true;
  }).sort((a, b) =>
    new Date(b.created_time || 0).getTime() - new Date(a.created_time || 0).getTime()
  );

  const counts = {
    all:     processes.length,
    running: processes.filter(p => p.current_state === 'running').length,
    done:    processes.filter(p => ['stopped','completed'].includes(p.current_state||'')).length,
    failed:  processes.filter(p => p.current_state === 'failed').length,
  };

  const FILTERS = [
    { key: 'all',     label: `All (${counts.all})` },
    { key: 'running', label: `Running (${counts.running})` },
    { key: 'done',    label: `Done (${counts.done})` },
    { key: 'failed',  label: `Failed (${counts.failed})` },
  ] as const;

  return (
    <AppShell>
      <div style={{ padding: '24px 28px' }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
          <div>
            <h1 style={{ fontFamily: 'Space Grotesk, sans-serif', fontSize: 26, fontWeight: 700, color: '#F0F4FF', margin: 0, marginBottom: 4 }}>
              Process Manager
            </h1>
            <p style={{ color: '#4A5280', fontSize: 13, margin: 0 }}>
              Every AI agent job — what it's doing, how long it took, whether it succeeded
            </p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 14px', background: counts.running > 0 ? 'rgba(0,212,255,0.08)' : 'rgba(255,255,255,0.03)', border: '1px solid rgba(0,212,255,0.2)', borderRadius: 100 }}>
            {counts.running > 0 && <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#00D4FF', boxShadow: '0 0 6px #00D4FF', display: 'inline-block' }} />}
            <span style={{ fontSize: 11, color: counts.running > 0 ? '#00D4FF' : '#4A5280', fontFamily: 'JetBrains Mono' }}>
              {counts.running > 0 ? `${counts.running} AGENTS WORKING` : 'ALL IDLE'}
            </span>
          </div>
        </div>

        {/* Quick stat cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 20 }}>
          {[
            { label: 'Total Runs', value: counts.all, color: '#F0F4FF', desc: 'agent executions' },
            { label: 'Active Now', value: counts.running, color: '#00D4FF', desc: 'processing' },
            { label: 'Completed', value: counts.done, color: '#00FF9D', desc: 'succeeded' },
            { label: 'Failed', value: counts.failed, color: '#FF3D71', desc: 'need attention' },
          ].map(({ label, value, color, desc }) => (
            <div key={label} style={{ borderRadius: 14, padding: '16px 18px', border: '1px solid rgba(255,255,255,0.07)', background: 'rgba(255,255,255,0.02)' }}>
              <div style={{ fontSize: 10, color: '#4A5280', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 6 }}>{label}</div>
              <div style={{ fontSize: 28, fontFamily: 'Space Grotesk', fontWeight: 700, color, marginBottom: 2 }}>{value}</div>
              <div style={{ fontSize: 11, color: '#4A5280' }}>{desc}</div>
            </div>
          ))}
        </div>

        {/* Filters + search */}
        <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 10, padding: 3, gap: 2 }}>
            {FILTERS.map(({ key, label }) => (
              <button key={key} onClick={() => setFilter(key)}
                style={{ padding: '5px 14px', borderRadius: 8, border: 'none', background: filter === key ? 'rgba(0,212,255,0.15)' : 'transparent', color: filter === key ? '#00D4FF' : '#4A5280', fontSize: 12, fontWeight: 500, cursor: 'pointer', transition: 'all 0.15s', whiteSpace: 'nowrap' }}>
                {label}
              </button>
            ))}
          </div>
          <input value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Search by agent name, task, or PID..."
            style={{ flex: 1, minWidth: 200, background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 10, padding: '7px 14px', color: '#F0F4FF', fontSize: 13, outline: 'none' }} />
        </div>

        {/* Process table */}
        <div style={{ borderRadius: 16, overflow: 'hidden', border: '1px solid rgba(255,255,255,0.07)', background: 'rgba(255,255,255,0.01)' }}>
          {/* Column headers */}
          <div style={{ display: 'grid', gridTemplateColumns: '90px 160px 1fr 140px 80px', padding: '10px 20px', background: 'rgba(255,255,255,0.02)', borderBottom: '1px solid rgba(255,255,255,0.06)', gap: 16 }}>
            {['Process ID', 'Agent', 'What it\'s doing', 'Status', 'Duration'].map(h => (
              <div key={h} style={{ fontSize: 10, color: '#4A5280', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.1em' }}>{h}</div>
            ))}
          </div>

          {loading && (
            <div style={{ padding: 40, textAlign: 'center', color: '#4A5280', fontSize: 13 }}>Loading processes...</div>
          )}

          <div style={{ maxHeight: 'calc(100vh - 400px)', overflowY: 'auto' }}>
            {!loading && filtered.length === 0 && (
              <div style={{ padding: 60, textAlign: 'center', color: '#4A5280' }}>
                <div style={{ fontSize: 32, marginBottom: 10 }}>○</div>
                <div>No processes match your filter</div>
              </div>
            )}
            {filtered.map((p, i) => {
              const state = (p.current_state || 'pending').toLowerCase();
              const meta = STATE_META[state] || STATE_META.pending;
              const agentLabel = AGENT_LABELS[p.agent] || p.agent || '—';

              return (
                <div key={p.pid || i}
                  style={{ display: 'grid', gridTemplateColumns: '90px 160px 1fr 140px 80px', padding: '12px 20px', gap: 16, borderBottom: '1px solid rgba(255,255,255,0.03)', alignItems: 'center', transition: 'background 0.1s', cursor: 'default' }}
                  onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.02)')}
                  onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                >
                  {/* PID */}
                  <div style={{ fontFamily: 'JetBrains Mono', fontSize: 11, color: '#00D4FF' }}>{p.pid || '—'}</div>

                  {/* Agent */}
                  <div style={{ fontSize: 12, color: '#F0F4FF', fontWeight: 500 }}>{agentLabel}</div>

                  {/* Task */}
                  <div style={{ fontSize: 12, color: '#8892B0', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {p.current_task || 'No task description'}
                  </div>

                  {/* Status pill */}
                  <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '4px 10px', borderRadius: 100, background: meta.bg, fontSize: 11, fontWeight: 600, color: meta.color, whiteSpace: 'nowrap' }}
                    title={meta.desc}>
                    {state === 'running' && <span style={{ width: 5, height: 5, borderRadius: '50%', background: meta.color, boxShadow: `0 0 5px ${meta.color}`, display: 'inline-block' }} />}
                    {meta.label}
                  </div>

                  {/* Duration */}
                  <div style={{ fontSize: 11, color: '#4A5280', fontFamily: 'JetBrains Mono' }}>
                    {p.created_time && p.updated_time ? dur(p.created_time, p.updated_time) : '—'}
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
