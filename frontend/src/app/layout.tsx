import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'AgentSphere OS — The Operating System for Autonomous AI Agents',
  description:
    'AgentSphere OS is a microkernel-based AI operating system. Manage agents like processes, memory like RAM, and workflows like OS jobs.',
  keywords: ['AI agents', 'AI OS', 'autonomous agents', 'agent orchestration'],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&family=Sora:wght@300;400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body style={{ background: 'var(--bg-base)', color: 'var(--text-primary)' }}>
        {/* Aurora animated background layers */}
        <div className="aurora-bg">
          <div className="aurora-orb" />
        </div>
        {/* Subtle grid overlay */}
        <div className="grid-overlay" />
        {children}
      </body>
    </html>
  );
}
