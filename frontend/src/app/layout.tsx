import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'AgentSphere OS — The Operating System for Autonomous AI Agents',
  description:
    'AgentSphere OS is a microkernel-based AI operating system. Manage agents like processes, memory like RAM, and workflows like OS jobs.',
  keywords: ['AI agents', 'AI OS', 'autonomous agents', 'agent orchestration'],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="bg-void text-white antialiased">{children}</body>
    </html>
  );
}
