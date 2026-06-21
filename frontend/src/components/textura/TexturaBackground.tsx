import { useEffect, useState, ReactNode } from 'react';

interface TexturaBackgroundProps {
  children?: ReactNode;
  className?: string;
  showOrbs?: boolean;
  showGrain?: boolean;
  showVignette?: boolean;
  showCursorGlow?: boolean;
}

export default function TexturaBackground({
  children,
  className = '',
  showOrbs = true,
  showGrain = true,
  showVignette = true,
  showCursorGlow = true,
}: TexturaBackgroundProps) {
  const [position, setPosition] = useState<{ x: number; y: number }>({ x: 50, y: 50 });
  const [reducedMotion, setReducedMotion] = useState<boolean>(false);

  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    setReducedMotion(mq.matches);

    const handleChange = (e: MediaQueryListEvent) => setReducedMotion(e.matches);
    mq.addEventListener('change', handleChange);
    return () => mq.removeEventListener('change', handleChange);
  }, []);

  useEffect(() => {
    if (!showCursorGlow || reducedMotion) return;

    const onMove = (e: MouseEvent) => {
      const x = (e.clientX / window.innerWidth) * 100;
      const y = (e.clientY / window.innerHeight) * 100;
      setPosition({ x, y });
    };

    window.addEventListener('mousemove', onMove, { passive: true });
    return () => window.removeEventListener('mousemove', onMove);
  }, [showCursorGlow, reducedMotion]);

  return (
    <div className={`relative min-h-screen bg-textura-bg overflow-hidden ${className}`}>
      {/* Pure black base */}
      <div className="absolute inset-0 bg-black" />

      {/* Gradient orbs */}
      {showOrbs && (
        <div
          className="absolute inset-0 pointer-events-none"
          style={{ filter: 'blur(120px)' }}
        >
          <div
            className="absolute w-[520px] h-[520px] rounded-full opacity-[0.14]"
            style={{
              top: '10%',
              left: '-8%',
              background: '#ffab98',
              animation: reducedMotion ? 'none' : 'textura-float 18s ease-in-out infinite',
            }}
          />
          <div
            className="absolute w-[560px] h-[560px] rounded-full opacity-[0.12]"
            style={{
              bottom: '5%',
              right: '-10%',
              background: '#a1ecff',
              animation: reducedMotion ? 'none' : 'textura-float 22s ease-in-out infinite reverse',
            }}
          />
        </div>
      )}

      {/* Cursor-tracking radial glow */}
      {showCursorGlow && !reducedMotion && (
        <div
          className="absolute inset-0 pointer-events-none opacity-30"
          style={{
            background: `radial-gradient(600px circle at ${position.x}% ${position.y}%, rgba(161,236,255,0.10), transparent 40%),
                         radial-gradient(500px circle at ${position.x}% ${position.y}%, rgba(255,171,152,0.06), transparent 40%)`,
          }}
        />
      )}

      {/* Film grain overlay */}
      {showGrain && (
        <div className="textura-grain" aria-hidden="true" />
      )}

      {/* Radial vignette */}
      {showVignette && (
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            background: 'radial-gradient(circle at center, transparent 0%, rgba(0,0,0,0.55) 100%)',
          }}
          aria-hidden="true"
        />
      )}

      {/* Content layer */}
      <div className="relative z-10">{children}</div>
    </div>
  );
}
