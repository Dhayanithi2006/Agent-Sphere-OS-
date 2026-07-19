'use client';
import AppShell from '@/components/AppShell';

const SETTINGS_SECTIONS = [
  {
    title: 'LLM Providers',
    items: [
      { label: 'Primary Model', value: 'qwen3.7-plus', type: 'text' },
      { label: 'Fallback Model', value: 'qwen-plus', type: 'text' },
      { label: 'Base URL', value: 'https://dashscope-intl.aliyuncs.com', type: 'text' },
      { label: 'API Key', value: '••••••••••••••••', type: 'password' },
    ],
  },
  {
    title: 'Scheduler',
    items: [
      { label: 'Max Concurrency', value: '5', type: 'number' },
      { label: 'Task Timeout (s)', value: '300', type: 'number' },
      { label: 'Retry Limit', value: '3', type: 'number' },
    ],
  },
  {
    title: 'Memory',
    items: [
      { label: 'Max Memory Keys', value: '10000', type: 'number' },
      { label: 'Snapshot on Checkpoint', value: 'true', type: 'toggle' },
      { label: 'Vector Search Enabled', value: 'true', type: 'toggle' },
    ],
  },
  {
    title: 'Checkpoints',
    items: [
      { label: 'Max Retained', value: '500', type: 'number' },
      { label: 'Auto-checkpoint', value: 'true', type: 'toggle' },
      { label: 'DB Path', value: './checkpoints.sqlite', type: 'text' },
    ],
  },
  {
    title: 'Security',
    items: [
      { label: 'Auth Token', value: '••••••••', type: 'password' },
      { label: 'CORS Origins', value: 'http://localhost:3000', type: 'text' },
      { label: 'Rate Limiting', value: 'false', type: 'toggle' },
    ],
  },
];

export default function SettingsPage() {
  return (
    <AppShell>
      <div style={{ padding: '28px 32px', maxWidth: 720 }}>
        <h1 style={{ fontFamily: 'Space Grotesk, sans-serif', fontSize: 28, fontWeight: 700, color: '#F0F4FF', marginBottom: 6 }}>Settings</h1>
        <p style={{ color: '#4A5280', marginBottom: 32 }}>System configuration and preferences</p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          {SETTINGS_SECTIONS.map((section) => (
            <div key={section.title} className="glass" style={{ borderRadius: 16, border: '1px solid rgba(255,255,255,0.07)', overflow: 'hidden' }}>
              <div style={{ padding: '14px 20px', borderBottom: '1px solid rgba(255,255,255,0.06)', fontSize: 13, fontWeight: 600, color: '#F0F4FF' }}>
                {section.title}
              </div>
              {section.items.map((item) => (
                <div key={item.label} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 20px', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                  <div style={{ fontSize: 13, color: '#8892B0' }}>{item.label}</div>
                  {item.type === 'toggle' ? (
                    <div style={{ width: 40, height: 22, borderRadius: 11, background: item.value === 'true' ? 'rgba(0,212,255,0.3)' : 'rgba(255,255,255,0.08)', border: `1px solid ${item.value === 'true' ? 'rgba(0,212,255,0.4)' : 'rgba(255,255,255,0.1)'}`, position: 'relative', cursor: 'pointer' }}>
                      <div style={{ position: 'absolute', top: 2, left: item.value === 'true' ? 18 : 2, width: 16, height: 16, borderRadius: '50%', background: item.value === 'true' ? '#00D4FF' : '#4A5280', transition: 'left 0.2s' }} />
                    </div>
                  ) : (
                    <input defaultValue={item.value} type={item.type} style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 8, padding: '6px 12px', color: '#F0F4FF', fontSize: 13, outline: 'none', fontFamily: item.type === 'password' ? 'sans-serif' : 'JetBrains Mono, monospace', minWidth: 240, textAlign: 'right' }} />
                  )}
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>
    </AppShell>
  );
}
