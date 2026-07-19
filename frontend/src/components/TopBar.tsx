'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';

interface SystemHealth {
  agentCount?: number;
  taskCount?: number;
  processCount?: number;
  status?: string;
}

export default function TopBar() {
  const [health, setHealth] = useState<SystemHealth>({});
  const [time, setTime] = useState('');

  useEffect(() => {
    const tick = () => setTime(new Date().toLocaleTimeString('en-US', { hour12: false }));
    tick();
    const t = setInterval(tick, 1000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const sv = await api.getSupervisor();
        setHealth({
          agentCount: sv.agent_count,
          taskCount: sv.task_count,
          processCount: sv.process_count,
          status: sv.status,
        });
      } catch {}
    };
    fetchHealth();
    const t = setInterval(fetchHealth, 3000);
    return () => clearInterval(t);
  }, []);

  return (
    <header
      style={{
        height: 48,
        background: 'rgba(8,8,24,0.9)',
        backdropFilter: 'blur(20px)',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 20px',
        position: 'sticky',
        top: 0,
        zIndex: 30,
        flexShrink: 0,
      }}
    >
      {/* Left: kernel status */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span
            style={{
              width: 6,
              height: 6,
              borderRadius: '50%',
              background: '#00FF9D',
              boxShadow: '0 0 8px #00FF9D',
              display: 'inline-block',
            }}
          />
          <span style={{ fontSize: 11, color: '#4A5280', fontFamily: 'JetBrains Mono, monospace' }}>
            KERNEL ACTIVE
          </span>
        </div>
        <div
          style={{
            height: 14,
            width: 1,
            background: 'rgba(255,255,255,0.08)',
          }}
        />
        <div style={{ display: 'flex', gap: 16 }}>
          {[
            { label: 'Agents', value: health.agentCount ?? '—', color: '#00D4FF' },
            { label: 'Tasks', value: health.taskCount ?? '—', color: '#7B2FFF' },
            { label: 'Procs', value: health.processCount ?? '—', color: '#00FF9D' },
          ].map(({ label, value, color }) => (
            <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
              <span style={{ fontSize: 11, color: '#4A5280' }}>{label}</span>
              <span style={{ fontSize: 12, color, fontFamily: 'JetBrains Mono, monospace', fontWeight: 600 }}>
                {value}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Right: clock + tag */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <div
          style={{
            fontSize: 10,
            color: '#4A5280',
            fontFamily: 'JetBrains Mono, monospace',
            background: 'rgba(0,212,255,0.05)',
            border: '1px solid rgba(0,212,255,0.1)',
            borderRadius: 4,
            padding: '2px 8px',
          }}
        >
          {time}
        </div>
        <div
          style={{
            fontSize: 10,
            color: 'rgba(255,255,255,0.2)',
            fontFamily: 'JetBrains Mono, monospace',
          }}
        >
          AgentSphere OS v2.0
        </div>
      </div>
    </header>
  );
}
