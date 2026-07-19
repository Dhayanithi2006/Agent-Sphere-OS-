'use client';
import AppShell from '@/components/AppShell';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';

export default function MarketplacePage() {
  const [plugins, setPlugins] = useState<any[]>([]);
  useEffect(() => {
    const load = async () => { try { const d = await api.getMarketplace(); setPlugins(Array.isArray(d) ? d : Object.values(d || {})); } catch {} };
    load();
  }, []);
  return (
    <AppShell>
      <div style={{ padding: '28px 32px' }}>
        <h1 style={{ fontFamily: 'Space Grotesk, sans-serif', fontSize: 28, fontWeight: 700, color: '#F0F4FF', marginBottom: 6 }}>Plugin Marketplace</h1>
        <p style={{ color: '#4A5280', marginBottom: 24 }}>Extend AgentSphere OS with new agent capabilities</p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 16 }}>
          {plugins.length === 0 && (
            [{ name: 'Showrunner Suite', desc: 'Complete AI movie generation pipeline with 12 specialized agents', icon: '🎬', color: '#7B2FFF', installed: true },
             { name: 'Code Review Agent', desc: 'Automated PR reviews and security scanning', icon: '⬡', color: '#00D4FF', installed: false },
             { name: 'Data Analyst', desc: 'CSV, SQL, and chart generation agent', icon: '◬', color: '#00FF9D', installed: false },
             { name: 'Web Scraper', desc: 'Intelligent web crawling and extraction', icon: '◉', color: '#FFB800', installed: false }].map((p) => (
              <div key={p.name} className="glass glass-hover card-hover" style={{ borderRadius: 16, padding: '20px', border: '1px solid rgba(255,255,255,0.07)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 14 }}>
                  <div style={{ width: 44, height: 44, borderRadius: 12, background: `${p.color}15`, border: `1px solid ${p.color}30`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 22 }}>{p.icon}</div>
                  {p.installed && <span style={{ fontSize: 10, color: '#00FF9D', background: 'rgba(0,255,157,0.08)', border: '1px solid rgba(0,255,157,0.2)', borderRadius: 100, padding: '3px 10px', height: 'fit-content' }}>INSTALLED</span>}
                </div>
                <div style={{ fontSize: 14, fontWeight: 600, color: '#F0F4FF', marginBottom: 6 }}>{p.name}</div>
                <div style={{ fontSize: 12, color: '#4A5280', marginBottom: 16, lineHeight: 1.5 }}>{p.desc}</div>
                <button style={{ width: '100%', padding: '8px', borderRadius: 8, background: p.installed ? 'rgba(255,255,255,0.04)' : `${p.color}20`, border: `1px solid ${p.installed ? 'rgba(255,255,255,0.08)' : p.color + '40'}`, color: p.installed ? '#4A5280' : p.color, fontSize: 13, cursor: 'pointer' }}>
                  {p.installed ? 'Installed' : 'Install'}
                </button>
              </div>
            ))
          )}
          {plugins.map((p: any, i: number) => (
            <div key={i} className="glass glass-hover card-hover" style={{ borderRadius: 16, padding: '20px', border: '1px solid rgba(255,255,255,0.07)' }}>
              <div style={{ fontSize: 14, fontWeight: 600, color: '#F0F4FF', marginBottom: 6 }}>{p.name || p.plugin_id}</div>
              <div style={{ fontSize: 12, color: '#4A5280' }}>{p.description || '—'}</div>
            </div>
          ))}
        </div>
      </div>
    </AppShell>
  );
}
