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
  const [date, setDate] = useState('');

  useEffect(() => {
    const tick = () => {
      const now = new Date();
      setTime(now.toLocaleTimeString('en-US', { hour12: false }));
      setDate(now.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));
    };
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

  const pills = [
    { label: 'Agents',    value: health.agentCount  ?? '—', color: '#8B5CF6', bg: 'rgba(139,92,246,0.12)',  border: 'rgba(139,92,246,0.25)' },
    { label: 'Tasks',     value: health.taskCount   ?? '—', color: '#F472B6', bg: 'rgba(244,114,182,0.12)', border: 'rgba(244,114,182,0.25)' },
    { label: 'Processes', value: health.processCount ?? '—', color: '#22D3EE', bg: 'rgba(34,211,238,0.10)',  border: 'rgba(34,211,238,0.22)' },
  ];

  return (
    <header
      style={{
        height: 52,
        background: 'rgba(5,5,8,0.85)',
        backdropFilter: 'blur(28px) saturate(180%)',
        WebkitBackdropFilter: 'blur(28px) saturate(180%)',
        borderBottom: '1px solid rgba(139,92,246,0.1)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 24px',
        position: 'sticky',
        top: 0,
        zIndex: 30,
        flexShrink: 0,
      }}
    >
      {/* ── Left: kernel status + counters ────── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
        {/* Kernel badge */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 7,
            background: 'rgba(52,211,153,0.08)',
            border: '1px solid rgba(52,211,153,0.2)',
            borderRadius: 8,
            padding: '4px 10px',
          }}
        >
          <span
            style={{
              width: 6,
              height: 6,
              borderRadius: '50%',
              background: '#34D399',
              boxShadow: '0 0 8px #34D399',
              display: 'inline-block',
              animation: 'topbar-pulse 2s ease-in-out infinite',
            }}
          />
          <span
            style={{
              fontSize: 11,
              fontFamily: 'JetBrains Mono, monospace',
              fontWeight: 500,
              color: '#34D399',
              letterSpacing: '0.08em',
            }}
          >
            KERNEL ACTIVE
          </span>
        </div>

        {/* Separator */}
        <div style={{ width: 1, height: 20, background: 'rgba(139,92,246,0.15)' }} />

        {/* Metric pills */}
        <div style={{ display: 'flex', gap: 8 }}>
          {pills.map(({ label, value, color, bg, border }) => (
            <div
              key={label}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                background: bg,
                border: `1px solid ${border}`,
                borderRadius: 7,
                padding: '3px 10px',
              }}
            >
              <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', fontFamily: 'Outfit, sans-serif' }}>
                {label}
              </span>
              <span
                style={{
                  fontSize: 13,
                  color,
                  fontFamily: 'JetBrains Mono, monospace',
                  fontWeight: 600,
                }}
              >
                {value}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* ── Right: clock + version ─────────────── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
        {/* Clock */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            background: 'rgba(139,92,246,0.07)',
            border: '1px solid rgba(139,92,246,0.15)',
            borderRadius: 8,
            padding: '4px 12px',
          }}
        >
          <span style={{ fontSize: 10, color: '#5C5880', fontFamily: 'Outfit, sans-serif' }}>{date}</span>
          <div style={{ width: 1, height: 12, background: 'rgba(139,92,246,0.2)' }} />
          <span
            style={{
              fontSize: 12,
              color: '#C4B5FD',
              fontFamily: 'JetBrains Mono, monospace',
              fontWeight: 500,
              letterSpacing: '0.05em',
            }}
          >
            {time}
          </span>
        </div>

        {/* Version tag */}
        <div
          style={{
            fontSize: 10,
            fontFamily: 'JetBrains Mono, monospace',
            background: 'linear-gradient(135deg, rgba(139,92,246,0.15), rgba(244,114,182,0.1))',
            border: '1px solid rgba(139,92,246,0.2)',
            borderRadius: 6,
            padding: '3px 9px',
            color: '#A78BFA',
            letterSpacing: '0.05em',
          }}
        >
          v2.0
        </div>
      </div>

      <style>{`
        @keyframes topbar-pulse {
          0%, 100% { box-shadow: 0 0 6px #34D399; opacity: 1; }
          50%       { box-shadow: 0 0 14px #34D399, 0 0 28px rgba(52,211,153,0.3); opacity: 0.8; }
        }
      `}</style>
    </header>
  );
}
