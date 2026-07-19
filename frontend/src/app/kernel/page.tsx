'use client';
import AppShell from '@/components/AppShell';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';

export default function KernelPage() {
  const [diag, setDiag] = useState<any>({});
  const [sv, setSv] = useState<any>({});

  useEffect(() => {
    const load = async () => {
      try {
        const [d, s] = await Promise.all([api.getDiagnostics(), api.getSupervisor()]);
        setDiag(d || {});
        setSv(s || {});
      } catch {}
    };
    load();
    const t = setInterval(load, 2000);
    return () => clearInterval(t);
  }, []);

  const subsystems = [
    { key: 'runtime',           label: 'Kernel Runtime' },
    { key: 'supervisor',        label: 'Supervisor' },
    { key: 'memory',            label: 'Memory Manager' },
    { key: 'shared_memory',     label: 'Shared Memory' },
    { key: 'execution_engine',  label: 'Execution Engine' },
    { key: 'dependency_manager',label: 'Dependency Manager' },
    { key: 'process_table',     label: 'Process Manager' },
  ];

  return (
    <AppShell>
      <div style={{ padding: '28px 32px' }}>
        <div style={{ marginBottom: 28 }}>
          <h1 style={{ fontFamily: 'Space Grotesk, sans-serif', fontSize: 28, fontWeight: 700, color: '#F0F4FF', marginBottom: 6 }}>
            Kernel
          </h1>
          <p style={{ color: '#4A5280', fontSize: 14 }}>
            Microkernel health · {sv.agent_count ?? '—'} agents · {sv.task_count ?? '—'} tasks executed
          </p>
        </div>

        {/* Subsystem status grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 16, marginBottom: 28 }}>
          {subsystems.map(({ key, label }) => {
            const alive = diag[key] === true || (typeof diag[key] === 'object' && diag[key] !== null);
            return (
              <div
                key={key}
                className="glass card-hover"
                style={{
                  borderRadius: 16,
                  padding: '20px',
                  border: `1px solid ${alive ? 'rgba(0,255,157,0.15)' : 'rgba(255,61,113,0.15)'}`,
                  background: alive ? 'rgba(0,255,157,0.03)' : 'rgba(255,61,113,0.03)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
                  <span
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: '50%',
                      background: alive ? '#00FF9D' : '#FF3D71',
                      boxShadow: `0 0 6px ${alive ? '#00FF9D' : '#FF3D71'}`,
                      display: 'inline-block',
                    }}
                  />
                  <span style={{ fontSize: 10, color: alive ? '#00FF9D' : '#FF3D71', fontFamily: 'JetBrains Mono, monospace', textTransform: 'uppercase' }}>
                    {alive ? 'ONLINE' : 'OFFLINE'}
                  </span>
                </div>
                <div style={{ fontSize: 14, fontWeight: 600, color: '#F0F4FF' }}>{label}</div>
              </div>
            );
          })}
        </div>

        {/* Raw diagnostics */}
        <div className="glass" style={{ borderRadius: 16, border: '1px solid rgba(255,255,255,0.07)', overflow: 'hidden' }}>
          <div style={{ padding: '14px 20px', borderBottom: '1px solid rgba(255,255,255,0.06)', fontSize: 13, fontWeight: 600, color: '#F0F4FF' }}>
            Diagnostics Output
          </div>
          <div style={{ padding: 20, maxHeight: 400, overflowY: 'auto' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {Object.entries(diag).map(([k, v]) => (
                <div
                  key={k}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '200px 1fr',
                    gap: 16,
                    padding: '8px 12px',
                    background: 'rgba(255,255,255,0.02)',
                    borderRadius: 8,
                  }}
                >
                  <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12, color: '#7B2FFF' }}>{k}</span>
                  <span style={{ fontSize: 12, color: '#8892B0', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {typeof v === 'boolean' ? (v ? '✓ true' : '✗ false') : typeof v === 'object' ? JSON.stringify(v).slice(0, 80) : String(v)}
                  </span>
                </div>
              ))}
              {Object.keys(diag).length === 0 && (
                <div style={{ color: '#4A5280', textAlign: 'center', padding: 20 }}>Loading diagnostics...</div>
              )}
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
