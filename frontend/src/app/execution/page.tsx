'use client';
import AppShell from '@/components/AppShell';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';

export default function ExecutionPage() {
  const [processes, setProcesses] = useState<any[]>([]);
  useEffect(() => {
    const load = async () => { try { const d = await api.getProcesses(); setProcesses(Array.isArray(d) ? d : []); } catch {} };
    load(); const t = setInterval(load, 1500); return () => clearInterval(t);
  }, []);
  return (
    <AppShell>
      <div style={{ padding: '28px 32px' }}>
        <h1 style={{ fontFamily: 'Space Grotesk, sans-serif', fontSize: 28, fontWeight: 700, color: '#F0F4FF', marginBottom: 6 }}>Execution Graph</h1>
        <p style={{ color: '#4A5280', marginBottom: 24 }}>Live DAG of agent execution · {processes.length} nodes</p>
        <div className="glass" style={{ borderRadius: 20, border: '1px solid rgba(255,255,255,0.07)', padding: 24, minHeight: 400, display: 'flex', flexWrap: 'wrap', gap: 12, alignContent: 'flex-start' }}>
          {processes.length === 0 && <div style={{ color: '#4A5280', margin: 'auto' }}>No executions yet. Run a workflow to see the DAG.</div>}
          {processes.map((p, i) => {
            const state = (p.current_state || p.state || 'pending').toLowerCase();
            const colors: Record<string, string> = { running: '#00D4FF', stopped: '#00FF9D', completed: '#00FF9D', failed: '#FF3D71', created: '#7B2FFF', pending: '#FFB800' };
            const color = colors[state] || '#4A5280';
            return (
              <div key={p.pid || i} style={{ borderRadius: 12, padding: '12px 16px', background: `${color}10`, border: `1px solid ${color}30`, minWidth: 140 }}>
                <div style={{ fontSize: 10, color, fontFamily: 'JetBrains Mono, monospace', marginBottom: 6, textTransform: 'uppercase' }}>{state}</div>
                <div style={{ fontSize: 13, color: '#F0F4FF', fontWeight: 600, marginBottom: 2 }}>{p.agent || '—'}</div>
                <div style={{ fontSize: 11, color: '#4A5280' }}>{p.pid || '—'}</div>
              </div>
            );
          })}
        </div>
      </div>
    </AppShell>
  );
}
