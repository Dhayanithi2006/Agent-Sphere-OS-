'use client';

import { useEffect, useState, useRef } from 'react';
import { useRouter } from 'next/navigation';

// ── Particle canvas ────────────────────────────────────────────────────────────
function ParticleField() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d')!;
    let raf: number;
    const resize = () => { canvas.width = window.innerWidth; canvas.height = window.innerHeight; };
    resize();
    window.addEventListener('resize', resize);
    const N = 70;
    const particles = Array.from({ length: N }, () => ({
      x: Math.random() * (canvas.width),
      y: Math.random() * (canvas.height),
      vx: (Math.random() - 0.5) * 0.3,
      vy: (Math.random() - 0.5) * 0.3,
      r: Math.random() * 1.5 + 0.5,
      hue: Math.random() > 0.5 ? 195 : 270,
    }));
    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      for (let i = 0; i < N; i++) {
        for (let j = i + 1; j < N; j++) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const d = Math.sqrt(dx * dx + dy * dy);
          if (d < 130) {
            ctx.beginPath();
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particles[j].x, particles[j].y);
            ctx.strokeStyle = `rgba(0,212,255,${0.06 * (1 - d / 130)})`;
            ctx.lineWidth = 0.5;
            ctx.stroke();
          }
        }
      }
      particles.forEach(p => {
        const grad = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.r * 3);
        grad.addColorStop(0, `hsla(${p.hue},100%,70%,0.8)`);
        grad.addColorStop(1, `hsla(${p.hue},100%,70%,0)`);
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = grad;
        ctx.fill();
        p.x += p.vx; p.y += p.vy;
        if (p.x < 0 || p.x > canvas.width) p.vx *= -1;
        if (p.y < 0 || p.y > canvas.height) p.vy *= -1;
      });
      raf = requestAnimationFrame(draw);
    };
    draw();
    return () => { cancelAnimationFrame(raf); window.removeEventListener('resize', resize); };
  }, []);
  return <canvas ref={canvasRef} style={{ position: 'fixed', inset: 0, width: '100%', height: '100%', pointerEvents: 'none', zIndex: 0 }} />;
}

// ── Demo accounts ──────────────────────────────────────────────────────────────
const DEMO_ACCOUNTS = [
  { email: 'admin@agentsphere.ai', password: 'admin2024', role: 'Admin', color: '#7B2FFF' },
  { email: 'demo@agentsphere.ai',  password: 'demo1234',  role: 'Demo',  color: '#00D4FF' },
  { email: 'hackathon@qwen.ai',    password: 'qwen2024',  role: 'Judge', color: '#00FF9D' },
];

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPass, setShowPass] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [focusedField, setFocusedField] = useState<string | null>(null);

  useEffect(() => {
    setMounted(true);
    // If already logged in, redirect
    if (typeof window !== 'undefined' && localStorage.getItem('agentsphere_user')) {
      router.push('/');
    }
  }, []);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    await new Promise(r => setTimeout(r, 800)); // simulate auth

    const account = DEMO_ACCOUNTS.find(a => a.email === email.trim().toLowerCase() && a.password === password);
    if (account) {
      localStorage.setItem('agentsphere_user', JSON.stringify({ email: account.email, role: account.role, loginAt: Date.now() }));
      router.push('/');
    } else {
      setError('Invalid credentials. Try a demo account below.');
      setLoading(false);
    }
  };

  const quickLogin = async (acc: typeof DEMO_ACCOUNTS[0]) => {
    setEmail(acc.email);
    setPassword(acc.password);
    setError('');
    setLoading(true);
    await new Promise(r => setTimeout(r, 600));
    localStorage.setItem('agentsphere_user', JSON.stringify({ email: acc.email, role: acc.role, loginAt: Date.now() }));
    router.push('/');
  };

  return (
    <div style={{ minHeight: '100vh', background: '#020814', display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative', overflow: 'hidden' }}>
      <style>{`
        @keyframes fadeUp { from { opacity:0; transform:translateY(20px); } to { opacity:1; transform:none; } }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        @keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:0.5; } }
        @keyframes glow { 0%,100% { box-shadow: 0 0 20px rgba(123,47,255,0.3); } 50% { box-shadow: 0 0 40px rgba(0,212,255,0.5), 0 0 80px rgba(123,47,255,0.3); } }
        .input-field { background: rgba(255,255,255,0.04); border: 1.5px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 14px 16px; color: #F0F4FF; font-size: 14px; outline: none; width: 100%; box-sizing: border-box; font-family: inherit; transition: all 0.2s; }
        .input-field:focus { border-color: rgba(0,212,255,0.5); background: rgba(0,212,255,0.04); box-shadow: 0 0 0 3px rgba(0,212,255,0.08); }
        .input-field::placeholder { color: #2A3060; }
        .demo-card { border-radius: 10px; padding: 10px 14px; cursor: pointer; border: 1px solid rgba(255,255,255,0.06); background: rgba(255,255,255,0.02); transition: all 0.2s; }
        .demo-card:hover { background: rgba(255,255,255,0.05); transform: translateY(-1px); }
      `}</style>

      <ParticleField />

      {/* Background glow orbs */}
      <div style={{ position: 'fixed', top: '-20%', right: '-10%', width: 600, height: 600, background: 'radial-gradient(circle, rgba(123,47,255,0.08) 0%, transparent 70%)', pointerEvents: 'none' }} />
      <div style={{ position: 'fixed', bottom: '-20%', left: '-10%', width: 500, height: 500, background: 'radial-gradient(circle, rgba(0,212,255,0.06) 0%, transparent 70%)', pointerEvents: 'none' }} />

      {/* Card */}
      <div style={{ position: 'relative', zIndex: 10, width: '100%', maxWidth: 440, padding: '0 20px', animation: mounted ? 'fadeUp 0.6s ease' : 'none' }}>

        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: 36 }}>
          <div style={{ width: 64, height: 64, borderRadius: 20, background: 'linear-gradient(135deg, #7B2FFF 0%, #00D4FF 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 28, margin: '0 auto 16px', animation: 'glow 3s ease-in-out infinite', boxShadow: '0 0 30px rgba(123,47,255,0.4)' }}>◈</div>
          <h1 style={{ fontFamily: 'Space Grotesk, sans-serif', fontSize: 28, fontWeight: 700, color: '#F0F4FF', margin: '0 0 6px' }}>AgentSphere OS</h1>
          <p style={{ color: '#4A5280', fontSize: 13, margin: 0 }}>The Operating System for Autonomous AI Agents</p>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, marginTop: 10, padding: '4px 12px', borderRadius: 100, background: 'rgba(0,255,157,0.06)', border: '1px solid rgba(0,255,157,0.15)' }}>
            <span style={{ width: 5, height: 5, borderRadius: '50%', background: '#00FF9D', boxShadow: '0 0 6px #00FF9D', display: 'inline-block' }} />
            <span style={{ fontSize: 10, color: '#00FF9D', fontFamily: 'JetBrains Mono' }}>KERNEL ACTIVE · Qwen Cloud</span>
          </div>
        </div>

        {/* Login card */}
        <div style={{ background: 'rgba(255,255,255,0.03)', backdropFilter: 'blur(20px)', borderRadius: 24, border: '1px solid rgba(255,255,255,0.08)', padding: '32px 28px', boxShadow: '0 24px 80px rgba(0,0,0,0.5)' }}>

          <h2 style={{ fontFamily: 'Space Grotesk, sans-serif', fontSize: 20, fontWeight: 700, color: '#F0F4FF', margin: '0 0 6px' }}>Sign In</h2>
          <p style={{ color: '#4A5280', fontSize: 13, margin: '0 0 24px' }}>Access the AI kernel dashboard</p>

          <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {/* Email */}
            <div>
              <label style={{ fontSize: 12, color: '#4A5280', display: 'block', marginBottom: 6, fontFamily: 'JetBrains Mono' }}>EMAIL ADDRESS</label>
              <input
                id="login-email"
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                onFocus={() => setFocusedField('email')}
                onBlur={() => setFocusedField(null)}
                placeholder="you@agentsphere.ai"
                className="input-field"
                autoComplete="email"
                required
              />
            </div>

            {/* Password */}
            <div>
              <label style={{ fontSize: 12, color: '#4A5280', display: 'block', marginBottom: 6, fontFamily: 'JetBrains Mono' }}>PASSWORD</label>
              <div style={{ position: 'relative' }}>
                <input
                  id="login-password"
                  type={showPass ? 'text' : 'password'}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  onFocus={() => setFocusedField('password')}
                  onBlur={() => setFocusedField(null)}
                  placeholder="••••••••"
                  className="input-field"
                  autoComplete="current-password"
                  required
                  style={{ paddingRight: 46 }}
                />
                <button
                  type="button"
                  onClick={() => setShowPass(s => !s)}
                  style={{ position: 'absolute', right: 14, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', color: '#4A5280', cursor: 'pointer', fontSize: 16, padding: 0 }}
                >
                  {showPass ? '🙈' : '👁'}
                </button>
              </div>
            </div>

            {/* Error */}
            {error && (
              <div style={{ padding: '10px 14px', background: 'rgba(255,61,113,0.08)', border: '1px solid rgba(255,61,113,0.2)', borderRadius: 10, fontSize: 13, color: '#FF3D71' }}>
                {error}
              </div>
            )}

            {/* Submit */}
            <button
              id="login-submit"
              type="submit"
              disabled={loading}
              style={{ padding: '14px', background: loading ? 'rgba(123,47,255,0.3)' : 'linear-gradient(135deg, #7B2FFF 0%, #00D4FF 100%)', border: 'none', borderRadius: 12, color: '#fff', fontSize: 15, fontWeight: 700, cursor: loading ? 'not-allowed' : 'pointer', fontFamily: 'Space Grotesk, sans-serif', transition: 'all 0.2s', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, boxShadow: loading ? 'none' : '0 4px 20px rgba(123,47,255,0.4)' }}
            >
              {loading ? (
                <>
                  <span style={{ animation: 'spin 1s linear infinite', display: 'inline-block' }}>⟳</span>
                  Authenticating...
                </>
              ) : 'Access AgentSphere OS →'}
            </button>
          </form>

          {/* Divider */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, margin: '24px 0 20px' }}>
            <div style={{ flex: 1, height: 1, background: 'rgba(255,255,255,0.06)' }} />
            <span style={{ fontSize: 11, color: '#2A3060', fontFamily: 'JetBrains Mono' }}>DEMO ACCOUNTS</span>
            <div style={{ flex: 1, height: 1, background: 'rgba(255,255,255,0.06)' }} />
          </div>

          {/* Demo accounts */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {DEMO_ACCOUNTS.map(acc => (
              <div key={acc.email} className="demo-card" onClick={() => quickLogin(acc)}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontSize: 12, color: '#F0F4FF', fontWeight: 600, marginBottom: 2 }}>{acc.email}</div>
                    <div style={{ fontSize: 11, color: '#4A5280', fontFamily: 'JetBrains Mono' }}>pw: {acc.password}</div>
                  </div>
                  <span style={{ padding: '3px 10px', borderRadius: 100, fontSize: 10, fontWeight: 700, color: acc.color, background: `${acc.color}15`, border: `1px solid ${acc.color}30` }}>
                    {acc.role}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <p style={{ textAlign: 'center', color: '#2A3060', fontSize: 11, marginTop: 20, fontFamily: 'JetBrains Mono' }}>
          AgentSphere OS v2.0 · Built for Qwen Cloud Hackathon 2024
        </p>
      </div>
    </div>
  );
}
