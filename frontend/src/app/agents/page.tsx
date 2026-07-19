'use client';

import { useEffect, useState } from 'react';
import AppShell from '@/components/AppShell';
import { api } from '@/lib/api';

interface Agent {
  agent_id: string;
  name: string;
  role: string;
  status: string;
  capabilities: string[];
  model: string;
}

// ── Per-agent personality config ──────────────────────────────────────────────
const AGENT_META: Record<string, { icon: string; color: string; gradient: string; desc: string; caps: string[] }> = {
  planner:               { icon: '🗺️', color: '#7B2FFF', gradient: 'linear-gradient(135deg,#7B2FFF22,#7B2FFF08)', desc: 'Breaks goals into step-by-step execution plans', caps: ['Planning','Decomposition','Strategy'] },
  researcher:            { icon: '🔬', color: '#00D4FF', gradient: 'linear-gradient(135deg,#00D4FF22,#00D4FF08)', desc: 'Gathers context, facts and domain knowledge', caps: ['Research','Analysis','Context'] },
  developer:             { icon: '💻', color: '#00FF9D', gradient: 'linear-gradient(135deg,#00FF9D22,#00FF9D08)', desc: 'Writes implementation code and project files', caps: ['Code Gen','File I/O','Debugging'] },
  tester:                { icon: '🧪', color: '#FFB800', gradient: 'linear-gradient(135deg,#FFB80022,#FFB80008)', desc: 'Validates logic, catches bugs, writes test cases', caps: ['Testing','QA','Validation'] },
  reviewer:              { icon: '🔍', color: '#FF3D71', gradient: 'linear-gradient(135deg,#FF3D7122,#FF3D7108)', desc: 'Reviews output quality and suggests improvements', caps: ['Review','Feedback','Quality'] },
  showrunner_planner:    { icon: '📋', color: '#7B2FFF', gradient: 'linear-gradient(135deg,#7B2FFF22,#7B2FFF08)', desc: 'Plans the full movie production pipeline', caps: ['Pipeline','Scheduling'] },
  showrunner_researcher: { icon: '📚', color: '#00D4FF', gradient: 'linear-gradient(135deg,#00D4FF22,#00D4FF08)', desc: 'Researches themes, genre and visual style', caps: ['Genre','Themes','Style'] },
  showrunner_script:     { icon: '📝', color: '#00FF9D', gradient: 'linear-gradient(135deg,#00FF9D22,#00FF9D08)', desc: 'Writes movie scripts and dialogue', caps: ['Screenplay','Dialogue'] },
  showrunner_storyboard: { icon: '🎨', color: '#FFB800', gradient: 'linear-gradient(135deg,#FFB80022,#FFB80008)', desc: 'Creates scene-by-scene storyboard prompts', caps: ['Storyboard','Scene Design'] },
  showrunner_scene:      { icon: '🎬', color: '#FF3D71', gradient: 'linear-gradient(135deg,#FF3D7122,#FF3D7108)', desc: 'Generates individual scene compositions', caps: ['Scene Gen','Composition'] },
  showrunner_prompt:     { icon: '✨', color: '#7B2FFF', gradient: 'linear-gradient(135deg,#7B2FFF22,#7B2FFF08)', desc: 'Engineers optimal prompts for video generation', caps: ['Prompt Eng','Optimization'] },
  showrunner_video:      { icon: '🎥', color: '#00D4FF', gradient: 'linear-gradient(135deg,#00D4FF22,#00D4FF08)', desc: 'Calls Happyhorse API to generate video clips', caps: ['T2V','I2V','Video Gen'] },
  showrunner_voice:      { icon: '🎙️', color: '#00FF9D', gradient: 'linear-gradient(135deg,#00FF9D22,#00FF9D08)', desc: 'Synthesizes voiceover using CosyVoice TTS', caps: ['TTS','Voiceover'] },
  showrunner_audio:      { icon: '🎵', color: '#FFB800', gradient: 'linear-gradient(135deg,#FFB80022,#FFB80008)', desc: 'Composes background music and audio mixing', caps: ['Music','SFX','Mixing'] },
  showrunner_subtitle:   { icon: '💬', color: '#FF3D71', gradient: 'linear-gradient(135deg,#FF3D7122,#FF3D7108)', desc: 'Generates and synchronises subtitles/captions', caps: ['Subtitles','SRT','Captions'] },
  showrunner_editor:     { icon: '✂️', color: '#00D4FF', gradient: 'linear-gradient(135deg,#00D4FF22,#00D4FF08)', desc: 'Assembles clips into a final cut timeline', caps: ['Video Edit','Timeline'] },
  showrunner_reviewer:   { icon: '👁️', color: '#7B2FFF', gradient: 'linear-gradient(135deg,#7B2FFF22,#7B2FFF08)', desc: 'Reviews completed movie for quality and coherence', caps: ['QA','Feedback'] },
  showrunner_director:   { icon: '🎭', color: '#FF3D71', gradient: 'linear-gradient(135deg,#FF3D7122,#FF3D7108)', desc: 'Oversees creative direction of the full production', caps: ['Direction','Creative'] },
  showrunner_poster:     { icon: '🖼️', color: '#FFB800', gradient: 'linear-gradient(135deg,#FFB80022,#FFB80008)', desc: 'Generates movie poster and thumbnail art', caps: ['Image Gen','Design'] },
  showrunner_trailer:    { icon: '📽️', color: '#00FF9D', gradient: 'linear-gradient(135deg,#00FF9D22,#00FF9D08)', desc: 'Cuts a cinematic trailer from the full movie', caps: ['Trailer','Highlight Reel'] },
  showrunner_publisher:  { icon: '📤', color: '#00D4FF', gradient: 'linear-gradient(135deg,#00D4FF22,#00D4FF08)', desc: 'Publishes assets to OSS / CDN for distribution', caps: ['Upload','CDN','Publish'] },
  showrunner_reporter:   { icon: '📊', color: '#7B2FFF', gradient: 'linear-gradient(135deg,#7B2FFF22,#7B2FFF08)', desc: 'Generates production report and cost summary', caps: ['Reporting','Analytics'] },
};

function getMeta(id: string) {
  return AGENT_META[id] || {
    icon: '🤖', color: '#00D4FF',
    gradient: 'linear-gradient(135deg,#00D4FF22,#00D4FF08)',
    desc: 'AgentSphere autonomous agent', caps: [],
  };
}

// ── Agent Card ─────────────────────────────────────────────────────────────────
function AgentCard({ agent, index }: { agent: Agent; index: number }) {
  const id = agent.agent_id || '';
  const meta = getMeta(id);
  const isShowrunner = id.includes('showrunner');
  const [hovered, setHovered] = useState(false);

  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        borderRadius: 18,
        padding: '20px',
        background: hovered ? meta.gradient.replace('08)', '14)') : meta.gradient,
        border: `1px solid ${hovered ? meta.color + '40' : meta.color + '18'}`,
        cursor: 'pointer',
        transition: 'all 0.25s cubic-bezier(.4,0,.2,1)',
        transform: hovered ? 'translateY(-4px) scale(1.01)' : 'none',
        boxShadow: hovered ? `0 12px 32px ${meta.color}18` : 'none',
        animation: `fadeSlideUp 0.4s ease both`,
        animationDelay: `${index * 30}ms`,
        display: 'flex',
        flexDirection: 'column',
        gap: 12,
      }}
    >
      {/* Top row: icon + status badge */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div style={{
          width: 48, height: 48, borderRadius: 14,
          background: `${meta.color}18`,
          border: `1px solid ${meta.color}30`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 22, flexShrink: 0,
          boxShadow: hovered ? `0 0 20px ${meta.color}30` : 'none',
          transition: 'box-shadow 0.25s',
        }}>
          {meta.icon}
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 5 }}>
          {/* READY badge */}
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: 5, padding: '3px 9px',
            borderRadius: 100, background: 'rgba(0,255,157,0.08)',
            border: '1px solid rgba(0,255,157,0.2)', fontSize: 9, color: '#00FF9D',
            fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.08em',
          }}>
            <span style={{ width: 5, height: 5, borderRadius: '50%', background: '#00FF9D', boxShadow: '0 0 5px #00FF9D', display: 'inline-block' }} />
            READY
          </div>
          {/* Type badge */}
          <div style={{
            fontSize: 9, padding: '2px 8px', borderRadius: 6,
            background: isShowrunner ? 'rgba(123,47,255,0.12)' : 'rgba(0,212,255,0.1)',
            border: isShowrunner ? '1px solid rgba(123,47,255,0.25)' : '1px solid rgba(0,212,255,0.2)',
            color: isShowrunner ? '#7B2FFF' : '#00D4FF',
            fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.05em',
          }}>
            {isShowrunner ? '🎬 SHOWRUNNER' : '⚙️ CORE'}
          </div>
        </div>
      </div>

      {/* Name */}
      <div>
        <div style={{ fontWeight: 700, fontSize: 14, color: '#F0F4FF', marginBottom: 4, fontFamily: 'Space Grotesk, sans-serif' }}>
          {agent.name || id}
        </div>
        <div style={{ fontSize: 11, color: '#4A5280', lineHeight: 1.5 }}>
          {meta.desc}
        </div>
      </div>

      {/* Capability pills */}
      {meta.caps.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
          {meta.caps.map((c) => (
            <span key={c} style={{
              fontSize: 10, padding: '2px 8px', borderRadius: 6,
              background: `${meta.color}10`,
              border: `1px solid ${meta.color}22`,
              color: meta.color,
            }}>
              {c}
            </span>
          ))}
        </div>
      )}

      {/* Bottom: color accent bar */}
      <div style={{
        height: 2, borderRadius: 2,
        background: `linear-gradient(90deg, ${meta.color}60, transparent)`,
        marginTop: 4,
        transition: 'opacity 0.25s',
        opacity: hovered ? 1 : 0.4,
      }} />
    </div>
  );
}

// ── Stat pill ─────────────────────────────────────────────────────────────────
function StatPill({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 10, padding: '10px 18px',
      borderRadius: 12, background: `${color}0d`, border: `1px solid ${color}22`,
    }}>
      <div style={{ width: 8, height: 8, borderRadius: '50%', background: color, boxShadow: `0 0 8px ${color}` }} />
      <span style={{ fontFamily: 'JetBrains Mono', fontSize: 18, fontWeight: 700, color }}>{value}</span>
      <span style={{ fontSize: 12, color: '#4A5280' }}>{label}</span>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [search, setSearch] = useState('');
  const [view, setView] = useState<'all' | 'core' | 'showrunner'>('all');

  useEffect(() => {
    const load = async () => {
      try { const data = await api.getAgents(); setAgents(Array.isArray(data) ? data : []); } catch {}
    };
    load();
    const t = setInterval(load, 3000);
    return () => clearInterval(t);
  }, []);

  const filtered = agents.filter((a) => {
    const id = (a.agent_id || '').toLowerCase();
    if (view === 'core' && id.includes('showrunner')) return false;
    if (view === 'showrunner' && !id.includes('showrunner')) return false;
    if (search) return id.includes(search.toLowerCase()) || (a.name || '').toLowerCase().includes(search.toLowerCase());
    return true;
  });

  const coreCount = agents.filter((a) => !(a.agent_id || '').includes('showrunner')).length;
  const srCount = agents.filter((a) => (a.agent_id || '').includes('showrunner')).length;

  const tabs: { key: typeof view; label: string }[] = [
    { key: 'all', label: `All (${agents.length})` },
    { key: 'core', label: `Core (${coreCount})` },
    { key: 'showrunner', label: `Showrunner (${srCount})` },
  ];

  return (
    <AppShell>
      <style>{`
        @keyframes fadeSlideUp {
          from { opacity: 0; transform: translateY(16px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
      `}</style>

      <div style={{ padding: '28px 32px', minHeight: '100vh' }}>

        {/* ── Header ── */}
        <div style={{ marginBottom: 28, display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16 }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
              <span style={{ fontSize: 28 }}>◉</span>
              <h1 style={{ fontFamily: 'Space Grotesk, sans-serif', fontSize: 28, fontWeight: 700, color: '#F0F4FF', margin: 0 }}>
                Agent Fleet
              </h1>
            </div>
            <p style={{ color: '#4A5280', fontSize: 13, margin: 0 }}>
              All registered agents — live status · hover to explore capabilities
            </p>
          </div>

          {/* Live stat pills */}
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            <StatPill label="Total" value={agents.length} color="#00D4FF" />
            <StatPill label="Core" value={coreCount} color="#00FF9D" />
            <StatPill label="Showrunner" value={srCount} color="#7B2FFF" />
          </div>
        </div>

        {/* ── Filter bar ── */}
        <div style={{ display: 'flex', gap: 12, marginBottom: 28, flexWrap: 'wrap', alignItems: 'center' }}>
          {/* Tab switcher */}
          <div style={{
            display: 'flex', background: 'rgba(255,255,255,0.03)',
            border: '1px solid rgba(255,255,255,0.07)', borderRadius: 10, padding: 3, gap: 2,
          }}>
            {tabs.map(({ key, label }) => (
              <button
                key={key}
                onClick={() => setView(key)}
                style={{
                  padding: '6px 16px', borderRadius: 8, border: 'none',
                  background: view === key ? 'rgba(0,212,255,0.15)' : 'transparent',
                  color: view === key ? '#00D4FF' : '#4A5280',
                  fontSize: 12, fontWeight: view === key ? 700 : 400,
                  cursor: 'pointer', transition: 'all 0.15s', whiteSpace: 'nowrap',
                  outline: 'none',
                }}
              >{label}</button>
            ))}
          </div>

          {/* Search */}
          <div style={{ flex: 1, minWidth: 220, position: 'relative' }}>
            <span style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: '#4A5280', fontSize: 14 }}>🔍</span>
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search agents by name or capability..."
              style={{
                width: '100%', boxSizing: 'border-box',
                background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)',
                borderRadius: 10, padding: '8px 14px 8px 36px',
                color: '#F0F4FF', fontSize: 13, outline: 'none',
              }}
            />
          </div>

          {/* Live indicator */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#4A5280', fontSize: 12 }}>
            <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#00FF9D', boxShadow: '0 0 6px #00FF9D', display: 'inline-block', animation: 'pulse 2s infinite' }} />
            Live
          </div>
        </div>

        {/* ── Section label if showing showrunner ── */}
        {view === 'showrunner' && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20,
            padding: '10px 16px', borderRadius: 10,
            background: 'rgba(123,47,255,0.07)', border: '1px solid rgba(123,47,255,0.15)',
          }}>
            <span style={{ fontSize: 20 }}>🎬</span>
            <div>
              <div style={{ color: '#7B2FFF', fontWeight: 700, fontSize: 13 }}>Showrunner Pipeline — {srCount} specialised agents</div>
              <div style={{ color: '#4A5280', fontSize: 11 }}>End-to-end AI film production · Script → Video → Audio → Publish</div>
            </div>
          </div>
        )}

        {view === 'core' && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20,
            padding: '10px 16px', borderRadius: 10,
            background: 'rgba(0,212,255,0.07)', border: '1px solid rgba(0,212,255,0.15)',
          }}>
            <span style={{ fontSize: 20 }}>⚙️</span>
            <div>
              <div style={{ color: '#00D4FF', fontWeight: 700, fontSize: 13 }}>Core OS Agents — {coreCount} foundation agents</div>
              <div style={{ color: '#4A5280', fontSize: 11 }}>Planner → Researcher → Developer → Tester → Reviewer</div>
            </div>
          </div>
        )}

        {/* ── Agent grid ── */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))',
          gap: 16,
        }}>
          {filtered.map((a, i) => (
            <AgentCard key={a.agent_id} agent={a} index={i} />
          ))}
          {filtered.length === 0 && (
            <div style={{
              gridColumn: '1/-1', padding: '80px 0', textAlign: 'center',
              color: '#4A5280',
            }}>
              <div style={{ fontSize: 40, marginBottom: 12 }}>🔍</div>
              <div style={{ fontSize: 14 }}>No agents match your search</div>
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
