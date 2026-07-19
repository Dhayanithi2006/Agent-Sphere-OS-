'use client';

import { useEffect, useState, useRef } from 'react';
import AppShell from '@/components/AppShell';

const API = 'http://localhost:8000';

const STAGES = [
  { id: 'showrunner_planner',    label: 'Planner',    icon: '◈' },
  { id: 'showrunner_parallel',   label: 'Research',   icon: '◉' },
  { id: 'showrunner_script',     label: 'Script',     icon: '✍' },
  { id: 'showrunner_storyboard', label: 'Storyboard', icon: '⬡' },
  { id: 'showrunner_scene',      label: 'Scene Gen',  icon: '◐' },
  { id: 'showrunner_prompt',     label: 'Prompts',    icon: '⊕' },
  { id: 'showrunner_voice',      label: 'Voice',      icon: '◎' },
  { id: 'showrunner_video',      label: 'Video',      icon: '▷' },
  { id: 'showrunner_subtitle',   label: 'Subtitles',  icon: '≡' },
  { id: 'showrunner_editor',     label: 'Editor',     icon: '◈' },
  { id: 'showrunner_poster',     label: 'Poster',     icon: '◇' },
  { id: 'showrunner_reviewer',   label: 'Reviewer',   icon: '◉' },
  { id: 'showrunner_reporter',   label: 'Reporter',   icon: '◬' },
];

interface LiveEvent {
  time: string;
  agent: string;
  message: string;
  type: 'start' | 'progress' | 'complete' | 'error' | 'info';
}

interface AgentOutput {
  agent_id: string;
  name: string;
  result: string;
  status: string;
}

interface ShowrunnerStatus {
  status?: string;
  current_agent?: string;
  current_model?: string;   // e.g. "qwen3.7-max", "wan2.1-t2v-turbo"
  progress?: string;
  movie_goal?: string;
  approval_state?: string;
  timeline?: string[];
  storyboard?: any[];
  review_report?: string;
  final_movie?: string;
  type?: string;
  user?: string;
  agents_metrics?: Record<string, any>;
  cost_breakdown?: Record<string, number>;
}

function StageNode({ stage, state, pulse }: { stage: typeof STAGES[0]; state: 'idle'|'running'|'done'|'pending'; pulse: boolean }) {
  const styles = {
    idle:    { bg: 'rgba(255,255,255,0.03)', border: 'rgba(255,255,255,0.08)', color: '#2A3060' },
    pending: { bg: 'rgba(255,184,0,0.06)',   border: 'rgba(255,184,0,0.2)',    color: '#FFB800' },
    running: { bg: 'rgba(0,212,255,0.1)',    border: 'rgba(0,212,255,0.4)',    color: '#00D4FF' },
    done:    { bg: 'rgba(0,255,157,0.08)',   border: 'rgba(0,255,157,0.3)',    color: '#00FF9D' },
  };
  const s = styles[state];
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6, minWidth: 72 }}>
      <div style={{ width: 48, height: 48, borderRadius: 14, background: s.bg, border: `1.5px solid ${s.border}`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: state === 'done' ? 18 : 16, color: s.color, position: 'relative', boxShadow: state === 'running' ? `0 0 16px ${s.border}` : state === 'done' ? '0 0 8px rgba(0,255,157,0.2)' : 'none', transition: 'all 0.4s ease' }}>
        {state === 'done' ? '✓' : stage.icon}
        {state === 'running' && <div style={{ position: 'absolute', inset: -3, borderRadius: 17, border: '2px solid transparent', borderTopColor: '#00D4FF', animation: 'spin 1s linear infinite' }} />}
      </div>
      <span style={{ fontSize: 9, color: s.color === '#2A3060' ? '#2A3060' : s.color, fontFamily: 'JetBrains Mono', textAlign: 'center', opacity: state === 'idle' ? 0.4 : 1 }}>{stage.label}</span>
    </div>
  );
}

function LogRow({ event }: { event: LiveEvent }) {
  const typeColor = { start: '#7B2FFF', progress: '#00D4FF', complete: '#00FF9D', error: '#FF3D71', info: '#4A5280' }[event.type] || '#4A5280';
  // Extract model badge from message if present
  const modelMatch = event.message.match(/\(model:\s*([^)]+)\)/i);
  const modelBadge = modelMatch ? modelMatch[1] : null;
  const cleanMsg = modelBadge ? event.message.replace(modelMatch![0], '').trim() : event.message;
  return (
    <div style={{ display: 'flex', gap: 10, padding: '7px 16px', borderBottom: '1px solid rgba(255,255,255,0.03)', alignItems: 'flex-start', animation: 'fadeIn 0.3s ease' }}>
      <span style={{ fontSize: 10, color: '#2A3060', fontFamily: 'JetBrains Mono', flexShrink: 0, paddingTop: 1 }}>{event.time}</span>
      <span style={{ fontSize: 10, fontFamily: 'JetBrains Mono', color: typeColor, flexShrink: 0, paddingTop: 1, minWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{event.agent}</span>
      <span style={{ fontSize: 12, color: '#8892B0', lineHeight: 1.5, flex: 1 }}>{cleanMsg}</span>
      {modelBadge && (
        <span style={{ flexShrink: 0, fontSize: 9, fontFamily: 'JetBrains Mono', color: '#7B2FFF', background: 'rgba(123,47,255,0.12)', border: '1px solid rgba(123,47,255,0.25)', borderRadius: 4, padding: '1px 6px', whiteSpace: 'nowrap', alignSelf: 'center' }}>
          {modelBadge}
        </span>
      )}
    </div>
  );
}

// ── Result display tabs ────────────────────────────────────────────────────────
function ResultPanel({ status, agentOutputs }: { status: ShowrunnerStatus; agentOutputs: AgentOutput[] }) {
  const [tab, setTab] = useState<'report'|'script'|'agents'|'cost'>('report');

  const TABS = [
    { id: 'report', label: '📄 Production Report' },
    { id: 'script', label: '✍ Script & Story' },
    { id: 'agents', label: '🤖 Agent Outputs' },
    { id: 'cost',   label: '💰 Cost Breakdown' },
  ] as const;

  return (
    <div style={{ borderRadius: 16, border: '1px solid rgba(0,255,157,0.2)', background: 'rgba(0,255,157,0.02)', overflow: 'hidden', animation: 'fadeIn 0.5s ease' }}>
      {/* Header */}
      <div style={{ padding: '16px 20px', borderBottom: '1px solid rgba(0,255,157,0.1)', background: 'rgba(0,255,157,0.04)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>🎬</span>
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, color: '#00FF9D' }}>Production Complete</div>
            <div style={{ fontSize: 11, color: '#4A5280' }}>{status.movie_goal} · {status.type}</div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <a href={`${API}/api/showrunner/status`} target="_blank" rel="noreferrer"
            style={{ padding: '6px 14px', background: 'rgba(123,47,255,0.15)', border: '1px solid rgba(123,47,255,0.3)', borderRadius: 8, color: '#7B2FFF', fontSize: 12, textDecoration: 'none', fontWeight: 600 }}>
            ⬇ Download JSON
          </a>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
        {TABS.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            style={{ padding: '10px 16px', background: 'none', border: 'none', borderBottom: tab === t.id ? '2px solid #00FF9D' : '2px solid transparent', color: tab === t.id ? '#00FF9D' : '#4A5280', fontSize: 12, cursor: 'pointer', fontFamily: 'inherit', transition: 'all 0.2s', marginBottom: -1 }}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab body */}
      <div style={{ padding: 20, maxHeight: 420, overflowY: 'auto' }}>

        {tab === 'report' && (
          <div>
            {status.review_report ? (
              <pre style={{ fontFamily: 'JetBrains Mono', fontSize: 12, color: '#CDD6F4', lineHeight: 1.7, whiteSpace: 'pre-wrap', margin: 0 }}>
                {status.review_report}
              </pre>
            ) : (
              <div style={{ fontFamily: 'JetBrains Mono', fontSize: 12, color: '#CDD6F4', lineHeight: 1.8 }}>
                <div style={{ color: '#00FF9D', fontWeight: 700, fontSize: 14, marginBottom: 12 }}>✓ {status.type} Production Complete</div>
                <div style={{ color: '#FFB800', marginBottom: 6 }}>Goal: {status.movie_goal}</div>
                <div style={{ color: '#4A5280', marginBottom: 4 }}>User: {status.user || 'User'}</div>
                <div style={{ color: '#4A5280', marginBottom: 16 }}>Pipeline: All {STAGES.length} stages completed successfully</div>
                <div style={{ color: '#8892B0', lineHeight: 1.9 }}>
                  {(status.timeline || []).map((line, i) => (
                    <div key={i} style={{ paddingLeft: 12, borderLeft: '2px solid rgba(0,255,157,0.2)', marginBottom: 4 }}>
                      {line}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {tab === 'script' && (
          <div>
            {agentOutputs.filter(a => a.agent_id.includes('script') || a.agent_id.includes('storyboard') || a.agent_id.includes('planner')).map(a => (
              <div key={a.agent_id} style={{ marginBottom: 20 }}>
                <div style={{ fontSize: 11, color: '#00D4FF', fontFamily: 'JetBrains Mono', marginBottom: 8, textTransform: 'uppercase' }}>
                  {a.name}
                </div>
                <pre style={{ fontFamily: 'JetBrains Mono', fontSize: 12, color: '#CDD6F4', lineHeight: 1.7, whiteSpace: 'pre-wrap', background: 'rgba(255,255,255,0.02)', padding: 12, borderRadius: 8, border: '1px solid rgba(255,255,255,0.06)', margin: 0 }}>
                  {a.result || '(No output captured)'}
                </pre>
              </div>
            ))}
            {agentOutputs.filter(a => a.agent_id.includes('script') || a.agent_id.includes('storyboard') || a.agent_id.includes('planner')).length === 0 && (
              <div style={{ color: '#4A5280', fontSize: 13, fontFamily: 'JetBrains Mono' }}>
                Agent output data is stored in shared memory. The full script and storyboard were processed by the pipeline.
                <br /><br />Check the <b>Agent Outputs</b> tab for all captured results.
              </div>
            )}
          </div>
        )}

        {tab === 'agents' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {agentOutputs.length === 0 && (
              <div style={{ color: '#4A5280', fontSize: 13, fontFamily: 'JetBrains Mono' }}>
                Loading agent outputs...
              </div>
            )}
            {agentOutputs.map(a => (
              <div key={a.agent_id} style={{ borderRadius: 10, border: '1px solid rgba(255,255,255,0.07)', overflow: 'hidden' }}>
                <div style={{ padding: '8px 14px', background: 'rgba(255,255,255,0.03)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 11, fontFamily: 'JetBrains Mono', color: '#00D4FF' }}>{a.name}</span>
                  <span style={{ fontSize: 10, color: a.status === 'completed' ? '#00FF9D' : '#FF3D71', fontFamily: 'JetBrains Mono' }}>{a.status}</span>
                </div>
                {a.result && (
                  <pre style={{ padding: 12, fontFamily: 'JetBrains Mono', fontSize: 11, color: '#8892B0', lineHeight: 1.6, whiteSpace: 'pre-wrap', margin: 0, maxHeight: 150, overflowY: 'auto' }}>
                    {a.result.substring(0, 800)}{a.result.length > 800 ? '\n...(truncated)' : ''}
                  </pre>
                )}
              </div>
            ))}
          </div>
        )}

        {tab === 'cost' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, marginBottom: 8 }}>
              {Object.entries(status.cost_breakdown || {}).filter(([k]) => k !== 'total').map(([key, val]) => (
                <div key={key} style={{ borderRadius: 10, padding: '12px 14px', border: '1px solid rgba(255,255,255,0.07)', background: 'rgba(255,255,255,0.02)' }}>
                  <div style={{ fontSize: 10, color: '#4A5280', textTransform: 'uppercase', marginBottom: 4 }}>{key}</div>
                  <div style={{ fontSize: 18, fontFamily: 'Space Grotesk', fontWeight: 700, color: '#FFB800' }}>${(Number(val) || 0).toFixed(4)}</div>
                </div>
              ))}
            </div>
            <div style={{ borderRadius: 10, padding: '14px 16px', border: '1px solid rgba(0,255,157,0.2)', background: 'rgba(0,255,157,0.04)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 13, color: '#00FF9D', fontWeight: 600 }}>Total Pipeline Cost</span>
              <span style={{ fontSize: 24, fontFamily: 'Space Grotesk', fontWeight: 700, color: '#00FF9D' }}>
                ${(Number(status.cost_breakdown?.total) || 0).toFixed(4)}
              </span>
            </div>
            <div style={{ fontSize: 11, color: '#2A3060', textAlign: 'center' }}>Powered by Qwen Cloud API</div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function ShowrunnerPage() {
  const [goal, setGoal] = useState('');
  const [mediaType, setMediaType] = useState('Short Film');
  const [launching, setLaunching] = useState(false);
  const [status, setStatus] = useState<ShowrunnerStatus>({});
  const [liveEvents, setLiveEvents] = useState<LiveEvent[]>([]);
  const [approving, setApproving] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [agentOutputs, setAgentOutputs] = useState<AgentOutput[]>([]);
  const [elapsed, setElapsed] = useState(0);
  const [startTime, setStartTime] = useState<number | null>(null);
  const logEndRef = useRef<HTMLDivElement>(null);
  const prevAgentRef = useRef('');
  const prevProgressRef = useRef('');
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── Poll showrunner status ──────────────────────────────────────────────────
  useEffect(() => {
    const poll = async () => {
      try {
        const r = await fetch(`${API}/api/showrunner/status`);
        const data: ShowrunnerStatus = await r.json();
        setStatus(data);

        const now = new Date().toLocaleTimeString('en-US', { hour12: false });
        const agent = data.current_agent || '';
        const progress = data.progress || '';
        const model = data.current_model || '';

        if (agent && agent !== prevAgentRef.current) {
          prevAgentRef.current = agent;
          const modelHint = model ? ` (model: ${model})` : '';
          setLiveEvents(prev => [...prev.slice(-200), { time: now, agent, message: `Agent activated${modelHint}`, type: 'start' }]);
        }
        if (progress && progress !== prevProgressRef.current) {
          prevProgressRef.current = progress;
          setLiveEvents(prev => [...prev.slice(-200), { time: now, agent: agent || 'kernel', message: progress, type: 'progress' }]);
        }
        if (data.status === 'completed' && prevProgressRef.current !== 'DONE') {
          prevProgressRef.current = 'DONE';
          setLiveEvents(prev => [...prev, { time: now, agent: 'reporter', message: 'Pipeline complete! All agents finished.', type: 'complete' }]);
          // Stop elapsed timer
          if (timerRef.current) clearInterval(timerRef.current);
        }
      } catch {}
    };
    poll();
    const t = setInterval(poll, 1500);
    return () => clearInterval(t);
  }, []);

  // ── When completed, load agent task results ────────────────────────────────
  useEffect(() => {
    if (status.status !== 'completed') return;
    const loadResults = async () => {
      try {
        const tasks = await fetch(`${API}/tasks`).then(r => r.json()) as any[];
        const LABEL_MAP: Record<string, string> = {
          showrunner_planner: 'Movie Planner', showrunner_script: 'Scriptwriter',
          showrunner_storyboard: 'Storyboard Artist', showrunner_scene: 'Scene Generator',
          showrunner_voice: 'Voice Director', showrunner_video: 'Video Producer',
          showrunner_subtitle: 'Subtitle Writer', showrunner_editor: 'Editor',
          showrunner_poster: 'Poster Designer', showrunner_reviewer: 'QA Reviewer',
          showrunner_reporter: 'Production Reporter', showrunner_researcher: 'Researcher',
          planner: 'Planning Agent',
        };
        const outputs: AgentOutput[] = tasks
          .filter(t => t.agent_id?.startsWith('showrunner') || t.agent_id === 'planner')
          .map(t => ({
            agent_id: t.agent_id,
            name: LABEL_MAP[t.agent_id] || t.agent_id,
            result: t.result || '',
            status: t.status || 'unknown',
          }));
        setAgentOutputs(outputs);
      } catch {}
    };
    loadResults();
  }, [status.status]);

  // ── Auto-scroll log ─────────────────────────────────────────────────────────
  useEffect(() => { logEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [liveEvents]);

  // ── Launch pipeline ─────────────────────────────────────────────────────────
  const handleLaunch = async () => {
    if (!goal.trim()) { setErrorMsg('Please enter a movie concept'); return; }
    setLaunching(true);
    setErrorMsg('');
    setAgentOutputs([]);
    setElapsed(0);
    prevAgentRef.current = '';
    prevProgressRef.current = '';
    setLiveEvents([{ time: new Date().toLocaleTimeString('en-US', { hour12: false }), agent: 'kernel', message: `Launching "${goal}" (model: qwen3.7-max → Model Router)`, type: 'start' }]);

    // Start elapsed timer
    const t0 = Date.now();
    setStartTime(t0);
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = setInterval(() => setElapsed(Math.floor((Date.now() - t0) / 1000)), 1000);

    try {
      const r = await fetch(`${API}/api/showrunner/generate`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ movie_goal: goal, user: 'User', type: mediaType }),
      });
      if (!r.ok) throw new Error(`API error: ${r.status}`);
      const data = await r.json();
      setLiveEvents(prev => [...prev, { time: new Date().toLocaleTimeString('en-US', { hour12: false }), agent: 'kernel', message: data.message || 'Pipeline started', type: 'info' }]);
    } catch (e: any) { setErrorMsg(e.message); }
    finally { setLaunching(false); }
  };

  const getStageState = (id: string): 'idle'|'running'|'done'|'pending' => {
    const cur = status.current_agent || '';
    const timeline: string[] = (status.timeline || []).map((t: any) => String(t));
    const isDone = status.status === 'completed';
    const isRunning = status.status === 'running';
    if (isDone) return 'done';
    if (timeline.some(line => line.toLowerCase().includes(id.replace('showrunner_','')))) return 'done';
    if (cur.includes(id) || id.includes(cur)) return 'running';
    if (isRunning) return 'pending';
    return 'idle';
  };

  const doneCount = STAGES.filter(s => getStageState(s.id) === 'done').length;
  const isRunning = status.status === 'running';
  const isCompleted = status.status === 'completed';
  const needsApproval = status.approval_state === 'pending';
  const progress = isCompleted ? 100 : doneCount > 0 ? Math.round((doneCount / STAGES.length) * 100) : 0;

  return (
    <AppShell>
      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }
        @keyframes pulse-border { 0%,100% { border-color: rgba(0,212,255,0.3); } 50% { border-color: rgba(0,212,255,0.7); box-shadow: 0 0 20px rgba(0,212,255,0.2); } }
      `}</style>

      <div style={{ padding: '24px 28px', display: 'flex', flexDirection: 'column', gap: 16, height: 'calc(100vh - 48px)', overflowY: 'auto' }}>

        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ width: 40, height: 40, borderRadius: 12, background: 'linear-gradient(135deg, #7B2FFF, #00D4FF)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18, boxShadow: '0 0 16px rgba(123,47,255,0.4)' }}>🎬</div>
            <div>
              <h1 style={{ fontFamily: 'Space Grotesk, sans-serif', fontSize: 24, fontWeight: 700, color: '#F0F4FF', margin: 0 }}>Showrunner Studio</h1>
              <p style={{ color: '#4A5280', fontSize: 12, margin: 0 }}>AI-powered {mediaType.toLowerCase()} pipeline · Qwen Cloud</p>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 10 }}>
            {isRunning && <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '5px 14px', background: 'rgba(0,212,255,0.08)', border: '1px solid rgba(0,212,255,0.25)', borderRadius: 100, fontSize: 11, color: '#00D4FF', animation: 'pulse-border 2s infinite' }}>
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#00D4FF', boxShadow: '0 0 6px #00D4FF', display: 'inline-block' }} />
              PIPELINE RUNNING
            </div>}
            {isCompleted && <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '5px 14px', background: 'rgba(0,255,157,0.08)', border: '1px solid rgba(0,255,157,0.25)', borderRadius: 100, fontSize: 11, color: '#00FF9D' }}>✓ COMPLETED</div>}
          </div>
        </div>

        {/* Launch bar */}
        <div className="glass" style={{ borderRadius: 16, padding: '16px 20px', border: '1px solid rgba(123,47,255,0.2)', background: 'rgba(123,47,255,0.03)' }}>
          <div style={{ fontSize: 11, color: '#4A5280', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 10 }}>Launch New Pipeline</div>
          <div style={{ display: 'flex', gap: 10 }}>
            <input value={goal} onChange={e => setGoal(e.target.value)} onKeyDown={e => e.key === 'Enter' && handleLaunch()}
              placeholder="Enter your concept — e.g. A short film about AI awakening on Mars..."
              style={{ flex: 1, background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 10, padding: '10px 14px', color: '#F0F4FF', fontSize: 14, outline: 'none' }} />
            <select value={mediaType} onChange={e => setMediaType(e.target.value)}
              style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 10, padding: '10px 14px', color: '#F0F4FF', fontSize: 13, outline: 'none', cursor: 'pointer' }}>
              <option value="Short Film">Short Film</option>
              <option value="Movie">Movie</option>
              <option value="Documentary">Documentary</option>
              <option value="Commercial">Commercial</option>
              <option value="Podcast">Podcast</option>
            </select>
            <button onClick={handleLaunch} disabled={launching || isRunning}
              style={{ padding: '10px 22px', background: launching || isRunning ? 'rgba(123,47,255,0.2)' : 'linear-gradient(135deg, #7B2FFF, #00D4FF)', border: 'none', borderRadius: 10, color: '#fff', fontSize: 14, fontWeight: 700, cursor: launching || isRunning ? 'not-allowed' : 'pointer', whiteSpace: 'nowrap', transition: 'all 0.2s' }}>
              {launching ? '⟳ Launching...' : isRunning ? '⟳ Running...' : '▷ Launch'}
            </button>
          </div>
          {errorMsg && <div style={{ marginTop: 8, fontSize: 12, color: '#FF3D71', padding: '6px 10px', background: 'rgba(255,61,113,0.08)', borderRadius: 6 }}>{errorMsg}</div>}
        </div>

        {/* Pipeline + Live Feed */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: 16 }}>

          {/* Left column */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

            {/* Stage nodes */}
            <div className="glass" style={{ borderRadius: 16, padding: '20px', border: '1px solid rgba(255,255,255,0.07)' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
                <span style={{ fontSize: 11, color: '#4A5280', textTransform: 'uppercase', letterSpacing: '0.1em' }}>Production Pipeline</span>
                <span style={{ fontSize: 11, color: '#4A5280', fontFamily: 'JetBrains Mono' }}>{doneCount}/{STAGES.length} stages</span>
              </div>
              <div style={{ display: 'flex', overflowX: 'auto', gap: 4, paddingBottom: 4 }}>
                {STAGES.map((stage, i) => (
                  <div key={stage.id} style={{ display: 'flex', alignItems: 'center' }}>
                    <StageNode stage={stage} state={getStageState(stage.id)} pulse={isRunning} />
                    {i < STAGES.length - 1 && <div style={{ width: 16, height: 2, flexShrink: 0, marginBottom: 20, background: getStageState(STAGES[i+1].id) === 'done' ? '#00FF9D' : getStageState(stage.id) === 'done' ? 'rgba(0,212,255,0.3)' : 'rgba(255,255,255,0.05)', transition: 'background 0.5s' }} />}
                  </div>
                ))}
              </div>
              {(isRunning || isCompleted || doneCount > 0) && (
                <div style={{ marginTop: 16 }}>
                  <div style={{ height: 4, borderRadius: 2, background: 'rgba(255,255,255,0.05)', overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${progress}%`, background: isCompleted ? '#00FF9D' : 'linear-gradient(90deg, #7B2FFF, #00D4FF)', borderRadius: 2, transition: 'width 0.8s ease', boxShadow: isRunning ? '0 0 8px rgba(0,212,255,0.5)' : 'none' }} />
                  </div>
                  <div style={{ marginTop: 6, fontSize: 11, color: '#4A5280', display: 'flex', justifyContent: 'space-between' }}>
                    <span>{status.progress || 'Initializing...'}</span>
                    <span style={{ color: isCompleted ? '#00FF9D' : '#00D4FF' }}>{progress}%</span>
                  </div>
                </div>
              )}
            </div>

            {/* Human approval gate */}
            {needsApproval && (
              <div className="glass" style={{ borderRadius: 16, padding: '20px', border: '1px solid rgba(255,184,0,0.3)', background: 'rgba(255,184,0,0.04)', animation: 'pulse-border 2s infinite' }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: '#FFB800', marginBottom: 8 }}>⚠ Human Approval Required</div>
                <div style={{ fontSize: 12, color: '#8892B0', marginBottom: 16 }}>The Storyboard agent has completed and is awaiting your review before video generation.</div>
                <div style={{ display: 'flex', gap: 10 }}>
                  <button onClick={async () => { setApproving(true); await fetch(`${API}/api/showrunner/approve`, { method: 'POST', headers: {'Content-Type':'application/json'}, body: '{}' }); setApproving(false); }}
                    disabled={approving}
                    style={{ padding: '9px 20px', background: 'rgba(0,255,157,0.15)', border: '1px solid rgba(0,255,157,0.3)', borderRadius: 10, color: '#00FF9D', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>
                    {approving ? '...' : '✓ Approve — Continue Pipeline'}
                  </button>
                  <button onClick={async () => await fetch(`${API}/api/showrunner/reject`, { method: 'POST', headers: {'Content-Type':'application/json'}, body: '{}' })}
                    style={{ padding: '9px 20px', background: 'rgba(255,61,113,0.1)', border: '1px solid rgba(255,61,113,0.25)', borderRadius: 10, color: '#FF3D71', fontSize: 13, cursor: 'pointer' }}>
                    ✗ Reject
                  </button>
                </div>
              </div>
            )}

            {/* ── RESULT PANEL — shows when completed ── */}
            {isCompleted && (
              <ResultPanel status={status} agentOutputs={agentOutputs} />
            )}

            {/* Current goal chip */}
            {status.movie_goal && !isCompleted && (
              <div className="glass" style={{ borderRadius: 14, padding: '14px 18px', border: '1px solid rgba(255,255,255,0.07)' }}>
                <div style={{ fontSize: 10, color: '#4A5280', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 6 }}>Current Goal</div>
                <div style={{ fontSize: 14, color: '#F0F4FF' }}>{status.movie_goal}</div>
                <div style={{ fontSize: 11, color: '#4A5280', marginTop: 4 }}>Type: {status.type || '—'} · User: {status.user || '—'}</div>
              </div>
            )}
          </div>

          {/* Right: Live Activity Feed */}
          <div className="glass" style={{ borderRadius: 16, border: '1px solid rgba(255,255,255,0.07)', display: 'flex', flexDirection: 'column', overflow: 'hidden', maxHeight: 620 }}>
            <div style={{ padding: '14px 16px', borderBottom: '1px solid rgba(255,255,255,0.06)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0 }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: '#F0F4FF' }}>Live Activity</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                {isRunning && <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#00D4FF', boxShadow: '0 0 6px #00D4FF', display: 'inline-block' }} />}
                <span style={{ fontSize: 10, color: '#4A5280', fontFamily: 'JetBrains Mono' }}>{liveEvents.length} events</span>
              </div>
            </div>
            {status.current_agent && isRunning && (
              <div style={{ padding: '10px 16px', borderBottom: '1px solid rgba(255,255,255,0.05)', background: 'rgba(0,212,255,0.04)', flexShrink: 0 }}>
                <div style={{ fontSize: 10, color: '#4A5280', marginBottom: 3 }}>CURRENTLY RUNNING</div>
                <div style={{ fontSize: 13, color: '#00D4FF', fontFamily: 'JetBrains Mono', fontWeight: 600 }}>{status.current_agent}</div>
                {/* Model + Elapsed display */}
                <div style={{ display: 'flex', gap: 12, marginTop: 6, flexWrap: 'wrap' }}>
                  {status.current_model && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                      <span style={{ fontSize: 9, color: '#4A5280', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Model</span>
                      <span style={{ fontSize: 10, fontFamily: 'JetBrains Mono', color: '#7B2FFF', background: 'rgba(123,47,255,0.12)', border: '1px solid rgba(123,47,255,0.3)', borderRadius: 4, padding: '1px 7px' }}>
                        {status.current_model}
                      </span>
                    </div>
                  )}
                  {isRunning && startTime !== null && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                      <span style={{ fontSize: 9, color: '#4A5280', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Elapsed</span>
                      <span style={{ fontSize: 10, fontFamily: 'JetBrains Mono', color: '#FFB800' }}>{elapsed}s</span>
                    </div>
                  )}
                </div>
              </div>
            )}
            <div style={{ flex: 1, overflowY: 'auto' }}>
              {liveEvents.length === 0 ? (
                <div style={{ padding: 40, textAlign: 'center', color: '#2A3060', fontSize: 13 }}>
                  <div style={{ fontSize: 28, marginBottom: 10 }}>◈</div>
                  Launch a pipeline to see real-time agent activity
                </div>
              ) : liveEvents.map((ev, i) => <LogRow key={i} event={ev} />)}
              <div ref={logEndRef} />
            </div>
            {liveEvents.length > 0 && (
              <div style={{ padding: '8px 16px', borderTop: '1px solid rgba(255,255,255,0.05)', flexShrink: 0 }}>
                <button onClick={() => setLiveEvents([])} style={{ background: 'none', border: 'none', color: '#4A5280', fontSize: 11, cursor: 'pointer', fontFamily: 'JetBrains Mono' }}>Clear log</button>
              </div>
            )}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
