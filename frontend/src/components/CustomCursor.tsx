import { useEffect, useRef, useState } from 'react';

/**
 * CustomCursor — a bespoke, lifelike pointer for the Textura aesthetic.
 *
 * Anatomy (two layers, decoupled motion = "lifelike"):
 *   • dot  — a small white core that tracks the mouse 1:1 (instant, precise)
 *   • ring — a larger accent ring that *trails* the dot via per-frame lerp (spring lag)
 *
 * Interactions:
 *   • magnetic — over a button/link the ring eases toward the element's centre and
 *     swells, so it "snaps" onto targets instead of floating past them
 *   • text     — over inputs the ring morphs into a tall I-beam
 *   • press    — on mousedown the whole rig contracts, like a real click
 *   • label    — elements with [data-cursor-label] print a word inside the ring
 *
 * Performance: position is written straight to the DOM via refs inside one rAF loop —
 * React state only flips the (rare) mode, so there is no re-render per mouse move.
 *
 * Accessibility: bails out entirely on touch / coarse pointers and when the user
 * prefers reduced motion, restoring the native cursor.
 */

type Mode = 'default' | 'hover' | 'text';

const INTERACTIVE = 'a, button, [role="button"], [data-cursor], label, summary, .card-interactive';
const TEXTUAL = 'input:not([type="checkbox"]):not([type="radio"]), textarea, [contenteditable="true"]';

export default function CustomCursor() {
  const dotRef = useRef<HTMLDivElement>(null);
  const ringRef = useRef<HTMLDivElement>(null);
  const labelRef = useRef<HTMLSpanElement>(null);

  // Live positions kept in refs so the rAF loop never triggers React renders.
  const mouse = useRef({ x: -100, y: -100 });
  const ring = useRef({ x: -100, y: -100 });
  const magnet = useRef<{ x: number; y: number; strength: number } | null>(null);

  const [enabled, setEnabled] = useState(false);
  const [mode, setMode] = useState<Mode>('default');
  const [down, setDown] = useState(false);
  const [visible, setVisible] = useState(false);

  // Decide whether to run at all (fine pointer + motion allowed).
  useEffect(() => {
    const finePointer = window.matchMedia('(pointer: fine)').matches;
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    setEnabled(finePointer && !reduced);
  }, []);

  useEffect(() => {
    if (!enabled) return;

    document.documentElement.classList.add('has-custom-cursor');

    const onMove = (e: MouseEvent) => {
      mouse.current.x = e.clientX;
      mouse.current.y = e.clientY;
      if (!visible) setVisible(true);

      // The dot is 1:1 with the mouse — write it immediately for zero perceived lag.
      const dot = dotRef.current;
      if (dot) dot.style.transform = `translate3d(${e.clientX}px, ${e.clientY}px, 0)`;
    };

    const onOver = (e: MouseEvent) => {
      const target = e.target as Element | null;
      if (!target) return;

      const textual = target.closest(TEXTUAL);
      if (textual) {
        setMode('text');
        magnet.current = null;
        setLabel('');
        return;
      }

      const hit = target.closest(INTERACTIVE) as HTMLElement | null;
      if (hit) {
        setMode('hover');
        const r = hit.getBoundingClientRect();
        // Pull the ring toward the element centre; bigger targets pull harder.
        const strength = Math.min(0.35, Math.max(0.12, 1 - r.width / 900));
        magnet.current = { x: r.left + r.width / 2, y: r.top + r.height / 2, strength };
        setLabel(hit.getAttribute('data-cursor-label') ?? '');
      } else {
        setMode('default');
        magnet.current = null;
        setLabel('');
      }
    };

    const setLabel = (text: string) => {
      const el = labelRef.current;
      if (el && el.textContent !== text) el.textContent = text;
    };

    const onDown = () => setDown(true);
    const onUp = () => setDown(false);
    const onLeave = () => setVisible(false);
    const onEnter = () => setVisible(true);

    window.addEventListener('mousemove', onMove, { passive: true });
    window.addEventListener('mouseover', onOver, { passive: true });
    window.addEventListener('mousedown', onDown, { passive: true });
    window.addEventListener('mouseup', onUp, { passive: true });
    document.addEventListener('mouseleave', onLeave);
    document.addEventListener('mouseenter', onEnter);

    let raf = 0;
    const tick = () => {
      const m = magnet.current;
      // Target = the mouse, blended toward a magnet centre when hovering a target.
      const tx = m ? mouse.current.x + (m.x - mouse.current.x) * m.strength : mouse.current.x;
      const ty = m ? mouse.current.y + (m.y - mouse.current.y) * m.strength : mouse.current.y;

      // Critically-damped-ish follow: the ring chases the target → spring lag.
      ring.current.x += (tx - ring.current.x) * 0.18;
      ring.current.y += (ty - ring.current.y) * 0.18;

      const el = ringRef.current;
      if (el) el.style.transform = `translate3d(${ring.current.x}px, ${ring.current.y}px, 0)`;

      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseover', onOver);
      window.removeEventListener('mousedown', onDown);
      window.removeEventListener('mouseup', onUp);
      document.removeEventListener('mouseleave', onLeave);
      document.removeEventListener('mouseenter', onEnter);
      document.documentElement.classList.remove('has-custom-cursor');
    };
  }, [enabled, visible]);

  if (!enabled) return null;

  return (
    <div className={`tx-cursor ${visible ? 'is-visible' : ''}`} aria-hidden="true">
      <div
        ref={ringRef}
        className={`tx-cursor__ring tx-cursor__ring--${mode} ${down ? 'is-down' : ''}`}
      >
        <span ref={labelRef} className="tx-cursor__label" />
      </div>
      <div className={`tx-cursor__dot ${down ? 'is-down' : ''} ${mode === 'hover' ? 'is-hover' : ''}`} ref={dotRef} />
    </div>
  );
}
