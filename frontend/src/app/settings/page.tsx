'use client';
import AppShell from '@/components/AppShell';

const SECTIONS = [
  {
    title: 'LLM Providers',
    icon: '🧠',
    color: '#8B5CF6',
    items: [
      { label: 'Primary Model',  value: 'qwen3.7-plus',                            type: 'text'     },
      { label: 'Max Model',      value: 'qwen3.7-max',                             type: 'text'     },
      { label: 'Base URL',       value: 'https://dashscope-intl.aliyuncs.com',     type: 'text'     },
      { label: 'API Key',        value: '••••••••••••••••',                        type: 'password' },
    ],
  },
  {
    title: 'Scheduler',
    icon: '🕐',
    color: '#22D3EE',
    items: [
      { label: 'Max Concurrency',  value: '5',   type: 'number' },
      { label: 'Task Timeout (s)', value: '300', type: 'number' },
      { label: 'Retry Limit',      value: '3',   type: 'number' },
    ],
  },
  {
    title: 'Memory',
    icon: '💾',
    color: '#34D399',
    items: [
      { label: 'Max Memory Keys',         value: '10000', type: 'number' },
      { label: 'Snapshot on Checkpoint',  value: 'true',  type: 'toggle' },
      { label: 'Vector Search Enabled',   value: 'true',  type: 'toggle' },
    ],
  },
  {
    title: 'Checkpoints',
    icon: '💠',
    color: '#F472B6',
    items: [
      { label: 'Max Retained',   value: '500',                  type: 'number' },
      { label: 'Auto-checkpoint', value: 'true',               type: 'toggle' },
      { label: 'DB Path',        value: './checkpoints.sqlite', type: 'text'   },
    ],
  },
  {
    title: 'Security',
    icon: '🔒',
    color: '#FBBF24',
    items: [
      { label: 'Auth Token',   value: '••••••••',                type: 'password' },
      { label: 'CORS Origins', value: 'http://localhost:3000',   type: 'text'     },
      { label: 'Rate Limiting', value: 'false',                  type: 'toggle'  },
    ],
  },
];

export default function SettingsPage() {
  return (
    <AppShell>
      <div style={{ padding: '28px 32px', maxWidth: 760 }}>
        {/* Header */}
        <div style={{ marginBottom: 28 }}>
          <h1 className="page-title" style={{ marginBottom: 6 }}>
            <span className="gradient-text">Settings</span>
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: 13, fontFamily: 'Sora, sans-serif' }}>
            System configuration and runtime preferences
          </p>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {SECTIONS.map((section) => (
            <div key={section.title} className="glass-card" style={{ overflow: 'hidden' }}>
              {/* Section header */}
              <div
                style={{
                  padding: '14px 20px',
                  borderBottom: '1px solid var(--border-soft)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  background: `rgba(${hexToRgb(section.color)},0.04)`,
                }}
              >
                <div
                  style={{
                    width: 30,
                    height: 30,
                    borderRadius: 8,
                    background: `rgba(${hexToRgb(section.color)},0.15)`,
                    border: `1px solid rgba(${hexToRgb(section.color)},0.25)`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: 14,
                    flexShrink: 0,
                  }}
                >
                  {section.icon}
                </div>
                <span
                  style={{
                    fontFamily: 'Outfit, sans-serif',
                    fontWeight: 700,
                    fontSize: 14,
                    color: 'var(--text-primary)',
                  }}
                >
                  {section.title}
                </span>
              </div>

              {/* Items */}
              {section.items.map((item, idx) => (
                <div
                  key={item.label}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '13px 20px',
                    borderBottom: idx < section.items.length - 1 ? '1px solid rgba(255,255,255,0.04)' : 'none',
                    transition: 'background 0.15s',
                  }}
                  onMouseEnter={e => (e.currentTarget.style.background = `rgba(${hexToRgb(section.color)},0.03)`)}
                  onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                >
                  <div style={{ fontSize: 13, color: 'var(--text-secondary)', fontFamily: 'Sora, sans-serif' }}>
                    {item.label}
                  </div>

                  {item.type === 'toggle' ? (
                    <div
                      style={{
                        width: 42,
                        height: 24,
                        borderRadius: 12,
                        background: item.value === 'true'
                          ? `rgba(${hexToRgb(section.color)},0.3)`
                          : 'rgba(255,255,255,0.06)',
                        border: `1px solid rgba(${hexToRgb(section.color)},${item.value === 'true' ? '0.5' : '0.1'})`,
                        position: 'relative',
                        cursor: 'pointer',
                        transition: 'all 0.25s ease',
                        flexShrink: 0,
                      }}
                    >
                      <div
                        style={{
                          position: 'absolute',
                          top: 3,
                          left: item.value === 'true' ? 19 : 3,
                          width: 16,
                          height: 16,
                          borderRadius: '50%',
                          background: item.value === 'true' ? section.color : '#3A3660',
                          boxShadow: item.value === 'true' ? `0 0 8px ${section.color}` : 'none',
                          transition: 'all 0.25s ease',
                        }}
                      />
                    </div>
                  ) : (
                    <input
                      defaultValue={item.value}
                      type={item.type}
                      className="input-aurora"
                      style={{
                        minWidth: 260,
                        textAlign: 'right',
                        fontFamily: item.type === 'password' ? 'sans-serif' : 'JetBrains Mono, monospace',
                        fontSize: 13,
                      }}
                    />
                  )}
                </div>
              ))}
            </div>
          ))}
        </div>

        {/* Save button */}
        <div style={{ marginTop: 24, display: 'flex', gap: 12 }}>
          <button className="btn-primary">Save Configuration</button>
          <button className="btn-ghost">Reset to Defaults</button>
        </div>
      </div>
    </AppShell>
  );
}

function hexToRgb(hex: string): string {
  const r = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return r ? `${parseInt(r[1],16)},${parseInt(r[2],16)},${parseInt(r[3],16)}` : '139,92,246';
}
