'use client';

import { useEffect, useState } from 'react';
import AppShell from '@/components/AppShell';
import { api } from '@/lib/api';

interface Checkpoint {
  id: string;
  task_id: string;
  name: string;
  created_at: string;
  size?: number;
}

function timeAgo(dateStr: string) {
  try {
    const ms = Date.now() - new Date(dateStr).getTime();
    if (ms < 60000) return `${Math.floor(ms / 1000)}s ago`;
    if (ms < 3600000) return `${Math.floor(ms / 60000)}m ago`;
    if (ms < 86400000) return `${Math.floor(ms / 3600000)}h ago`;
    return `${Math.floor(ms / 86400000)}d ago`;
  } catch {
    return '—';
  }
}

export default function CheckpointsPage() {
  const [checkpoints, setCheckpoints] = useState<Checkpoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [restoring, setRestoring] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await api.getCheckpoints(100);
        const list = Array.isArray(data) ? data : data.checkpoints || [];
        setCheckpoints(list);
      } catch {
        setCheckpoints([]);
      } finally {
        setLoading(false);
      }
    };
    load();
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, []);

  const handleRestore = async (id: string) => {
    setRestoring(id);
    try {
      await api.rollback(id);
      setMessage(`Restored checkpoint ${id}`);
      setTimeout(() => setMessage(null), 3000);
    } catch (e: any) {
      setMessage('Restore failed: ' + e.message);
      setTimeout(() => setMessage(null), 3000);
    } finally {
      setRestoring(null);
    }
  };

  return (
    <AppShell>
      <div style={{ padding: '28px 32px' }}>
        {/* Header */}
        <div style={{ marginBottom: 24 }}>
          <h1 style={{ fontFamily: 'Space Grotesk, sans-serif', fontSize: 28, fontWeight: 700, color: '#F0F4FF', marginBottom: 6 }}>
            Checkpoint Timeline
          </h1>
          <p style={{ color: '#4A5280', fontSize: 14 }}>
            {checkpoints.length} checkpoints · System restore points
          </p>
        </div>

        {message && (
          <div
            style={{
              marginBottom: 20,
              padding: '12px 20px',
              borderRadius: 10,
              background: 'rgba(0,255,157,0.08)',
              border: '1px solid rgba(0,255,157,0.2)',
              color: '#00FF9D',
              fontSize: 13,
            }}
          >
            {message}
          </div>
        )}

        {loading ? (
          <div style={{ padding: 60, textAlign: 'center', color: '#4A5280' }}>Loading checkpoints...</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
            {checkpoints.length === 0 && (
              <div style={{ padding: 60, textAlign: 'center', color: '#4A5280' }}>No checkpoints yet</div>
            )}
            {checkpoints.map((cp, i) => (
              <div key={cp.id || i} style={{ display: 'flex', gap: 20, position: 'relative' }}>
                {/* Timeline line */}
                <div
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    flexShrink: 0,
                    paddingTop: 16,
                  }}
                >
                  <div
                    style={{
                      width: 12,
                      height: 12,
                      borderRadius: '50%',
                      background: 'linear-gradient(135deg, #00D4FF, #7B2FFF)',
                      boxShadow: '0 0 8px rgba(0,212,255,0.4)',
                      flexShrink: 0,
                    }}
                  />
                  {i < checkpoints.length - 1 && (
                    <div
                      style={{
                        width: 2,
                        flex: 1,
                        minHeight: 30,
                        background: 'linear-gradient(to bottom, rgba(0,212,255,0.2), rgba(123,47,255,0.1))',
                        margin: '4px 0',
                      }}
                    />
                  )}
                </div>

                {/* Card */}
                <div
                  className="glass card-hover"
                  style={{
                    flex: 1,
                    borderRadius: 12,
                    padding: '16px 20px',
                    marginBottom: 12,
                    border: '1px solid rgba(255,255,255,0.07)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: 16,
                  }}
                >
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
                      <span
                        style={{
                          fontFamily: 'JetBrains Mono, monospace',
                          fontSize: 12,
                          color: '#00D4FF',
                          background: 'rgba(0,212,255,0.08)',
                          padding: '2px 8px',
                          borderRadius: 6,
                          border: '1px solid rgba(0,212,255,0.15)',
                        }}
                      >
                        {(cp.id || '').slice(0, 32)}
                      </span>
                      <span style={{ fontSize: 11, color: '#4A5280' }}>{timeAgo(cp.created_at)}</span>
                    </div>
                    <div style={{ fontSize: 14, color: '#F0F4FF', fontWeight: 500 }}>
                      {cp.name || 'Checkpoint'}
                    </div>
                    <div
                      style={{
                        fontSize: 11,
                        color: '#4A5280',
                        fontFamily: 'JetBrains Mono, monospace',
                        marginTop: 4,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      task: {cp.task_id || '—'}
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
                    <button
                      onClick={() => handleRestore(cp.id)}
                      disabled={restoring === cp.id}
                      style={{
                        padding: '6px 14px',
                        borderRadius: 8,
                        background:
                          restoring === cp.id
                            ? 'rgba(255,255,255,0.05)'
                            : 'rgba(0,212,255,0.1)',
                        border: '1px solid rgba(0,212,255,0.2)',
                        color: '#00D4FF',
                        fontSize: 12,
                        cursor: restoring === cp.id ? 'not-allowed' : 'pointer',
                        transition: 'all 0.15s',
                      }}
                    >
                      {restoring === cp.id ? '...' : '↺ Restore'}
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}
