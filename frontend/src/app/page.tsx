'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import AppShell from '@/components/AppShell';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ── Prompt templates ─────────────────────────────────────────────────────────
const PROMPT_TEMPLATES = [
  { icon: '🌐', label: 'Login Page', prompt: 'Create a beautiful login page with glassmorphism design, email and password fields, and a gradient submit button', workflow: 'coding', color: '#00D4FF' },
  { icon: '🧠', label: 'Neural Network', prompt: 'Design a CNN image classifier architecture for detecting objects in images with 5 classes', workflow: 'coding', color: '#7B2FFF' },
  { icon: '🔐', label: 'Auth API', prompt: 'Write a complete REST API for user authentication with JWT tokens, registration, login, and refresh endpoints', workflow: 'coding', color: '#00FF9D' },
  { icon: '🔬', label: 'Research Report', prompt: 'Research the latest advances in transformer models and write a comprehensive summary with key findings', workflow: 'research', color: '#FFB800' },
  { icon: '📊', label: 'Dashboard UI', prompt: 'Create a data analytics dashboard with charts, KPI cards, and a dark theme using HTML CSS and JavaScript', workflow: 'coding', color: '#FF3D71' },
  { icon: '🤖', label: 'LSTM Model', prompt: 'Design an LSTM neural network architecture for time series forecasting with attention mechanism', workflow: 'coding', color: '#00D4FF' },
];

// ── Pipeline steps config ─────────────────────────────────────────────────────
const PIPELINE_AGENTS = [
  { id: 'planner',    label: 'Plan',     icon: '🗺️', color: '#7B2FFF' },
  { id: 'researcher', label: 'Research', icon: '🔬', color: '#00D4FF' },
  { id: 'developer',  label: 'Build',    icon: '💻', color: '#00FF9D' },
  { id: 'tester',     label: 'Test',     icon: '🧪', color: '#FFB800' },
  { id: 'reviewer',   label: 'Review',   icon: '🔍', color: '#FF3D71' },
];

// ── Particle canvas ───────────────────────────────────────────────────────────
function ParticleField() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d')!;
    let raf: number;
    const resize = () => { canvas.width = canvas.offsetWidth; canvas.height = canvas.offsetHeight; };
    resize();
    window.addEventListener('resize', resize);
    const N = 55;
    const particles = Array.from({ length: N }, () => ({
      x: Math.random() * (canvas.width || 800),
      y: Math.random() * (canvas.height || 400),
      vx: (Math.random() - 0.5) * 0.35,
      vy: (Math.random() - 0.5) * 0.35,
      r: Math.random() * 1.8 + 0.8,
    }));
    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      for (let i = 0; i < N; i++) {
        for (let j = i + 1; j < N; j++) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const d = Math.sqrt(dx * dx + dy * dy);
          if (d < 110) {
            ctx.beginPath();
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particles[j].x, particles[j].y);
            ctx.strokeStyle = `rgba(0,212,255,${0.07 * (1 - d / 110)})`;
            ctx.lineWidth = 0.5;
            ctx.stroke();
          }
        }
      }
      particles.forEach(p => {
        ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(0,212,255,0.4)';
        ctx.shadowBlur = 5; ctx.shadowColor = '#00D4FF';
        ctx.fill(); ctx.shadowBlur = 0;
        p.x += p.vx; p.y += p.vy;
        if (p.x < 0 || p.x > canvas.width) p.vx *= -1;
        if (p.y < 0 || p.y > canvas.height) p.vy *= -1;
      });
      raf = requestAnimationFrame(draw);
    };
    draw();
    return () => { cancelAnimationFrame(raf); window.removeEventListener('resize', resize); };
  }, []);
  return <canvas ref={canvasRef} style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', opacity: 0.5 }} />;
}

// ── Pending terminal while task runs ─────────────────────────────────────────
interface ExecLine {
  type: 'input' | 'system' | 'agent' | 'output' | 'error' | 'success';
  text: string;
  agent?: string;
  time: string;
}

function PendingTerminal({ lines, loading }: { lines: ExecLine[]; loading: boolean }) {
  const endRef = useRef<HTMLDivElement>(null);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [lines]);

  const colors: Record<string, string> = {
    input: '#F0F4FF', system: '#4A5280', agent: '#7B2FFF',
    output: '#8892B0', error: '#FF3D71', success: '#00FF9D',
  };
  const prefixes: Record<string, string> = {
    input: '$ ', system: '# ', agent: '◉ ', output: '  ', error: '✗ ', success: '✓ ',
  };

  return (
    <div style={{
      marginTop: 16, background: 'rgba(0,0,0,0.5)', border: '1px solid rgba(0,212,255,0.15)',
      borderRadius: 12, padding: '14px 16px', maxHeight: 220, overflowY: 'auto',
      fontFamily: 'JetBrains Mono, monospace', fontSize: 12, lineHeight: 1.7,
    }}>
      {lines.map((l, i) => (
        <div key={i} style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
          <span style={{ color: '#2A3060', fontSize: 10, paddingTop: 2, flexShrink: 0 }}>{l.time}</span>
          {l.agent && <span style={{ color: '#7B2FFF', paddingTop: 1, flexShrink: 0, fontSize: 11 }}>[{l.agent}]</span>}
          <span style={{ color: colors[l.type] || '#8892B0' }}>
            <span style={{ opacity: 0.5 }}>{prefixes[l.type] || '  '}</span>
            {l.text}
          </span>
        </div>
      ))}
      {loading && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#00D4FF', paddingTop: 4 }}>
          <span style={{ animation: 'spin 1s linear infinite', display: 'inline-block' }}>⟳</span>
          <span>Agents building your project...</span>
        </div>
      )}
      <div ref={endRef} />
    </div>
  );
}

// ── Build Output viewer ───────────────────────────────────────────────────────
interface BuildFile { filename: string; language: string; content: string; }
interface BuildResult {
  output_type: 'web' | 'api' | 'architecture' | 'writing' | 'code';
  files: BuildFile[];
  preview_url: string;
  architecture: string;
  summary: string;
  raw: string;
  file_count: number;
}

type TabId = 'preview' | 'code' | 'files' | 'summary';

const langIcons: Record<string, string> = {
  html: '🌐', css: '🎨', javascript: '⚡', js: '⚡', typescript: '🔷', ts: '🔷',
  python: '🐍', py: '🐍', json: '📋', bash: '⚙️', sh: '⚙️', sql: '🗄️',
  yaml: '📄', yml: '📄', text: '📝', txt: '📝',
};

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button onClick={copy} style={{
      padding: '3px 10px', background: copied ? 'rgba(0,255,157,0.15)' : 'rgba(255,255,255,0.07)',
      border: `1px solid ${copied ? 'rgba(0,255,157,0.3)' : 'rgba(255,255,255,0.12)'}`,
      borderRadius: 6, color: copied ? '#00FF9D' : '#8892B0', fontSize: 11, cursor: 'pointer',
      transition: 'all 0.2s',
    }}>
      {copied ? '✓ Copied' : 'Copy'}
    </button>
  );
}

function DownloadButton({ filename, content }: { filename: string; content: string }) {
  const download = () => {
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = filename; a.click();
    URL.revokeObjectURL(url);
  };
  return (
    <button onClick={download} style={{
      padding: '3px 10px', background: 'rgba(255,255,255,0.07)',
      border: '1px solid rgba(255,255,255,0.12)',
      borderRadius: 6, color: '#8892B0', fontSize: 11, cursor: 'pointer',
    }}>↓</button>
  );
}

function MermaidDiagram({ chart }: { chart: string }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!chart || !ref.current) return;
    const el = ref.current;

    const renderMermaid = (mermaidObj: any) => {
      mermaidObj.initialize({
        theme: 'dark',
        themeVariables: { background: '#0a0f1e', primaryColor: '#1a2340' }
      });
      mermaidObj.render('mermaid-diag-' + Date.now(), chart)
        .then(({ svg }: { svg: string }) => { el.innerHTML = svg; })
        .catch(() => { el.innerHTML = `<pre style="color:#8892B0;font-size:12px;white-space:pre-wrap;padding:16px">${chart}</pre>`; });
    };

    // Try global mermaid (from CDN script in layout)
    if ((window as any).mermaid) {
      renderMermaid((window as any).mermaid);
    } else {
      // Inject CDN script once
      if (!document.getElementById('mermaid-cdn')) {
        const s = document.createElement('script');
        s.id = 'mermaid-cdn';
        s.src = 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js';
        s.onload = () => renderMermaid((window as any).mermaid);
        document.head.appendChild(s);
      } else {
        // Script loading — show chart as code fallback
        el.innerHTML = `<pre style="color:#8892B0;font-size:12px;white-space:pre-wrap;padding:16px">${chart}</pre>`;
      }
    }
  }, [chart]);
  return <div ref={ref} style={{ width: '100%', overflowX: 'auto', padding: 8, minHeight: 200 }} />;
}

function BuildOutput({ result, goal, elapsed }: { result: BuildResult; goal: string; elapsed: number }) {
  const [activeTab, setActiveTab] = useState<TabId>(() => {
    if (result.output_type === 'web' && result.preview_url) return 'preview';
    if (result.output_type === 'architecture') return 'preview';
    return 'code';
  });
  const [activeFile, setActiveFile] = useState(0);

  const tabs: { id: TabId; label: string; icon: string }[] = [
    { id: 'preview', label: result.output_type === 'architecture' ? 'Architecture' : 'Preview', icon: result.output_type === 'web' ? '🖼️' : result.output_type === 'architecture' ? '🗺️' : '👁️' },
    { id: 'code', label: 'Code', icon: '💻' },
    { id: 'files', label: `Files (${result.file_count})`, icon: '📁' },
    { id: 'summary', label: 'Summary', icon: '📋' },
  ];

  const typeColors: Record<string, string> = {
    web: '#00D4FF', api: '#7B2FFF', architecture: '#00FF9D', writing: '#FFB800', code: '#8892B0',
  };
  const typeColor = typeColors[result.output_type] || '#8892B0';

  return (
    <div style={{ marginTop: 20, borderRadius: 16, border: `1px solid ${typeColor}30`, background: 'rgba(0,0,0,0.4)', overflow: 'hidden' }}>
      {/* Header */}
      <div style={{ padding: '14px 18px', borderBottom: '1px solid rgba(255,255,255,0.06)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#00FF9D', boxShadow: '0 0 8px #00FF9D', display: 'inline-block' }} />
          <span style={{ color: '#00FF9D', fontFamily: 'JetBrains Mono', fontSize: 12, fontWeight: 700 }}>BUILD COMPLETE</span>
          <span style={{ color: '#2A3060', fontSize: 11 }}>· {elapsed.toFixed(1)}s · {result.file_count} file{result.file_count !== 1 ? 's' : ''}</span>
        </div>
        <span style={{ fontSize: 11, padding: '3px 10px', borderRadius: 20, background: `${typeColor}15`, border: `1px solid ${typeColor}30`, color: typeColor, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          {result.output_type}
        </span>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', borderBottom: '1px solid rgba(255,255,255,0.06)', padding: '0 4px' }}>
        {tabs.map(tab => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)} style={{
            padding: '10px 16px', background: 'transparent', border: 'none', outline: 'none', cursor: 'pointer',
            color: activeTab === tab.id ? typeColor : '#4A5280', fontSize: 12, fontWeight: activeTab === tab.id ? 700 : 400,
            borderBottom: activeTab === tab.id ? `2px solid ${typeColor}` : '2px solid transparent',
            transition: 'all 0.15s', display: 'flex', alignItems: 'center', gap: 5,
          }}>
            <span>{tab.icon}</span> {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div style={{ minHeight: 300 }}>

        {/* PREVIEW TAB */}
        {activeTab === 'preview' && (
          <div>
            {result.output_type === 'web' && result.preview_url ? (
              <div>
                <div style={{ padding: '8px 12px', background: 'rgba(0,212,255,0.05)', borderBottom: '1px solid rgba(0,212,255,0.1)', display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#FF3D71', display: 'inline-block' }} />
                  <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#FFB800', display: 'inline-block' }} />
                  <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#00FF9D', display: 'inline-block' }} />
                  <span style={{ flex: 1, textAlign: 'center', fontSize: 11, color: '#4A5280', fontFamily: 'JetBrains Mono' }}>
                    {API}{result.preview_url}
                  </span>
                  <a href={`${API}${result.preview_url}`} target="_blank" rel="noreferrer" style={{ color: '#00D4FF', fontSize: 11, textDecoration: 'none' }}>↗ Open</a>
                </div>
                <iframe
                  src={`${API}${result.preview_url}`}
                  style={{ width: '100%', height: 420, border: 'none', background: '#fff' }}
                  title="Live Preview"
                  sandbox="allow-scripts allow-same-origin"
                />
              </div>
            ) : result.output_type === 'architecture' && result.architecture ? (
              <div style={{ padding: 20 }}>
                <p style={{ color: '#4A5280', fontSize: 12, marginBottom: 16 }}>AI-generated architecture diagram for: <em style={{ color: '#8892B0' }}>{goal}</em></p>
                <MermaidDiagram chart={result.architecture} />
              </div>
            ) : result.output_type === 'writing' ? (
              <div style={{ padding: 24, maxWidth: 720 }}>
                {result.files[0]?.content.split('\n').map((line, i) => {
                  if (line.startsWith('# ')) return <h1 key={i} style={{ color: '#F0F4FF', fontFamily: 'Space Grotesk', marginBottom: 8 }}>{line.slice(2)}</h1>;
                  if (line.startsWith('## ')) return <h2 key={i} style={{ color: '#8892B0', fontFamily: 'Space Grotesk', marginBottom: 6 }}>{line.slice(3)}</h2>;
                  if (line.startsWith('- ')) return <li key={i} style={{ color: '#8892B0', marginLeft: 16, marginBottom: 2 }}>{line.slice(2)}</li>;
                  if (!line.trim()) return <br key={i} />;
                  return <p key={i} style={{ color: '#8892B0', lineHeight: 1.7, marginBottom: 4 }}>{line}</p>;
                })}
              </div>
            ) : (
              <div style={{ padding: 32, textAlign: 'center', color: '#4A5280' }}>
                <div style={{ fontSize: 32, marginBottom: 10 }}>💻</div>
                <div>No live preview available for this output type.</div>
                <div style={{ fontSize: 12, marginTop: 6 }}>Switch to the <strong>Code</strong> or <strong>Files</strong> tab to view the output.</div>
              </div>
            )}
          </div>
        )}

        {/* CODE TAB */}
        {activeTab === 'code' && (
          <div style={{ display: 'grid', gridTemplateColumns: result.files.length > 1 ? '160px 1fr' : '1fr', height: 400 }}>
            {result.files.length > 1 && (
              <div style={{ borderRight: '1px solid rgba(255,255,255,0.06)', padding: '8px 0', overflowY: 'auto' }}>
                {result.files.map((f, i) => (
                  <button key={i} onClick={() => setActiveFile(i)} style={{
                    width: '100%', textAlign: 'left', padding: '8px 12px', background: activeFile === i ? 'rgba(0,212,255,0.08)' : 'transparent',
                    border: 'none', borderLeft: activeFile === i ? '2px solid #00D4FF' : '2px solid transparent',
                    color: activeFile === i ? '#F0F4FF' : '#4A5280', fontSize: 11, cursor: 'pointer',
                    display: 'flex', alignItems: 'center', gap: 6, transition: 'all 0.15s',
                  }}>
                    <span>{langIcons[f.language] || '📄'}</span>
                    <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{f.filename}</span>
                  </button>
                ))}
              </div>
            )}
            <div style={{ position: 'relative', overflowY: 'auto' }}>
              <div style={{ position: 'sticky', top: 0, padding: '8px 12px', background: 'rgba(10,15,30,0.9)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.06)', zIndex: 1 }}>
                <span style={{ fontFamily: 'JetBrains Mono', fontSize: 12, color: '#8892B0' }}>
                  {langIcons[result.files[activeFile]?.language] || '📄'} {result.files[activeFile]?.filename}
                </span>
                <div style={{ display: 'flex', gap: 6 }}>
                  <CopyButton text={result.files[activeFile]?.content || ''} />
                  <DownloadButton filename={result.files[activeFile]?.filename || 'file.txt'} content={result.files[activeFile]?.content || ''} />
                </div>
              </div>
              <pre style={{ margin: 0, padding: '12px 16px', fontFamily: 'JetBrains Mono, monospace', fontSize: 12, lineHeight: 1.7, color: '#8892B0', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                {result.files[activeFile]?.content}
              </pre>
            </div>
          </div>
        )}

        {/* FILES TAB */}
        {activeTab === 'files' && (
          <div style={{ padding: 16 }}>
            <div style={{ display: 'grid', gap: 8 }}>
              {result.files.map((f, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 14px', borderRadius: 10, background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)' }}>
                  <span style={{ fontSize: 18 }}>{langIcons[f.language] || '📄'}</span>
                  <div style={{ flex: 1 }}>
                    <div style={{ color: '#F0F4FF', fontSize: 13, fontWeight: 600 }}>{f.filename}</div>
                    <div style={{ color: '#4A5280', fontSize: 11 }}>{f.language.toUpperCase()} · {f.content.split('\n').length} lines · {(new Blob([f.content]).size / 1024).toFixed(1)} KB</div>
                  </div>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <CopyButton text={f.content} />
                    <DownloadButton filename={f.filename} content={f.content} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* SUMMARY TAB */}
        {activeTab === 'summary' && (
          <div style={{ padding: 24 }}>
            <div style={{ marginBottom: 20, padding: 16, borderRadius: 12, background: 'rgba(0,212,255,0.05)', border: '1px solid rgba(0,212,255,0.12)' }}>
              <div style={{ fontSize: 11, color: '#4A5280', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 8 }}>What was built</div>
              <p style={{ color: '#8892B0', lineHeight: 1.7, margin: 0 }}>{result.summary}</p>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: 10 }}>
              {[
                { label: 'Output Type', value: result.output_type.toUpperCase(), color: typeColor },
                { label: 'Files', value: String(result.file_count), color: '#7B2FFF' },
                { label: 'Total Lines', value: String(result.files.reduce((a, f) => a + f.content.split('\n').length, 0)), color: '#FFB800' },
                { label: 'Size', value: `${(result.files.reduce((a, f) => a + new Blob([f.content]).size, 0) / 1024).toFixed(1)} KB`, color: '#00FF9D' },
              ].map(({ label, value, color }) => (
                <div key={label} style={{ padding: '14px 16px', borderRadius: 10, border: '1px solid rgba(255,255,255,0.06)', background: 'rgba(255,255,255,0.01)' }}>
                  <div style={{ fontSize: 10, color: '#4A5280', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 6 }}>{label}</div>
                  <div style={{ fontSize: 22, fontFamily: 'Space Grotesk', fontWeight: 700, color }}>{value}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Quick action card ─────────────────────────────────────────────────────────
function QuickAction({ href, icon, label, desc, color }: { href: string; icon: string; label: string; desc: string; color: string }) {
  return (
    <Link href={href} style={{ textDecoration: 'none' }}>
      <div
        style={{ borderRadius: 14, padding: '16px', cursor: 'pointer', border: '1px solid rgba(255,255,255,0.07)', background: 'rgba(255,255,255,0.02)', transition: 'all 0.2s' }}
        onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.04)'; (e.currentTarget as HTMLElement).style.borderColor = `${color}30`; (e.currentTarget as HTMLElement).style.transform = 'translateY(-2px)'; }}
        onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.02)'; (e.currentTarget as HTMLElement).style.borderColor = 'rgba(255,255,255,0.07)'; (e.currentTarget as HTMLElement).style.transform = 'none'; }}
      >
        <div style={{ width: 38, height: 38, borderRadius: 10, background: `${color}15`, border: `1px solid ${color}30`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18, marginBottom: 10 }}>{icon}</div>
        <div style={{ fontWeight: 600, fontSize: 13, color: '#F0F4FF', marginBottom: 3 }}>{label}</div>
        <div style={{ fontSize: 11, color: '#4A5280', lineHeight: 1.4 }}>{desc}</div>
      </div>
    </Link>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function HomePage() {
  const [supervisor, setSupervisor] = useState<any>({});
  const [goal, setGoal] = useState('');
  const [workflow, setWorkflow] = useState('coding');
  const [loading, setLoading] = useState(false);
  const [execLines, setExecLines] = useState<ExecLine[]>([]);
  const [hasExecuted, setHasExecuted] = useState(false);
  const [buildResult, setBuildResult] = useState<BuildResult | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const pollRef = useRef<NodeJS.Timeout | null>(null);
  const startTimeRef = useRef<number>(0);

  const ts = () => new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });

  const addLine = (line: Omit<ExecLine, 'time'>) =>
    setExecLines(prev => [...prev, { ...line, time: ts() }]);

  useEffect(() => {
    const load = async () => {
      try { const s = await (await fetch(`${API}/supervisor`)).json(); setSupervisor(s || {}); } catch {}
    };
    load(); const t = setInterval(load, 3000); return () => clearInterval(t);
  }, []);

  const handleExecute = async () => {
    if (!goal.trim()) return;
    setLoading(true);
    setHasExecuted(true);
    setBuildResult(null);
    setExecLines([]);
    startTimeRef.current = Date.now();

    addLine({ type: 'input', text: goal });
    addLine({ type: 'system', text: `Routing to kernel — workflow: ${workflow}` });

    try {
      const res = await fetch(`${API}/kernel/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task: goal, workflow }),
      });

      const data = await res.json();

      if (!res.ok) {
        addLine({ type: 'error', text: `Kernel error: ${data.detail || res.statusText}` });
        setLoading(false);
        return;
      }

      addLine({ type: 'system', text: `Task ID: ${data.task_id || '—'} · PID: ${data.pid || '—'}` });
      addLine({ type: 'system', text: `Agent: ${data.agent_id || '—'} · Status: queued` });

      const taskId = data.task_id;
      const pid = data.pid;

      if (pid || taskId) {
        let done = false;
        let ticks = 0;
        pollRef.current = setInterval(async () => {
          try {
            // Poll process state
            if (pid) {
              const pr = await fetch(`${API}/processes`);
              const procs: any[] = await pr.json();
              const proc = procs.find(p => p.pid === pid);
              if (proc) {
                const state = (proc.current_state || '').toLowerCase();
                if (state === 'running') {
                  addLine({ type: 'agent', text: proc.current_task || 'Building...', agent: proc.agent });
                }
              }
            }

            // Poll task result endpoint
            if (taskId) {
              const tr = await fetch(`${API}/tasks/${taskId}/result`);
              const taskResult = await tr.json();

              if (taskResult.ready) {
                done = true;
                clearInterval(pollRef.current!);
                const elapsedSec = (Date.now() - startTimeRef.current) / 1000;
                setElapsed(elapsedSec);

                if (taskResult.status === 'failed') {
                  addLine({ type: 'error', text: 'Build failed — check logs' });
                } else {
                  addLine({ type: 'success', text: `Build complete · ${taskResult.file_count} file(s) generated` });
                  setBuildResult(taskResult as BuildResult);
                }
                setLoading(false);
              }
            }

            ticks++;
            if (ticks > 60) { clearInterval(pollRef.current!); setLoading(false); }
          } catch { clearInterval(pollRef.current!); setLoading(false); }
        }, 1500);
      } else {
        addLine({ type: 'success', text: 'Task queued — monitor Processes for updates' });
        setLoading(false);
      }
    } catch (e: any) {
      addLine({ type: 'error', text: e.message });
      setLoading(false);
    }
  };

  return (
    <AppShell>
      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        @keyframes fadeIn { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:none; } }
      `}</style>

      {/* ── Hero ── */}
      <div style={{ position: 'relative', minHeight: 480, display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
        <ParticleField />
        <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%,-50%)', width: 700, height: 700, background: 'radial-gradient(circle, rgba(0,212,255,0.05) 0%, transparent 65%)', pointerEvents: 'none' }} />

        <div style={{ position: 'relative', textAlign: 'center', padding: '60px 40px', maxWidth: 760, width: '100%' }}>
          {/* Status pill */}
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8, background: 'rgba(0,212,255,0.06)', border: '1px solid rgba(0,212,255,0.15)', borderRadius: 100, padding: '5px 16px', marginBottom: 22 }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#00FF9D', boxShadow: '0 0 8px #00FF9D', display: 'inline-block' }} />
            <span style={{ fontSize: 11, color: '#00D4FF', fontFamily: 'JetBrains Mono' }}>
              KERNEL ACTIVE · {supervisor.agent_count ?? 0} AGENTS · {supervisor.task_count ?? 0} TASKS EXECUTED
            </span>
          </div>

          <h1 style={{ fontFamily: 'Space Grotesk, sans-serif', fontSize: 'clamp(32px, 5vw, 60px)', fontWeight: 700, color: '#F0F4FF', marginBottom: 14, lineHeight: 1.1 }}>
            The Operating System
            <br />
            <span style={{ background: 'linear-gradient(135deg, #00D4FF 0%, #7B2FFF 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              for Autonomous AI
            </span>
          </h1>

          <p style={{ fontSize: 15, color: '#4A5280', margin: '0 auto 28px', maxWidth: 460 }}>
            Describe what to build — agents design, code, and deliver the result.
          </p>

          {/* ── Goal input with workflow selector ── */}
          <div style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(0,212,255,0.2)', borderRadius: 14, padding: '8px 8px 8px 16px', display: 'flex', gap: 8, marginBottom: 12 }}>
            <input
              value={goal}
              onChange={e => setGoal(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleExecute()}
              placeholder="Describe what to build — e.g. Create a login page with glassmorphism design..."
              style={{ flex: 1, background: 'transparent', border: 'none', outline: 'none', color: '#F0F4FF', fontSize: 14, minWidth: 0 }}
            />
            <select value={workflow} onChange={e => setWorkflow(e.target.value)}
              style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, padding: '8px 10px', color: '#8892B0', fontSize: 12, outline: 'none', cursor: 'pointer', flexShrink: 0 }}>
              <option value="coding">💻 Coding</option>
              <option value="research">🔬 Research</option>
              <option value="analysis">📊 Analysis</option>
              <option value="writing">✍ Writing</option>
              <option value="automation">⚙ Automation</option>
            </select>
            <button onClick={handleExecute} disabled={loading}
              style={{ padding: '10px 22px', background: loading ? 'rgba(0,212,255,0.2)' : 'linear-gradient(135deg, #00D4FF, #7B2FFF)', border: 'none', borderRadius: 10, color: '#fff', fontSize: 14, fontWeight: 700, cursor: loading ? 'not-allowed' : 'pointer', transition: 'all 0.2s', flexShrink: 0, whiteSpace: 'nowrap' }}>
              {loading ? '⟳ Building' : '▶ Build'}
            </button>
          </div>

          {/* ── Prompt Template Library ── */}
          {!hasExecuted && (
            <div style={{ marginTop: 16, textAlign: 'left' }}>
              <div style={{ fontSize: 10, color: '#4A5280', textTransform: 'uppercase', letterSpacing: '0.12em', marginBottom: 10, paddingLeft: 2 }}>⚡ Quick Start Templates</div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
                {PROMPT_TEMPLATES.map((t) => (
                  <button key={t.label} onClick={() => { setGoal(t.prompt); setWorkflow(t.workflow); }}
                    style={{
                      padding: '10px 12px', borderRadius: 10, border: `1px solid ${t.color}20`,
                      background: `${t.color}08`, cursor: 'pointer', textAlign: 'left',
                      transition: 'all 0.2s', outline: 'none',
                    }}
                    onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = `${t.color}18`; (e.currentTarget as HTMLElement).style.borderColor = `${t.color}40`; (e.currentTarget as HTMLElement).style.transform = 'translateY(-1px)'; }}
                    onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = `${t.color}08`; (e.currentTarget as HTMLElement).style.borderColor = `${t.color}20`; (e.currentTarget as HTMLElement).style.transform = 'none'; }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3 }}>
                      <span style={{ fontSize: 14 }}>{t.icon}</span>
                      <span style={{ fontSize: 11, fontWeight: 700, color: t.color }}>{t.label}</span>
                    </div>
                    <div style={{ fontSize: 10, color: '#4A5280', lineHeight: 1.4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {t.prompt.slice(0, 50)}…
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* ── Multi-Agent Pipeline Builder ── */}
          {!hasExecuted && (
            <div style={{ marginTop: 16, padding: '14px 16px', borderRadius: 12, background: 'rgba(123,47,255,0.06)', border: '1px solid rgba(123,47,255,0.15)', textAlign: 'left' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontSize: 14 }}>🔗</span>
                  <span style={{ fontSize: 12, fontWeight: 700, color: '#7B2FFF' }}>Multi-Agent Pipeline</span>
                  <span style={{ fontSize: 10, color: '#4A5280' }}>· chain agents sequentially</span>
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
                {PIPELINE_AGENTS.map((a, i) => (
                  <div key={a.id} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <div style={{
                      display: 'flex', alignItems: 'center', gap: 5, padding: '5px 10px',
                      borderRadius: 8, background: `${a.color}12`, border: `1px solid ${a.color}25`,
                    }}>
                      <span style={{ fontSize: 12 }}>{a.icon}</span>
                      <span style={{ fontSize: 11, color: a.color, fontWeight: 600 }}>{a.label}</span>
                    </div>
                    {i < PIPELINE_AGENTS.length - 1 && (
                      <span style={{ color: '#2A3060', fontSize: 14 }}>→</span>
                    )}
                  </div>
                ))}
                <button
                  onClick={() => { setWorkflow('coding'); if (goal.trim()) handleExecute(); else setGoal('Build a complete web application with authentication, dashboard, and REST API'); }}
                  style={{
                    marginLeft: 8, padding: '5px 14px', borderRadius: 8,
                    background: 'linear-gradient(135deg,#7B2FFF,#00D4FF)',
                    border: 'none', color: '#fff', fontSize: 11, fontWeight: 700,
                    cursor: 'pointer',
                  }}
                >▶ Run Full Pipeline</button>
              </div>
            </div>
          )}

          {/* ── Pending terminal while building ── */}
          {hasExecuted && !buildResult && (
            <PendingTerminal lines={execLines} loading={loading} />
          )}

          {/* ── Build output (shown after completion) ── */}
          {buildResult && (
            <div style={{ animation: 'fadeIn 0.4s ease', textAlign: 'left' }}>
              {/* Show completion line */}
              <div style={{ fontFamily: 'JetBrains Mono', fontSize: 12, color: '#00FF9D', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
                <span>✓</span>
                <span>{execLines.find(l => l.type === 'success')?.text}</span>
              </div>
              <BuildOutput result={buildResult} goal={goal} elapsed={elapsed} />
            </div>
          )}

          {!hasExecuted && (
            <div style={{ fontSize: 12, color: '#2A3060', marginTop: 8 }}>
              Press Enter or click Build · The result will be shown with live preview below
            </div>
          )}
        </div>
      </div>

      {/* ── Metrics + Actions ── */}
      <div style={{ padding: '28px 32px 16px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 14, marginBottom: 28 }}>
          {[
            { label: 'Agents', value: supervisor.agent_count ?? '—', sub: 'registered', color: '#00D4FF' },
            { label: 'Tasks Executed', value: supervisor.task_count ?? '—', sub: 'total runs', color: '#7B2FFF' },
            { label: 'Processes', value: supervisor.process_count ?? '—', sub: 'tracked', color: '#00FF9D' },
            { label: 'Status', value: supervisor.status ? 'ONLINE' : '—', sub: 'kernel health', color: '#00FF9D' },
          ].map(({ label, value, sub, color }) => (
            <div key={label} style={{ borderRadius: 14, padding: '18px 20px', border: '1px solid rgba(255,255,255,0.07)', background: 'rgba(255,255,255,0.02)' }}>
              <div style={{ fontSize: 10, color: '#4A5280', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 6 }}>{label}</div>
              <div style={{ fontSize: 28, fontFamily: 'Space Grotesk', fontWeight: 700, color, marginBottom: 2 }}>{value}</div>
              <div style={{ fontSize: 11, color: '#4A5280' }}>{sub}</div>
            </div>
          ))}
        </div>

        <div style={{ fontSize: 11, color: '#4A5280', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 14 }}>Quick Navigation</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(185px, 1fr))', gap: 12 }}>
          <QuickAction href="/dashboard"   icon="◈" label="Mission Control"  desc="Live system overview + event stream" color="#00D4FF" />
          <QuickAction href="/showrunner"  icon="🎬" label="Showrunner"       desc="AI movie generation pipeline" color="#7B2FFF" />
          <QuickAction href="/agents"      icon="◉" label="Agent Fleet"      desc="All 22 agents + capabilities" color="#00FF9D" />
          <QuickAction href="/processes"   icon="▣" label="Process Manager"  desc="Live task manager for AI jobs" color="#FFB800" />
          <QuickAction href="/memory"      icon="⬡" label="Memory Explorer"  desc="Inspect shared agent memory" color="#00D4FF" />
          <QuickAction href="/checkpoints" icon="◎" label="Checkpoints"      desc="Restore points + history" color="#FF3D71" />
        </div>
      </div>
    </AppShell>
  );
}
