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

  // Don't render until auth check completes
  if (!checked || !user) {
    return (
      <div style={{ height: '100vh', background: '#020814', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ fontFamily: 'JetBrains Mono', color: '#4A5280', fontSize: 13, display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ animation: 'spin 1s linear infinite', display: 'inline-block', fontSize: 18 }}>⟳</span>
          Authenticating...
        </div>
        <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden', background: '#02020A' }}>
      <Sidebar user={user} />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <TopBar user={user} />
        <main style={{ flex: 1, overflowY: 'auto', overflowX: 'hidden', position: 'relative', paddingBottom: 36 }}>
          <div style={{ position: 'fixed', inset: 0, backgroundImage: 'linear-gradient(rgba(0,212,255,0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(0,212,255,0.02) 1px, transparent 1px)', backgroundSize: '40px 40px', pointerEvents: 'none', zIndex: 0 }} />
          <div style={{ position: 'relative', zIndex: 1 }}>{children}</div>
        </main>
      </div>
      <GlobalLiveFeed />
    </div>
  );
}
