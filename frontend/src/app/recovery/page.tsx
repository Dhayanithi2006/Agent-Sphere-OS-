'use client';
import AppShell from '@/components/AppShell';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';

export default function RecoveryPage() {
  const [processes, setProcesses] = useState<any[]>([]);
  const [recovering, setRecovering] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  useEffect(() => {
    const load = async () => { try { const d = await api.getProcesses(); setProcesses(Array.isArray(d) ? d : []); } catch {} };
    load(); const t = setInterval(load, 2000); return () => clearInterval(t);
  }, []);
  const failed = processes.filter(p => (p.current_state || p.state || '').toLowerCase() === 'failed');
  const handleRecover = async (taskId: string) => {
    setRecovering(taskId);
    try { await api.recover(taskId); setMsg('Recovery triggered for ' + taskId); setTimeout(() => setMsg(null), 3000); }
    catch (e: any) { setMsg('Failed: ' + e.message); setTimeout(() => setMsg(null), 3000); }
    finally { setRecovering(null); }
  };
  return (
    <AppShell>
      <div style={{ padding: '28px 32px' }}>
        <h1 style={{ fontFamily: 'Space Grotesk, sans-serif', fontSize: 28, fontWeight: 700, color: '#F0F4FF', marginBottom: 6 }}>Recovery Engine</h1>
        <p style={{ color: '#4A5280', marginBottom: 24 }}>{failed.length} failed processes · Auto-recovery enabled</p>
        {msg && <div style={{ marginBottom: 16, padding: '10px 16px', borderRadius: 10, background: 'rgba(0,255,157,0.08)', border: '1px solid rgba(0,255,157,0.2)', color: '#00FF9D', fontSize: 13 }}>{msg}</div>}
        <div className="glass" style={{ borderRadius: 16, border: '1px solid rgba(255,255,255,0.07)', overflow: 'hidden' }}>
          <div style={{ padding: '14px 20px', borderBottom: '1px solid rgba(255,255,255,0.06)', fontSize: 13, fontWeight: 600, color: '#F0F4FF' }}>Failed Processes</div>
          {failed.length === 0 ? (
            <div style={{ padding: 60, textAlign: 'center', color: '#4A5280' }}>
              <div style={{ fontSize: 32, marginBottom: 12 }}>✓</div>
              <div>No failed processes. All systems healthy.</div>
            </div>
          ) : (
            failed.map((p, i) => (
              <div key={p.pid || i} style={{ display: 'grid', gridTemplateColumns: '100px 120px 1fr auto', padding: '14px 20px', borderBottom: '1px solid rgba(255,255,255,0.03)', gap: 16, alignItems: 'center' }}>
                <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12, color: '#FF3D71' }}>{p.pid}</span>
                <span style={{ fontSize: 13, color: '#8892B0' }}>{p.agent}</span>
                <span style={{ fontSize: 12, color: '#F0F4FF' }}>{p.current_task || '—'}</span>
                <button onClick={() => handleRecover(p.task_id)} disabled={recovering === p.task_id}
                  style={{ padding: '6px 14px', borderRadius: 8, background: 'rgba(0,212,255,0.1)', border: '1px solid rgba(0,212,255,0.2)', color: '#00D4FF', fontSize: 12, cursor: 'pointer' }}>
                  {recovering === p.task_id ? '...' : '↺ Recover'}
                </button>
              </div>
            ))
          )}
        </div>
      </div>
    </AppShell>
  );
}
