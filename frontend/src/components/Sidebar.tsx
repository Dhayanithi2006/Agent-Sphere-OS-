'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState } from 'react';

const NAV = [
  { href: '/',            label: 'Home',        icon: '⬡', desc: 'Command Center' },
  { href: '/dashboard',   label: 'Dashboard',   icon: '◈', desc: 'Mission Control' },
  { href: '/processes',   label: 'Processes',   icon: '▣', desc: 'Task Manager' },
  { href: '/agents',      label: 'Agents',      icon: '◉', desc: 'Agent Fleet' },
  { href: '/memory',      label: 'Memory',      icon: '⬡', desc: 'RAM Explorer' },
  { href: '/scheduler',   label: 'Scheduler',   icon: '≡', desc: 'CPU Scheduler' },
  { href: '/execution',   label: 'Execution',   icon: '▷', desc: 'Live DAG' },
  { href: '/checkpoints', label: 'Checkpoints', icon: '◎', desc: 'System Restore' },
  { href: '/recovery',    label: 'Recovery',    icon: '↺', desc: 'Recovery Engine' },
  { href: '/marketplace', label: 'Marketplace', icon: '⊞', desc: 'Plugin Store' },
  { href: '/showrunner',  label: 'Showrunner',  icon: '◈', desc: 'Creative Studio' },
  { href: '/analytics',   label: 'Analytics',   icon: '◬', desc: 'Insights' },
  { href: '/settings',    label: 'Settings',    icon: '⚙', desc: 'System Config' },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      style={{
        width: collapsed ? '60px' : '220px',
        transition: 'width 0.25s cubic-bezier(0.4,0,0.2,1)',
        background: 'rgba(8,8,24,0.95)',
        backdropFilter: 'blur(20px)',
        borderRight: '1px solid rgba(255,255,255,0.06)',
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        position: 'sticky',
        top: 0,
        zIndex: 40,
        flexShrink: 0,
      }}
    >
      {/* Logo */}
      <div
        style={{
          padding: collapsed ? '20px 0' : '20px 16px',
          borderBottom: '1px solid rgba(255,255,255,0.06)',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            width: 32,
            height: 32,
            borderRadius: 8,
            background: 'linear-gradient(135deg, #00D4FF, #7B2FFF)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 16,
            flexShrink: 0,
            boxShadow: '0 0 16px rgba(0,212,255,0.4)',
          }}
        >
          ⬡
        </div>
        {!collapsed && (
          <div>
            <div
              style={{
                fontFamily: 'Space Grotesk, sans-serif',
                fontWeight: 700,
                fontSize: 13,
                color: '#F0F4FF',
                whiteSpace: 'nowrap',
              }}
            >
              AgentSphere OS
            </div>
            <div style={{ fontSize: 10, color: '#4A5280', whiteSpace: 'nowrap' }}>
              v2.0 · Kernel Active
            </div>
          </div>
        )}
      </div>

      {/* Nav */}
      <nav style={{ flex: 1, padding: '8px 0', overflowY: 'auto', overflowX: 'hidden' }}>
        {NAV.map(({ href, label, icon, desc }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: collapsed ? '10px 0' : '9px 16px',
                justifyContent: collapsed ? 'center' : 'flex-start',
                margin: '1px 6px',
                borderRadius: 8,
                textDecoration: 'none',
                background: active ? 'rgba(0,212,255,0.08)' : 'transparent',
                border: active
                  ? '1px solid rgba(0,212,255,0.2)'
                  : '1px solid transparent',
                transition: 'all 0.15s ease',
                overflow: 'hidden',
              }}
              title={collapsed ? label : undefined}
            >
              <span
                style={{
                  fontSize: 15,
                  color: active ? '#00D4FF' : 'rgba(255,255,255,0.5)',
                  flexShrink: 0,
                  filter: active ? 'drop-shadow(0 0 4px #00D4FF)' : 'none',
                }}
              >
                {icon}
              </span>
              {!collapsed && (
                <span
                  style={{
                    fontSize: 13,
                    fontWeight: active ? 600 : 400,
                    color: active ? '#00D4FF' : '#8892B0',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {label}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Collapse toggle */}
      <div style={{ padding: '12px 8px', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
        <button
          onClick={() => setCollapsed(!collapsed)}
          style={{
            width: '100%',
            padding: '8px',
            borderRadius: 8,
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(255,255,255,0.08)',
            color: '#4A5280',
            cursor: 'pointer',
            fontSize: 13,
            transition: 'all 0.15s ease',
          }}
        >
          {collapsed ? '→' : '← Collapse'}
        </button>
      </div>
    </aside>
  );
}
