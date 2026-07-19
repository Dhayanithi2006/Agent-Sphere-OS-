'use client';

/**
 * GlobalLiveFeed — always-visible real-time activity strip at the bottom.
 * Shows: current running agent, last event, and live process count.
 * Polls /stream (SSE) and /api/showrunner/status.
 */

import { useEffect, useState, useRef } from 'react';

const API = 'http://localhost:8000';

interface Activity {
  agent: string;
  message: string;
  time: string;
  color: string;
}

export default function GlobalLiveFeed() {
  const [activities, setActivities] = useState<Activity[]>([]);
  const [runningCount, setRunningCount] = useState(0);
  const [currentAgent, setCurrentAgent] = useState('');
  const [showrunnerProgress, setShowrunnerProgress] = useState('');
  const prevDataRef = useRef('');

  useEffect(() => {
    const poll = async () => {
      try {
        // Processes
        const pr = await fetch(`${API}/processes`, { signal: AbortSignal.timeout(3000) });
        const procs: any[] = await pr.json();
        const running = procs.filter(p => p.current_state === 'running');
        setRunningCount(running.length);

        // Showrunner status
        const sr = await fetch(`${API}/api/showrunner/status`, { signal: AbortSignal.timeout(3000) });
        const sv = await sr.json();
        const newKey = `${sv.current_agent}|${sv.progress}|${running.map(p => p.pid).join(',')}`;
        if (newKey === prevDataRef.current) return;
        prevDataRef.current = newKey;

        const now = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });

        if (sv.current_agent) setCurrentAgent(sv.current_agent);
        if (sv.progress) setShowrunnerProgress(sv.progress);

        const newActivities: Activity[] = [];

        running.slice(0, 3).forEach(p => {
          if (p.agent && p.current_task) {
            newActivities.push({
              agent: p.agent,
              message: p.current_task,
              time: now,
              color: '#00D4FF',
            });
          }
        });

        if (sv.current_agent && sv.progress && sv.status === 'running') {
          newActivities.push({
            agent: sv.current_agent,
            message: sv.progress,
            time: now,
            color: '#7B2FFF',
          });
        }

        if (newActivities.length > 0) {
          setActivities(prev => [...newActivities, ...prev].slice(0, 8));
        }
      } catch {}
    };

    poll();
    const t = setInterval(poll, 2000);
    return () => clearInterval(t);
  }, []);

  if (activities.length === 0 && runningCount === 0) return null;

  return (
    <div
      style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        zIndex: 50,
        background: 'rgba(5,5,18,0.95)',
        backdropFilter: 'blur(20px)',
        borderTop: '1px solid rgba(0,212,255,0.1)',
        height: 36,
        display: 'flex',
        alignItems: 'center',
        gap: 0,
        overflow: 'hidden',
      }}
    >
      {/* Status badge */}
      <div style={{
        padding: '0 14px',
        borderRight: '1px solid rgba(255,255,255,0.06)',
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        flexShrink: 0,
        height: '100%',
      }}>
        {runningCount > 0 ? (
          <>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#00D4FF', boxShadow: '0 0 6px #00D4FF', display: 'inline-block' }} />
            <span style={{ fontSize: 10, fontFamily: 'JetBrains Mono', color: '#00D4FF', whiteSpace: 'nowrap' }}>
              {runningCount} RUNNING
            </span>
          </>
        ) : (
          <>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#00FF9D', display: 'inline-block' }} />
            <span style={{ fontSize: 10, fontFamily: 'JetBrains Mono', color: '#4A5280' }}>IDLE</span>
          </>
        )}
      </div>

      {/* Scrolling activity ticker */}
      <div style={{ flex: 1, overflow: 'hidden', display: 'flex', alignItems: 'center', padding: '0 12px' }}>
        <div
          style={{
            display: 'flex',
            gap: 32,
            animation: activities.length > 2 ? 'ticker 20s linear infinite' : 'none',
            whiteSpace: 'nowrap',
          }}
        >
          {activities.map((a, i) => (
            <span key={i} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 10, color: a.color, fontFamily: 'JetBrains Mono', flexShrink: 0 }}>
                {a.agent}
              </span>
              <span style={{ fontSize: 11, color: '#8892B0', maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {a.message}
              </span>
              <span style={{ fontSize: 9, color: '#2A3060', fontFamily: 'JetBrains Mono' }}>{a.time}</span>
            </span>
          ))}
        </div>
      </div>

      {/* Showrunner progress */}
      {showrunnerProgress && (
        <div style={{
          padding: '0 14px',
          borderLeft: '1px solid rgba(255,255,255,0.06)',
          display: 'flex',
          alignItems: 'center',
          maxWidth: 300,
          height: '100%',
          flexShrink: 0,
        }}>
          <span style={{ fontSize: 11, color: '#4A5280', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {showrunnerProgress}
          </span>
        </div>
      )}

      <style>{`
        @keyframes ticker {
          0%   { transform: translateX(0); }
          100% { transform: translateX(-50%); }
        }
      `}</style>
    </div>
  );
}
