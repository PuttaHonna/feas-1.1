import React, { useEffect, useLayoutEffect, useRef, useState } from 'react';

const PATTERNS = {
  arrow: { 3: { cells: [1, 2, 3, 0, 1, 2, 1, 2, 3], loop: 7.2, scale: 1 } },
  dots: { 3: { cells: [0, 1, 2, 0, 1, 2, 0, 1, 2], loop: 3, scale: 2.4 } },
  ripple: { 3: { cells: [2, 1, 2, 1, 0, 1, 2, 1, 2], loop: 4.8, scale: 1.5 } },
  spiral: { 3: { cells: [0, 1, 2, 7, 8, 3, 6, 5, 4], loop: 9, scale: 1.2, lit: 0.35 } },
  orbit: {
    3: { cells: [0, 1, 2, 7, null, 3, 6, 5, 4], loop: 8, scale: 1.2 },
    4: { cells: [0, 1, 2, 3, 11, null, null, 4, 10, null, null, 5, 9, 8, 7, 6], loop: 6, scale: 1.2, lit: 0.45 }
  },
  snake: {
    3: { cells: [0, 1, 2, 5, 4, 3, 6, 7, 8], loop: 9, scale: 1, lit: 0.35 },
    4: { cells: [0, 1, 2, 3, 7, 6, 5, 4, 8, 9, 10, 11, 15, 14, 13, 12], loop: 16, scale: 1, lit: 0.25 }
  },
  sweep: { 4: { cells: [0, 1, 2, 3, 1, 2, 3, 4, 2, 3, 4, 5, 3, 4, 5, 6], loop: 5, scale: 1, lit: 0.45 } },
  spin: { 4: { cells: [0, 0, 1, 1, 0, 0, 1, 1, 3, 3, 2, 2, 3, 3, 2, 2], loop: 4, scale: 1.6, lit: 0.35 } },
  rain: { 4: { cells: [0, 2, 1, 3, 1, 3, 2, 4, 2, 4, 3, 5, 3, 5, 4, 6], loop: 4, scale: 1.2, lit: 0.35 } },
  pulse: { 4: { cells: [2, 1, 1, 2, 1, 0, 0, 1, 1, 0, 0, 1, 2, 1, 1, 2], loop: 2.4, scale: 2.5, lit: 0.45 } }
};

const DEFAULT_PATTERN = { 3: 'orbit', 4: 'sweep' };

const MARKS = {
  3: { done: [2, 3, 5, 7], error: [0, 2, 4, 6, 8] },
  4: { done: [7, 8, 10, 13], error: [0, 3, 5, 6, 9, 10, 12, 15] }
};

const resolvePattern = (pattern, grid) => {
  if (typeof pattern === 'string') {
    const named = PATTERNS[pattern];
    return (named && named[grid]) || (PATTERNS[DEFAULT_PATTERN[grid]][grid]);
  }
  const cells = Array.from({ length: grid * grid }, (_, i) => pattern.cells[i] ?? null);
  const max = Math.max(0, ...cells.filter(v => v != null));
  return { cells, loop: pattern.loop ?? max + 4.2, scale: pattern.scale ?? 1, lit: pattern.lit ?? 0.62 };
};

const STYLE = `
@keyframes lattice-on { 0%, 100% { opacity: var(--ll-idle); } 18%, 42% { opacity: var(--ll-peak); } 62% { opacity: var(--ll-idle); } }
@keyframes lattice-on-45 { 0%, 100% { opacity: var(--ll-idle); } 13%, 31% { opacity: var(--ll-peak); } 45% { opacity: var(--ll-idle); } }
@keyframes lattice-on-35 { 0%, 100% { opacity: var(--ll-idle); } 10%, 24% { opacity: var(--ll-peak); } 35% { opacity: var(--ll-idle); } }
@keyframes lattice-on-25 { 0%, 100% { opacity: var(--ll-idle); } 7%, 17% { opacity: var(--ll-peak); } 25% { opacity: var(--ll-idle); } }

.ll-root {
  display: inline-flex;
  align-items: center;
  position: relative;
  line-height: 1;
  font-family: inherit;
  gap: calc(var(--ll-font) * 0.625);
  font-size: var(--ll-font);
  color: var(--ll-color);
  font-weight: 500;
  vertical-align: middle;
}

.ll-grid-wrapper {
  display: grid;
  flex-shrink: 0;
  position: relative;
}

.ll-run {
  grid-area: 1 / 1;
  display: grid;
  grid-template-columns: repeat(var(--ll-n), var(--ll-cell));
  grid-template-rows: repeat(var(--ll-n), var(--ll-cell));
  gap: var(--ll-gap);
  transition: opacity 200ms ease;
}

.ll-root[data-status="done"] .ll-run,
.ll-root[data-status="error"] .ll-run {
  opacity: 0;
  pointer-events: none;
}
.ll-root[data-status="done"] .ll-run > span,
.ll-root[data-status="error"] .ll-run > span {
  animation-play-state: paused !important;
}

.ll-cell {
  height: var(--ll-cell);
  width: var(--ll-cell);
  border-radius: max(1px, calc(var(--ll-cell) * 0.25));
  background: var(--ll-color);
  transition: opacity 180ms ease, background-color 200ms ease;
  display: block;
}

.ll-root[data-shape="round"] .ll-cell {
  border-radius: 9999px !important;
}

.ll-root[data-glow="true"] .ll-run > span {
  box-shadow: 0 0 calc(var(--ll-cell) * 1.4) calc(var(--ll-cell) * 0.15) var(--ll-glow);
}

.ll-mark {
  grid-area: 1 / 1;
  display: grid;
  grid-template-columns: repeat(var(--ll-n), var(--ll-cell));
  grid-template-rows: repeat(var(--ll-n), var(--ll-cell));
  gap: var(--ll-gap);
  transform-origin: center;
  opacity: 0;
  transform: scale(0.9);
  transition: opacity 160ms var(--ll-ease-out), transform 160ms var(--ll-ease-out);
}

.ll-root[data-status="done"] .ll-mark,
.ll-root[data-status="error"] .ll-mark {
  opacity: 1;
  transform: none;
}

.ll-mark .ll-cell {
  opacity: var(--ll-idle);
}

.ll-mark .ll-cell[data-on="true"] {
  background: var(--ll-mark) !important;
  opacity: var(--ll-peak) !important;
}

.ll-root[data-glow="true"] .ll-mark .ll-cell[data-on="true"] {
  box-shadow: 0 0 calc(var(--ll-cell) * 1.5) calc(var(--ll-cell) * 0.2) var(--ll-mark-glow);
}

.ll-text-container {
  position: relative;
  display: inline-block;
  font-weight: 500;
  color: inherit;
}

.ll-text {
  position: absolute;
  top: 0;
  left: 0;
  white-space: nowrap;
  opacity: 0;
  filter: blur(2px);
  transition: opacity 200ms ease, filter 200ms ease;
}

.ll-text[data-active="true"] {
  position: static;
  opacity: 1;
  filter: blur(0);
}

.ll-timer {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-variant-numeric: tabular-nums;
  opacity: 0.7;
  font-size: calc(var(--ll-font) * 0.875);
}

.ll-sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

@media (prefers-reduced-motion: reduce) {
  .ll-run { --ll-peak: 0.7; }
  .ll-run > span { animation-delay: 0ms !important; animation-duration: 1400ms !important; }
  .ll-mark { transform: none !important; }
  .ll-text { filter: none !important; }
}
`;

const fmt = (ds) =>
  ds < 600 ? `${(ds / 10).toFixed(1)}s` : `${Math.floor(ds / 600)}m ${((ds % 600) / 10).toFixed(1)}s`;

const spoken = (ds) =>
  ds < 600
    ? `${(ds / 10).toFixed(1)} seconds`
    : `${Math.floor(ds / 600)} minutes ${((ds % 600) / 10).toFixed(1)} seconds`;

const LatticeLoader = ({
  label = 'Thinking',
  doneLabel = 'Done in',
  errorLabel = 'Failed after',
  status = 'working',
  pattern = 'arrow',
  grid = 3,
  shape = 'round',
  color = '#f5f5f5',
  doneColor = '#22c55e',
  errorColor = '#ef4444',
  cellSize = 6,
  gap = 2,
  fontSize = 14,
  step = 90,
  idleOpacity = 0.15,
  glow = false,
  glowColor = '',
  showTimer = true,
  elapsed,
  className = '',
  style
}) => {
  const n = grid === 4 ? 4 : 3;
  const pat = resolvePattern(pattern, n);
  const marks = MARKS[n];
  const d = step * pat.scale;
  const cycle = Math.round(pat.loop * d);

  const timerRef = useRef(null);
  const dsRef = useRef(0);
  const markRef = useRef('done');
  const mark = status === 'working' ? markRef.current : status;
  markRef.current = mark;
  const [announce, setAnnounce] = useState(`${label}, in progress`);

  const paint = (ds) => {
    dsRef.current = ds;
    if (timerRef.current) timerRef.current.textContent = fmt(ds);
  };

  useLayoutEffect(() => {
    if (elapsed != null) {
      paint(Math.round(elapsed * 10));
      return undefined;
    }
    if (status !== 'working') return undefined;
    const startedAt = performance.now();
    paint(0);
    const id = setInterval(() => paint(Math.floor((performance.now() - startedAt) / 100)), 100);
    return () => clearInterval(id);
  }, [status, elapsed]);

  useEffect(() => {
    if (status === 'working') setAnnounce(`${label}, in progress`);
    else setAnnounce(`${status === 'done' ? doneLabel : errorLabel}${showTimer ? ` ${spoken(dsRef.current)}` : ''}`);
  }, [status, label, doneLabel, errorLabel, showTimer]);

  const litKey = Math.round((pat.lit ?? 0.62) * 100);
  const animName = litKey === 45 ? 'lattice-on-45' : (litKey === 35 ? 'lattice-on-35' : (litKey === 25 ? 'lattice-on-25' : 'lattice-on'));

  return (
    <span
      role="status"
      className={`ll-root ${className}`.trim()}
      data-status={status}
      data-shape={shape}
      data-glow={glow ? 'true' : 'false'}
      style={{
        '--ll-n': n,
        '--ll-cell': `${cellSize}px`,
        '--ll-gap': `${gap}px`,
        '--ll-font': `${fontSize}px`,
        '--ll-color': color,
        '--ll-mark': status === 'error' ? errorColor : doneColor,
        '--ll-idle': idleOpacity,
        '--ll-glow': glowColor || color,
        '--ll-mark-glow': glowColor || (status === 'error' ? errorColor : doneColor),
        '--ll-cycle': `${cycle}ms`,
        '--ll-peak': 1,
        '--ll-ease-out': 'cubic-bezier(0.23, 1, 0.32, 1)',
        '--ll-ease-in-out': 'cubic-bezier(0.77, 0, 0.175, 1)',
        ...style
      }}
    >
      <style>{STYLE}</style>

      <span className="ll-grid-wrapper" aria-hidden="true">
        <span className="ll-run">
          {pat.cells.map((unit, i) => (
            <span
              key={i}
              className="ll-cell"
              style={{
                opacity: unit == null ? idleOpacity * 0.47 : idleOpacity,
                animation: unit == null ? 'none' : `${animName} ${cycle}ms infinite var(--ll-ease-in-out)`,
                animationDelay: unit == null ? undefined : `${Math.round(unit * d)}ms`
              }}
            />
          ))}
        </span>

        <span className="ll-mark">
          {pat.cells.map((_, i) => (
            <span
              key={i}
              className="ll-cell"
              data-on={marks[mark]?.includes(i) ? 'true' : 'false'}
            />
          ))}
        </span>
      </span>

      <span className="ll-text-container" aria-hidden="true">
        <span
          className="ll-text"
          data-active={status === 'working' ? 'true' : 'false'}
        >
          {label}
        </span>
        <span
          className="ll-text"
          data-active={status === 'done' ? 'true' : 'false'}
        >
          {doneLabel}
        </span>
        <span
          className="ll-text"
          data-active={status === 'error' ? 'true' : 'false'}
        >
          {errorLabel}
        </span>
      </span>

      {showTimer ? (
        <span
          ref={timerRef}
          className="ll-timer"
          aria-hidden="true"
        >
          0.0s
        </span>
      ) : null}

      <span className="ll-sr-only">{announce}</span>
    </span>
  );
};

export default LatticeLoader;
