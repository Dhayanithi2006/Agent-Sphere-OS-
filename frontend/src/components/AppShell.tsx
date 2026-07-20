'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Sidebar from '@/components/Sidebar';
import TopBar from '@/components/TopBar';
import GlobalLiveFeed from '@/components/GlobalLiveFeed';

export default function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<{ email: string; role: string } | null>(null);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem('agentsphere_user');
    if (!stored) {
      router.push('/login');
    } else {
      try {
        setUser(JSON.parse(stored));
      } catch {
        router.push('/login');
      }
    }
    setChecked(true);
  }, []);

  if (!checked || !user) {
    return (
      <div
        style={{
          height: '100vh',
          background: 'var(--bg-base)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 16,
        }}
      >
        {/* Loading spinner */}
        <div
          style={{
            width: 48,
            height: 48,
            borderRadius: '50%',
            border: '2px solid rgba(139,92,246,0.15)',
            borderTop: '2px solid #8B5CF6',
            animation: 'shell-spin 0.8s linear infinite',
          }}
        />
        <div
          style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 12,
            color: '#5C5880',
            letterSpacing: '0.08em',
          }}
        >
          AUTHENTICATING...
        </div>
        <style>{`
          @keyframes shell-spin {
            from { transform: rotate(0deg); }
            to   { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    );
  }

  return (
    <div
      style={{
        display: 'flex',
        height: '100vh',
        overflow: 'hidden',
        background: 'var(--bg-base)',
      }}
    >
      <Sidebar />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', minWidth: 0 }}>
        <TopBar />
        <main
          style={{
            flex: 1,
            overflowY: 'auto',
            overflowX: 'hidden',
            position: 'relative',
            paddingBottom: 40,
          }}
        >
          <div style={{ position: 'relative', zIndex: 1 }}>{children}</div>
        </main>
      </div>
      <GlobalLiveFeed />
    </div>
  );
}
