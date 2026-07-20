'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState } from 'react';

const NAV = [
  { href: '/',            label: 'Home',        icon: '🏠', desc: 'Command Center',  color: '#8B5CF6' },
  { href: '/dashboard',   label: 'Dashboard',   icon: '📊', desc: 'Mission Control', color: '#F472B6' },
  { href: '/processes',   label: 'Processes',   icon: '⚙️', desc: 'Task Manager',    color: '#22D3EE' },
  { href: '/agents',      label: 'Agents',      icon: '🤖', desc: 'Agent Fleet',     color: '#34D399' },
  { href: '/memory',      label: 'Memory',      icon: '💾', desc: 'RAM Explorer',    color: '#FBBF24' },
  { href: '/scheduler',   label: 'Scheduler',   icon: '🕐', desc: 'CPU Scheduler',   color: '#8B5CF6' },
  { href: '/execution',   label: 'Execution',   icon: '▶',  desc: 'Live DAG',        color: '#22D3EE' },
  { href: '/checkpoints', label: 'Checkpoints', icon: '💠', desc: 'System Restore',  color: '#F472B6' },
  { href: '/recovery',    label: 'Recovery',    icon: '🔄', desc: 'Recovery Engine', color: '#34D399' },
  { href: '/marketplace', label: 'Marketplace', icon: '🛒', desc: 'Plugin Store',    color: '#FBBF24' },
  { href: '/showrunner',  label: 'Showrunner',  icon: '🎬', desc: 'Creative Studio', color: '#F472B6' },
  { href: '/analytics',   label: 'Analytics',   icon: '📈', desc: 'Insights',        color: '#22D3EE' },
  { href: '/settings',    label: 'Settings',    icon: '⚙',  desc: 'System Config',   color: '#8B5CF6' },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      style={{
        width: collapsed ? 64 : 228,
        transition: 'width 0.3s cubic-bezier(0.4,0,0.2,1)',
        background: 'rgba(8,8,16,0.92)',
        backdropFilter: 'blur(28px) saturate(180%)',
        WebkitBackdropFilter: 'blur(28px) saturate(180%)',
        borderRight: '1px solid rgba(139,92,246,0.12)',
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        position: 'sticky',
        top: 0,
        zIndex: 40,
        flexShrink: 0,
      }}
    >
      {/* ── Logo ─────────────────────────────── */}
      <div
        style={{
          padding: collapsed ? '20px 0' : '20px 16px',
          borderBottom: '1px solid rgba(139,92,246,0.1)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: collapsed ? 'center' : 'flex-start',
          gap: 12,
          overflow: 'hidden',
        }}
      >
        {/* Logo mark */}
        <div
          style={{
            width: 36,
            height: 36,
            borderRadius: 10,
            background: 'linear-gradient(135deg, #8B5CF6, #F472B6)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 18,
            flexShrink: 0,
            boxShadow: '0 0 20px rgba(139,92,246,0.5), 0 0 40px rgba(244,114,182,0.2)',
            position: 'relative',
          }}
        >
          <span style={{ filter: 'brightness(2)' }}>⬡</span>
          {/* Pulse ring */}
          <div
            style={{
              position: 'absolute',
              inset: -3,
              borderRadius: 13,
              border: '1px solid rgba(139,92,246,0.4)',
              animation: 'logo-ring 3s ease-in-out infinite',
            }}
          />
        </div>

        {!collapsed && (
          <div style={{ overflow: 'hidden' }}>
            <div
              style={{
                fontFamily: 'Outfit, sans-serif',
                fontWeight: 800,
                fontSize: 14,
                letterSpacing: '-0.02em',
                background: 'linear-gradient(135deg, #F1F0FF, #C4B5FD)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                backgroundClip: 'text',
                whiteSpace: 'nowrap',
              }}
            >
              AgentSphere OS
            </div>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 5,
                marginTop: 2,
              }}
            >
              <span
                style={{
                  width: 5,
                  height: 5,
                  borderRadius: '50%',
                  background: '#34D399',
                  boxShadow: '0 0 6px #34D399',
                  display: 'inline-block',
                  animation: 'pulse-cyan 2s infinite',
                }}
              />
              <span
                style={{
                  fontSize: 10,
                  color: '#5C5880',
                  fontFamily: 'JetBrains Mono, monospace',
                  whiteSpace: 'nowrap',
                }}
              >
                Kernel Active
              </span>
            </div>
          </div>
        )}
      </div>

      {/* ── Navigation ───────────────────────── */}
      <nav style={{ flex: 1, padding: '10px 0', overflowY: 'auto', overflowX: 'hidden' }}>
        {NAV.map(({ href, label, icon, desc, color }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              title={collapsed ? label : undefined}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: collapsed ? '10px 0' : '9px 12px',
                margin: '1px 6px',
                borderRadius: 10,
                textDecoration: 'none',
                justifyContent: collapsed ? 'center' : 'flex-start',
                background: active
                  ? `rgba(${hexToRgb(color)},0.12)`
                  : 'transparent',
                border: active
                  ? `1px solid rgba(${hexToRgb(color)},0.25)`
                  : '1px solid transparent',
                position: 'relative',
                overflow: 'hidden',
                transition: 'all 0.2s cubic-bezier(0.4,0,0.2,1)',
              }}
            >
              {/* Active accent line */}
              {active && (
                <div
                  style={{
                    position: 'absolute',
                    left: 0,
                    top: '20%',
                    bottom: '20%',
                    width: 2,
                    background: `linear-gradient(${color}, ${color}88)`,
                    borderRadius: '0 2px 2px 0',
                    boxShadow: `0 0 8px ${color}`,
                  }}
                />
              )}

              {/* Icon */}
              <span
                style={{
                  fontSize: collapsed ? 18 : 16,
                  flexShrink: 0,
                  filter: active ? `drop-shadow(0 0 6px ${color})` : 'grayscale(0.3) opacity(0.7)',
                  transition: 'filter 0.2s',
                }}
              >
                {icon}
              </span>

              {/* Label + desc */}
              {!collapsed && (
                <div style={{ overflow: 'hidden' }}>
                  <div
                    style={{
                      fontSize: 13,
                      fontWeight: active ? 600 : 400,
                      color: active ? color : '#A8A5C6',
                      fontFamily: 'Outfit, sans-serif',
                      whiteSpace: 'nowrap',
                      transition: 'color 0.2s',
                    }}
                  >
                    {label}
                  </div>
                </div>
              )}
            </Link>
          );
        })}
      </nav>

      {/* ── Collapse toggle ───────────────────── */}
      <div
        style={{
          padding: '10px 8px',
          borderTop: '1px solid rgba(139,92,246,0.1)',
        }}
      >
        <button
          onClick={() => setCollapsed(!collapsed)}
          style={{
            width: '100%',
            padding: '8px',
            borderRadius: 8,
            background: 'rgba(139,92,246,0.07)',
            border: '1px solid rgba(139,92,246,0.15)',
            color: '#8B5CF6',
            cursor: 'pointer',
            fontSize: 13,
            fontFamily: 'Outfit, sans-serif',
            fontWeight: 500,
            transition: 'all 0.2s ease',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 6,
          }}
        >
          {collapsed ? '→' : (
            <>
              <span>←</span>
              <span>Collapse</span>
            </>
          )}
        </button>
      </div>

      <style>{`
        @keyframes logo-ring {
          0%, 100% { opacity: 0.4; transform: scale(1); }
          50%       { opacity: 0.8; transform: scale(1.05); }
        }
      `}</style>
    </aside>
  );
}

/** Convert hex color to "r,g,b" string for rgba() usage */
function hexToRgb(hex: string): string {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result
    ? `${parseInt(result[1], 16)},${parseInt(result[2], 16)},${parseInt(result[3], 16)}`
    : '139,92,246';
}
