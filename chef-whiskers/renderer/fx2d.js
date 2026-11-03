// 2D motion graphics drawn on a canvas layered over the 3D render: comic bursts, stickers,
// speed lines, light rays and impact rings. Every function is a pure function of its inputs,
// so frames stay deterministic.
const INK = '#1d1206';
const FONT = size => `900 ${size}px "Inter", "Arial Black", "DejaVu Sans", sans-serif`;

function hash(i, s = 1) { const x = Math.sin(i * 127.1 + s * 311.7) * 43758.5453; return x - Math.floor(x); }

function withAlpha(ctx, alpha, fn) {
  if (alpha <= 0.002) return;
  ctx.save();
  ctx.globalAlpha = Math.min(1, alpha);
  fn();
  ctx.restore();
}

function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

// Spiky comic "pow" burst.
export function starburst(ctx, x, y, r, { points = 12, inner = 0.62, fill = '#ffd84d', stroke = INK, lineWidth = 10, rot = 0, alpha = 1, jitter = 0.14, seed = 1 } = {}) {
  withAlpha(ctx, alpha, () => {
    ctx.translate(x, y); ctx.rotate(rot);
    ctx.beginPath();
    for (let i = 0; i < points * 2; i++) {
      const a = i / (points * 2) * Math.PI * 2, rr = (i % 2 ? r * inner : r) * (1 + jitter * (hash(i, seed) - 0.5) * 2);
      if (i) ctx.lineTo(Math.cos(a) * rr, Math.sin(a) * rr); else ctx.moveTo(Math.cos(a) * rr, Math.sin(a) * rr);
    }
    ctx.closePath();
    if (fill) { ctx.fillStyle = fill; ctx.fill(); }
    if (stroke) { ctx.lineJoin = 'round'; ctx.lineWidth = lineWidth; ctx.strokeStyle = stroke; ctx.stroke(); }
  });
}

// Short radial strokes around a point, for impacts ("action lines").
export function actionLines(ctx, x, y, r0, r1, { count = 14, width = 9, color = '#ffffff', alpha = 1, seed = 2, rot = 0 } = {}) {
  withAlpha(ctx, alpha, () => {
    ctx.lineCap = 'round'; ctx.strokeStyle = color;
    for (let i = 0; i < count; i++) {
      const a = rot + i / count * Math.PI * 2 + (hash(i, seed) - 0.5) * 0.3, k = 0.75 + 0.5 * hash(i + 9, seed);
      ctx.lineWidth = width * (0.6 + 0.7 * hash(i + 4, seed));
      ctx.beginPath();
      ctx.moveTo(x + Math.cos(a) * r0 * k, y + Math.sin(a) * r0 * k);
      ctx.lineTo(x + Math.cos(a) * r1 * k, y + Math.sin(a) * r1 * k);
      ctx.stroke();
    }
  });
}

// Big outlined comic lettering, e.g. "CRUNCH!".
export function comicText(ctx, x, y, text, { size = 130, rot = 0, scale = 1, fill = '#ffffff', stroke = INK, lineWidth = 18, alpha = 1 } = {}) {
  withAlpha(ctx, alpha, () => {
    ctx.translate(x, y); ctx.rotate(rot); ctx.scale(scale, scale);
    ctx.font = FONT(size); ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.lineJoin = 'round';
    ctx.fillStyle = 'rgba(0,0,0,0.35)'; ctx.fillText(text, 7, 12);
    ctx.lineWidth = lineWidth; ctx.strokeStyle = stroke; ctx.strokeText(text, 0, 0);
    ctx.fillStyle = fill; ctx.fillText(text, 0, 0);
  });
}

// Rounded label with an optional icon, like a sticker slapped on the video.
export function sticker(ctx, x, y, text, { size = 62, scale = 1, rot = 0, bg = '#ffffff', fg = INK, alpha = 1, icon = null, iconColor = '#ff5a36', t = 0 } = {}) {
  if (scale <= 0.01) return;
  withAlpha(ctx, alpha, () => {
    ctx.translate(x, y); ctx.rotate(rot); ctx.scale(scale, scale);
    ctx.font = FONT(size);
    const tw = ctx.measureText(text).width, iw = icon ? size * 1.0 : 0, pad = size * 0.42, h = size * 1.55;
    const w = tw + pad * 2 + (icon ? iw + size * 0.22 : 0);
    roundRect(ctx, -w / 2 + 6, -h / 2 + 10, w, h, h * 0.34); ctx.fillStyle = 'rgba(0,0,0,0.3)'; ctx.fill();
    roundRect(ctx, -w / 2, -h / 2, w, h, h * 0.34); ctx.fillStyle = bg; ctx.fill();
    ctx.lineWidth = size * 0.12; ctx.strokeStyle = INK; ctx.stroke();
    let cx = -w / 2 + pad;
    if (icon) { icon(ctx, cx + iw / 2, 0, size * 0.95, iconColor, t); cx += iw + size * 0.22; }
    ctx.fillStyle = fg; ctx.textAlign = 'left'; ctx.textBaseline = 'middle'; ctx.fillText(text, cx, size * 0.05);
  });
}

// Anime-style speed lines rushing in from the frame edges toward a point.
export function speedLines(ctx, cx, cy, t, { count = 56, alpha = 0.5, inner = 430, outer = 1700, color = '255,255,255', seed = 3 } = {}) {
  withAlpha(ctx, alpha, () => {
    const step = Math.floor(t * 24);
    for (let i = 0; i < count; i++) {
      const flick = hash(i + step * 31, seed);
      if (flick < 0.4) continue;
      const a = (i / count) * Math.PI * 2 + (hash(i, seed) - 0.5) * 0.1, r0 = inner * (0.8 + 0.5 * hash(i * 3, seed));
      const da = (5 + 13 * hash(i * 7, seed)) / outer;
      ctx.beginPath();
      ctx.moveTo(cx + Math.cos(a - da) * outer, cy + Math.sin(a - da) * outer);
      ctx.lineTo(cx + Math.cos(a) * r0, cy + Math.sin(a) * r0);
      ctx.lineTo(cx + Math.cos(a + da) * outer, cy + Math.sin(a + da) * outer);
      ctx.closePath();
      ctx.fillStyle = `rgba(${color},${0.45 + 0.55 * flick})`; ctx.fill();
    }
  });
}

// Soft rotating light rays (added light).
export function rays(ctx, cx, cy, t, { count = 12, alpha = 0.12, len = 1500, width = 0.12, color = '255,236,170' } = {}) {
  withAlpha(ctx, alpha, () => {
    ctx.globalCompositeOperation = 'lighter';
    const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, len);
    g.addColorStop(0, `rgba(${color},1)`); g.addColorStop(1, `rgba(${color},0)`);
    ctx.fillStyle = g;
    for (let i = 0; i < count; i++) {
      const a = t * 0.35 + i / count * Math.PI * 2;
      ctx.beginPath(); ctx.moveTo(cx, cy); ctx.arc(cx, cy, len, a - width / 2, a + width / 2); ctx.closePath(); ctx.fill();
    }
  });
}

// Expanding impact ring, squashed to sit on a surface.
export function ringFx(ctx, x, y, r, { alpha = 1, width = 12, color = '#ffffff', squash = 0.4 } = {}) {
  withAlpha(ctx, alpha, () => {
    ctx.translate(x, y); ctx.scale(1, squash);
    ctx.beginPath(); ctx.arc(0, 0, Math.max(1, r), 0, Math.PI * 2);
    ctx.lineWidth = width / squash * 0.6; ctx.strokeStyle = color; ctx.stroke();
  });
}

// Small four-point twinkle.
export function twinkleStar(ctx, x, y, r, { alpha = 1, color = '#fff6cf', rot = 0 } = {}) {
  withAlpha(ctx, alpha, () => {
    ctx.translate(x, y); ctx.rotate(rot); ctx.fillStyle = color;
    ctx.beginPath();
    for (let i = 0; i < 8; i++) { const a = i / 8 * Math.PI * 2, rr = i % 2 ? r * 0.18 : r; if (i) ctx.lineTo(Math.cos(a) * rr, Math.sin(a) * rr); else ctx.moveTo(rr, 0); }
    ctx.closePath(); ctx.fill();
  });
}

// ---- icons for stickers: (ctx, x, y, size, color, t)
export function thermoIcon(ctx, x, y, s, color = '#ff5a36') {
  ctx.save(); ctx.translate(x, y); ctx.lineWidth = s * 0.1; ctx.strokeStyle = INK;
  roundRect(ctx, -s * 0.14, -s * 0.48, s * 0.28, s * 0.72, s * 0.14); ctx.fillStyle = '#ffffff'; ctx.fill(); ctx.stroke();
  ctx.beginPath(); ctx.arc(0, s * 0.3, s * 0.21, 0, Math.PI * 2); ctx.fillStyle = color; ctx.fill(); ctx.stroke();
  ctx.fillStyle = color; ctx.fillRect(-s * 0.055, -s * 0.28, s * 0.11, s * 0.5);
  ctx.restore();
}

export function clockIcon(ctx, x, y, s, color = '#2f80ed', t = 0) {
  ctx.save(); ctx.translate(x, y); ctx.lineWidth = s * 0.1; ctx.strokeStyle = INK; ctx.lineCap = 'round';
  ctx.beginPath(); ctx.arc(0, 0, s * 0.44, 0, Math.PI * 2); ctx.fillStyle = color; ctx.fill(); ctx.stroke();
  ctx.beginPath(); ctx.arc(0, 0, s * 0.3, 0, Math.PI * 2); ctx.fillStyle = '#ffffff'; ctx.fill();
  const a = t * 6;
  ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(Math.sin(a) * s * 0.24, -Math.cos(a) * s * 0.24); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(s * 0.14, 0); ctx.stroke();
  ctx.restore();
}

export function flameIcon(ctx, x, y, s, color = '#ff5a36', t = 0) {
  ctx.save(); ctx.translate(x, y); ctx.scale(1, 1 + 0.06 * Math.sin(t * 20)); ctx.lineWidth = s * 0.09; ctx.strokeStyle = INK; ctx.lineJoin = 'round';
  const flame = k => {
    ctx.beginPath();
    ctx.moveTo(0, -s * 0.48 * k);
    ctx.bezierCurveTo(s * 0.32 * k, -s * 0.12 * k, s * 0.38 * k, s * 0.22 * k, 0, s * 0.42 * k);
    ctx.bezierCurveTo(-s * 0.38 * k, s * 0.22 * k, -s * 0.3 * k, -s * 0.1 * k, -s * 0.05 * k, -s * 0.2 * k);
    ctx.closePath();
  };
  flame(1); ctx.fillStyle = color; ctx.fill(); ctx.stroke();
  ctx.translate(0, s * 0.12); flame(0.5); ctx.fillStyle = '#ffd84d'; ctx.fill();
  ctx.restore();
}

export function checkIcon(ctx, x, y, s, color = '#2fbf5b') {
  ctx.save(); ctx.translate(x, y); ctx.lineWidth = s * 0.1; ctx.strokeStyle = INK;
  ctx.beginPath(); ctx.arc(0, 0, s * 0.44, 0, Math.PI * 2); ctx.fillStyle = color; ctx.fill(); ctx.stroke();
  ctx.lineWidth = s * 0.13; ctx.strokeStyle = '#ffffff'; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
  ctx.beginPath(); ctx.moveTo(-s * 0.2, 0); ctx.lineTo(-s * 0.05, s * 0.16); ctx.lineTo(s * 0.22, -s * 0.16); ctx.stroke();
  ctx.restore();
}

export function speakerIcon(ctx, x, y, s, color = '#ff5a36', t = 0) {
  ctx.save(); ctx.translate(x, y); ctx.lineWidth = s * 0.09; ctx.strokeStyle = INK; ctx.lineJoin = 'round'; ctx.lineCap = 'round';
  ctx.beginPath();
  ctx.moveTo(-s * 0.44, -s * 0.14); ctx.lineTo(-s * 0.22, -s * 0.14); ctx.lineTo(s * 0.04, -s * 0.38);
  ctx.lineTo(s * 0.04, s * 0.38); ctx.lineTo(-s * 0.22, s * 0.14); ctx.lineTo(-s * 0.44, s * 0.14); ctx.closePath();
  ctx.fillStyle = color; ctx.fill(); ctx.stroke();
  for (let k = 0; k < 2; k++) {
    const r = s * (0.22 + k * 0.17), a = 0.62 + 0.1 * Math.sin(t * 14 + k * 1.5);
    ctx.beginPath(); ctx.arc(s * 0.08, 0, r, -a, a); ctx.stroke();
  }
  ctx.restore();
}

// Full-frame flash, e.g. white on a hard cut.
export function flash(ctx, alpha, color = '255,255,255') {
  withAlpha(ctx, alpha, () => { ctx.fillStyle = `rgb(${color})`; ctx.fillRect(0, 0, ctx.canvas.width, ctx.canvas.height); });
}
