'use client';

import { useEffect, useState } from 'react';
import AppShell from '@/components/AppShell';
import { api } from '@/lib/api';

interface MemoryEntry {
  namespace: string;
  key: string;
  value: unknown;
}

export default function MemoryPage() {
  const [memory, setMemory] = useState<Record<string, Record<string, unknown>>>({});
  const [selected, setSelected] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [writeNS, setWriteNS] = useState('');
  const [writeKey, setWriteKey] = useState('');
  const [writeVal, setWriteVal] = useState('');
  const [writing, setWriting] = useState(false);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await api.getMemory();
        if (typeof data === 'object' && !Array.isArray(data)) {
          setMemory(data as Record<string, Record<string, unknown>>);
        }
      } catch {}
    };
    load();
    const t = setInterval(load, 3000);
    return () => clearInterval(t);
  }, []);

  const namespaces = Object.keys(memory);
  const activeNS = selected || namespaces[0] || null;
  const activeEntries = activeNS ? Object.entries(memory[activeNS] || {}) : [];
  const filteredEntries = activeEntries.filter(
    ([k]) => !search || k.toLowerCase().includes(search.toLowerCase())
  );

  const handleWrite = async () => {
    if (!writeNS || !writeKey) return;
    setWriting(true);
    try {
      await api.writeMemory(writeNS, writeKey, writeVal);
      setWriteNS('');
      setWriteKey('');
      setWriteVal('');
    } catch {}
    setWriting(false);
  };

  return (
    <AppShell>
      <div style={{ padding: '28px 32px' }}>
        <div style={{ marginBottom: 24 }}>
          <h1 style={{ fontFamily: 'Space Grotesk, sans-serif', fontSize: 28, fontWeight: 700, color: '#F0F4FF', marginBottom: 6 }}>
            Memory Explorer
          </h1>
          <p style={{ color: '#4A5280', fontSize: 14 }}>
            {namespaces.length} namespaces · Shared agent memory · live sync every 3s
          </p>
        </div>

        {/* ── Memory Snapshot Cards ── */}
        {namespaces.length > 0 && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginBottom: 24 }}>
            {namespaces.map(ns => {
              const keys = Object.keys(memory[ns] || {});
              const sizeBytes = JSON.stringify(memory[ns] || {}).length;
              const sizeKB = (sizeBytes / 1024).toFixed(1);
              const lastKey = keys[keys.length - 1];
              const isActive = activeNS === ns;
              return (
                <div key={ns} onClick={() => setSelected(ns)}
                  style={{
                    borderRadius: 14, padding: '16px', cursor: 'pointer',
                    border: `1px solid ${isActive ? 'rgba(0,212,255,0.35)' : 'rgba(255,255,255,0.07)'}`,
                    background: isActive ? 'rgba(0,212,255,0.08)' : 'rgba(255,255,255,0.02)',
                    transition: 'all 0.2s',
                  }}
                  onMouseEnter={e => { if (!isActive) { (e.currentTarget as HTMLElement).style.borderColor = 'rgba(0,212,255,0.2)'; (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.03)'; } }}
                  onMouseLeave={e => { if (!isActive) { (e.currentTarget as HTMLElement).style.borderColor = 'rgba(255,255,255,0.07)'; (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.02)'; } }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
                    <span style={{ fontSize: 18 }}>⯮</span>
                    <span style={{
                      fontSize: 9, padding: '2px 8px', borderRadius: 6, fontFamily: 'JetBrains Mono',
                      background: isActive ? 'rgba(0,212,255,0.15)' : 'rgba(255,255,255,0.06)',
                      color: isActive ? '#00D4FF' : '#4A5280',
                    }}>{keys.length} keys</span>
                  </div>
                  <div style={{ fontSize: 13, fontWeight: 700, color: isActive ? '#00D4FF' : '#F0F4FF', marginBottom: 4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{ns}</div>
                  <div style={{ fontSize: 10, color: '#4A5280', marginBottom: 8 }}>{sizeKB} KB stored</div>
                  {lastKey && (
                    <div style={{
                      fontSize: 10, color: '#7B2FFF', fontFamily: 'JetBrains Mono',
                      background: 'rgba(123,47,255,0.08)', borderRadius: 5, padding: '3px 7px',
                      overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                    }}>last: {lastKey}</div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: '200px 1fr', gap: 20, minHeight: 400 }}>
          {/* Namespace tree */}
          <div
            className="glass"
            style={{ borderRadius: 16, padding: '12px 0', border: '1px solid rgba(255,255,255,0.07)', height: 'fit-content' }}
          >
            <div style={{ padding: '6px 16px 10px', fontSize: 10, color: '#4A5280', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
              Namespaces
            </div>
            {namespaces.length === 0 && (
              <div style={{ padding: '8px 16px', fontSize: 13, color: '#4A5280' }}>Empty</div>
            )}
            {namespaces.map((ns) => (
              <button
                key={ns}
                onClick={() => setSelected(ns)}
                style={{
                  width: '100%',
                  textAlign: 'left',
                  padding: '9px 16px',
                  border: 'none',
                  background: activeNS === ns ? 'rgba(0,212,255,0.08)' : 'transparent',
                  borderLeft: activeNS === ns ? '2px solid #00D4FF' : '2px solid transparent',
                  color: activeNS === ns ? '#00D4FF' : '#8892B0',
                  fontSize: 13,
                  cursor: 'pointer',
                  transition: 'all 0.1s',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{ns}</span>
                <span
                  style={{
                    fontSize: 10,
                    background: 'rgba(255,255,255,0.06)',
                    borderRadius: 8,
                    padding: '1px 6px',
                    color: '#4A5280',
                    flexShrink: 0,
                    marginLeft: 6,
                  }}
                >
                  {Object.keys(memory[ns] || {}).length}
                </span>
              </button>
            ))}
          </div>

          {/* Key-value explorer */}
          <div>
            <div
              className="glass"
              style={{ borderRadius: 16, border: '1px solid rgba(255,255,255,0.07)', marginBottom: 16 }}
            >
              <div
                style={{
                  padding: '12px 20px',
                  borderBottom: '1px solid rgba(255,255,255,0.06)',
                  display: 'flex',
                  gap: 10,
                  alignItems: 'center',
                }}
              >
                <input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder={`Search keys in ${activeNS || 'namespace'}...`}
                  style={{
                    flex: 1,
                    background: 'transparent',
                    border: 'none',
                    outline: 'none',
                    color: '#F0F4FF',
                    fontSize: 13,
                  }}
                />
                <span style={{ fontSize: 12, color: '#4A5280' }}>{filteredEntries.length} keys</span>
              </div>

              <div style={{ maxHeight: 400, overflowY: 'auto' }}>
                {!activeNS && (
                  <div style={{ padding: 40, textAlign: 'center', color: '#4A5280' }}>Select a namespace</div>
                )}
                {activeNS && filteredEntries.length === 0 && (
                  <div style={{ padding: 40, textAlign: 'center', color: '#4A5280' }}>No keys found</div>
                )}
                {filteredEntries.map(([key, val]) => (
                  <div
                    key={key}
                    style={{
                      display: 'grid',
                      gridTemplateColumns: '200px 1fr',
                      padding: '10px 20px',
                      borderBottom: '1px solid rgba(255,255,255,0.04)',
                      gap: 20,
                      alignItems: 'center',
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255,255,255,0.02)')}
                    onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                  >
                    <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12, color: '#7B2FFF', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {key}
                    </div>
                    <div
                      style={{
                        fontSize: 12,
                        color: '#8892B0',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                        fontFamily: typeof val === 'object' ? 'JetBrains Mono, monospace' : 'inherit',
                      }}
                    >
                      {typeof val === 'object' ? JSON.stringify(val) : String(val)}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Write panel */}
            <div
              className="glass"
              style={{ borderRadius: 16, padding: '16px 20px', border: '1px solid rgba(255,255,255,0.07)' }}
            >
              <div style={{ fontSize: 12, color: '#4A5280', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 14 }}>
                Write Memory
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 2fr auto', gap: 10 }}>
                <input
                  value={writeNS}
                  onChange={(e) => setWriteNS(e.target.value)}
                  placeholder="namespace"
                  style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 8, padding: '7px 12px', color: '#F0F4FF', fontSize: 13, outline: 'none', fontFamily: 'JetBrains Mono, monospace' }}
                />
                <input
                  value={writeKey}
                  onChange={(e) => setWriteKey(e.target.value)}
                  placeholder="key"
                  style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 8, padding: '7px 12px', color: '#F0F4FF', fontSize: 13, outline: 'none', fontFamily: 'JetBrains Mono, monospace' }}
                />
                <input
                  value={writeVal}
                  onChange={(e) => setWriteVal(e.target.value)}
                  placeholder="value"
                  style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 8, padding: '7px 12px', color: '#F0F4FF', fontSize: 13, outline: 'none' }}
                />
                <button
                  onClick={handleWrite}
                  disabled={writing}
                  style={{
                    padding: '7px 16px',
                    background: 'linear-gradient(135deg, #00D4FF, #7B2FFF)',
                    border: 'none',
                    borderRadius: 8,
                    color: '#fff',
                    fontSize: 13,
                    fontWeight: 600,
                    cursor: writing ? 'not-allowed' : 'pointer',
                  }}
                >
                  {writing ? '...' : 'Write'}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
