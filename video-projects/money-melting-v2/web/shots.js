// Shot list: each shot mirrors a reference frame composition, rebuilt in 3D with upgraded motion.
import { THREE, tl, C, camState, camTo, camSet, shake, flash, zoomBlur, post, floorU, figure, Panel, particles, TEX, glyphTexture, dashedLine, shot, every, mulberry32 } from './engine.js';
import { T, DUR, S, E, L, w, we, sfx, music, lbl, big, neonRect, bar, strikeLine, icon, glitchText, prog, clamp01, lerp, money, q, E_OUT, E_INOUT, E_BACK } from './lib.js';
import { text } from './engine.js';

// ---------------------------------------------------------------- helpers
const SEG = Object.keys(T.segments);
const nextStart = id => { const i = SEG.indexOf(id); return i + 1 < SEG.length ? S(SEG[i + 1]) : DUR + 1; };
function panel(parent, { w: pw, h: ph, x = 0, y = 0, z = 0, rx = 0, ry = 0, rz = 0, ppu = 620, draw, key = null, boost = 0.95, hud = false, additive = false, opacity = 1 }) {
  const p = new Panel({ w: pw, h: ph, ppu, draw, key, boost, additive, opacity, fog: !hud });
  p.mesh.position.set(x, y, z); p.mesh.rotation.set(rx, ry, rz);
  if (hud) { p.mesh.layers.set(1); p.mat.depthTest = false; p.mesh.renderOrder = 10; }
  parent.add(p.mesh);
  return p;
}
const hidden = o => { o.scale.setScalar(0.0001); return o; };
function popScale(o, t, { to = 1, dur = 0.45, ease = 'back.out(2)', s = 'pop', gain = 0.55 } = {}) {
  tl.fromTo(o.scale, { x: 0.0001, y: 0.0001, z: 0.0001 }, { x: to, y: to, z: to, duration: dur, ease }, t);
  if (s) sfx(s, t, gain);
}
function fadeMat(mat, t, to, dur = 0.4, from = null) { if (from !== null) tl.fromTo(mat, { opacity: from }, { opacity: to, duration: dur, ease: 'power2.out' }, t); else tl.to(mat, { opacity: to, duration: dur, ease: 'power2.out' }, t); }
function floorTint(t, color, k = 1, dur = 0.4) { const c = new THREE.Color(color).multiplyScalar(k * 0.06); tl.to(floorU.tint.value, { r: c.r, g: c.g, b: c.b, duration: dur }, t); }
function poolColor(fig, t, color, opacity = null, dur = 0.35) {
  const m = fig.userData.pool.material, c = new THREE.Color(color);
  tl.to(m.color, { r: c.r, g: c.g, b: c.b, duration: dur }, t);
  if (opacity !== null) tl.to(m, { opacity, duration: dur }, t);
}
function cut(t, kind = 'zoom') {
  if (kind === 'zoom') { zoomBlur(t, 0.9, 0.32); sfx('whoosh', t - 0.18, 0.5); }
  else if (kind === 'flash') { flash(t, 0.35, 0.3); sfx('hit', t, 0.6); }
  else sfx('swoosh', t - 0.08, 0.35);
}
function neonPlane(parent, iconName, { x, y = 0.55, z = 0, size = 0.9, color = C.mint, lw = 1.25 }) {
  return panel(parent, { w: size, h: size, x, y, z, ppu: 520, boost: 1.6, additive: true, draw: (c, t, P) => icon(c, iconName, P.cw / 2, P.ch / 2, P.cw * 0.86, color, lw, 26) });
}
function floorLabel(parent, s, { x, z = 0.42, w: lw = 1.1, color = C.grey, size = 34, ry = 0 }) {
  return panel(parent, { w: lw, h: 0.13, x, y: 0.004, z, rx: -Math.PI / 2, rz: ry, ppu: 640, draw: (c, t, P) => lbl(c, s, P.cw / 2, P.ch / 2, size, color) });
}
function glowPool(parent, { x = 0, z = 0, size = 1.6, color = C.mint, opacity = 0.0 }) {
  const m = new THREE.Mesh(new THREE.PlaneGeometry(size, size), new THREE.MeshBasicMaterial({ map: TEX.glow, transparent: true, opacity, depthWrite: false, blending: THREE.AdditiveBlending, toneMapped: false, color: new THREE.Color(color) }));
  m.rotation.x = -Math.PI / 2; m.position.set(x, 0.005, z); m.scale.set(1, 0.55, 1); parent.add(m); return m;
}
const DOLLAR = glyphTexture('$', '900 210px "Inter Display"');
const MINUS2 = glyphTexture('-2%', '900 92px "Inter Display"');
const UP = glyphTexture('▲', '900 150px Inter');

// global defaults that shots may change (reset at every cut)
function resetLook(t) { tl.set(post, { bloom: 0.7, fade: 0 }, t); tl.set(floorU.strength, { value: 0.55 }, t); floorTint(t, '#000000', 0, 0.01); }

// =====================================================================
// 1  HOOK — YOUR SAVINGS · REAL VALUE (red dripping glitch number)
// =====================================================================
shot(0, S('s02'), g => {
  resetLook(0);
  music(0, 0.7);
  const fig = figure({ glow: '#ff2a45', glowSize: 3.4, glowOpacity: 0.7 }); g.add(fig);
  floorTint(0, C.red, 1.4, 0.01);
  g.add(dashedLine(60, 0.95, 0, 0.4));
  const tN = w('s01', 'notice');
  const val = t => 8852 - 360 * Math.pow(clamp01(t / 3.0), 1.25);
  panel(g, {
    w: 1.6, h: 0.7, x: 0.0, y: 1.95, z: 0, ppu: 1000, boost: 1.1, key: t => q(t, 15),
    draw: (c, t, P) => {
      lbl(c, 'Your savings  ·  Real value', P.cw / 2, 80, 36, C.white, { glow: 8 });
      glitchText(c, '$' + money(val(t)), P.cw / 2, 330, 250, C.red, t, t < tN ? 1 : 0.35);
      if (t > tN) { c.globalAlpha = prog(t, tN, 0.3); lbl(c, '▼  You didn\'t notice', P.cw / 2, 560, 34, C.red, { glow: 12 }); c.globalAlpha = 1; }
    },
  });
  // blood-red drips on threads, falling to the mirror floor
  const R = mulberry32(3), D = Array.from({ length: 18 }, () => ({ x: (R() - 0.5) * 1.15, z: (R() - 0.5) * 0.12, p: R(), sp: 0.5 + R() * 0.7, L: 0.18 + R() * 0.55 }));
  const tp = new Float32Array(D.length * 6), thrGeo = new THREE.BufferGeometry();
  thrGeo.setAttribute('position', new THREE.BufferAttribute(tp, 3));
  const thr = new THREE.LineSegments(thrGeo, new THREE.LineBasicMaterial({ color: new THREE.Color(C.red).multiplyScalar(1.5), transparent: true, opacity: 0.75, toneMapped: false }));
  thr.frustumCulled = false; g.add(thr);
  const Y0 = 1.7;
  g.add(particles({
    count: D.length * 2, texture: TEX.glow, size: 0.04, color: C.red, boost: 2.0,
    fn: (t, p, a) => {
      D.forEach((d, i) => {
        const Tc = 1.5 / d.sp, u = ((t + d.p * Tc) % Tc) / Tc, len = d.L * E_OUT(Math.min(1, u / 0.6));
        tp.set([d.x, Y0, d.z, d.x, Y0 - len, d.z], i * 6);
        p.set([d.x, Y0 - len, d.z], i * 6); a[i * 2] = 1;
        const f = (u - 0.6) * Tc, y = Y0 - d.L - 0.5 * 9.8 * f * f;
        p.set([d.x, Math.max(0.01, y), d.z], i * 6 + 3); a[i * 2 + 1] = u > 0.6 && y > 0.01 ? 1 : 0;
      });
      thrGeo.attributes.position.needsUpdate = true;
    },
  }));
  // camera: open tight on the figure + number, then pull back to reveal
  const tAnd = w('s01', 'and');
  camSet(0, { x: 0.2, y: 1.05, z: 4.1, tx: 0.0, ty: 1.55, tz: 0, roll: -3, fov: 34 });
  camTo(0, { x: 0.14, z: 3.8, ty: 1.58 }, tAnd - 0.1, 'none');
  camTo(tAnd - 0.15, { x: 0.05, y: 1.2, z: 6.6, tx: 0.0, ty: 1.3, roll: -7, fov: 30 }, 1.0, 'power3.inOut');
  sfx('boom', 0.02, 0.8);
  for (let t = 0.1; t < S('s02') - 0.3; t += 1 / 12) { const r = Math.abs(Math.sin(Math.floor(t * 12) * 12.9898) * 43758.5453 % 1); if (r > 0.55) sfx('glitch', t, 0.18); }
  sfx('down', tN, 0.5, { dur: 0.8 });
  sfx('riser', S('s02') - 0.9, 0.4, { dur: 0.9 });
});

// =====================================================================
// 2  RAISE — PAYCHECK +5% vs PRICES +12% columns
// =====================================================================
shot(S('s02'), S('s03'), g => {
  const t0 = S('s02');
  resetLook(t0); cut(t0, 'zoom');
  const fig = figure({ glowOpacity: 0.55 }); fig.position.set(-0.6, 0, 0.05); g.add(fig);
  g.add(dashedLine(60, 0.55, 0.06, 0.4));
  const cols = [{ x: 0.12, color: C.mint, to: 0.95, label: 'Paycheck', pct: '+5%', t: w('s02', 'raise') - 0.05 },
                { x: 0.58, color: C.red, to: 1.6, label: 'Prices', pct: '+12%', t: w('s02', 'buy') - 0.1 }];
  for (const b of cols) {
    const frame = new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(0.28, 1.8, 0.28)), new THREE.LineBasicMaterial({ color: new THREE.Color(b.color).multiplyScalar(1.3), transparent: true, opacity: 0.5, toneMapped: false }));
    frame.position.set(b.x, 0.9, 0); g.add(frame);
    const glass = new THREE.Mesh(new THREE.BoxGeometry(0.28, 1.8, 0.28), new THREE.MeshStandardMaterial({ color: 0x0b0f14, transparent: true, opacity: 0.35, roughness: 0.15, metalness: 0.2 }));
    glass.position.copy(frame.position); g.add(glass);
    const fill = new THREE.Mesh(new THREE.BoxGeometry(0.24, 1, 0.24), new THREE.MeshBasicMaterial({ color: new THREE.Color(b.color).multiplyScalar(1.15), toneMapped: false, transparent: true, opacity: 0.9 }));
    fill.position.x = b.x; fill.scale.y = 0.0001; g.add(fill);
    tl.fromTo(fill.scale, { y: 0.0001 }, { y: b.to, duration: 0.95, ease: 'power3.out' }, b.t);
    sfx('riser', b.t, 0.35, { dur: 0.8 });
    const pl = panel(g, { w: 0.6, h: 0.22, x: b.x, y: 0, z: 0.02, ppu: 640, boost: 1.5, draw: (c, t, P) => big(c, b.pct, P.cw / 2, P.ch / 2 + 6, 104, b.color, { glow: 24 }) });
    every(t => { fill.position.y = fill.scale.y / 2; pl.mesh.position.y = fill.scale.y + 0.16; pl.mesh.scale.setScalar(fill.scale.y > 0.06 ? 1 : 0.0001); });
    panel(g, { w: 0.18, h: 0.9, x: b.x + 0.24, y: 0.5, z: 0, rz: 0, ppu: 640, draw: (c, t, P) => { c.save(); c.translate(P.cw / 2, P.ch / 2); c.rotate(-Math.PI / 2); lbl(c, b.label, 0, 0, 30, C.grey); c.restore(); } });
  }
  const qm = hidden(panel(g, { w: 0.55, h: 0.6, x: 0.38, y: 2.15, z: 0, ppu: 600, boost: 1.6, draw: (c, t, P) => big(c, '?', P.cw / 2, P.ch / 2 + 20, 320, C.white, { glow: 40 }) }).mesh);
  popScale(qm, w('s02', 'less') - 0.05, { s: 'hit', gain: 0.6 });
  shake(w('s02', 'less'), 0.4, 0.35);
  camSet(t0, { x: 1.35, y: 1.15, z: 6.2, tx: 0.0, ty: 1.0, tz: 0, roll: -6, fov: 31 });
  camTo(t0, { x: 0.85, z: 5.5, ty: 1.05 }, nextStart('s02') - t0, 'none');
});

// =====================================================================
// 3  INFLATION — floating title, small figure, mirror reflection
// =====================================================================
shot(S('s03'), S('s04'), g => {
  const t0 = S('s03');
  resetLook(t0); cut(t0, 'cut');
  const fig = figure({ glowOpacity: 0.5 }); fig.scale.setScalar(0.6); g.add(fig);
  g.add(dashedLine(80, 0.5, 0, 0.35));
  const tI = w('s03', 'inflation'), tSi = w('s03', 'silence');
  panel(g, {
    w: 2.7, h: 0.5, x: 0, y: 2.0, z: -0.5, ppu: 700, boost: 1.35, key: t => (t < tI + 1.2 ? q(t) : 'done') + (t > tSi ? 's' : ''),
    draw: (c, t, P) => {
      const s = 'INFLATION'; c.font = '900 150px "Inter Display"'; c.letterSpacing = '0px';
      const sp = 36, ws = [...s].map(ch => c.measureText(ch).width), total = ws.reduce((a, b) => a + b, 0) + sp * (s.length - 1);
      let x = (P.cw - total) / 2;
      [...s].forEach((ch, i) => {
        const k = prog(t, tI - 0.12 + i * 0.045, 0.45, E_OUT);
        c.save(); c.globalAlpha = k; c.filter = `blur(${((1 - k) * 14).toFixed(1)}px)`;
        c.shadowColor = '#fff'; c.shadowBlur = t > tSi ? 14 : 34; c.fillStyle = '#F4F7FF'; c.textBaseline = 'middle';
        c.fillText(ch, x, P.ch / 2 + (1 - k) * 60); c.restore(); x += ws[i] + sp;
      });
    },
  });
  sfx('boom', tI, 0.6); sfx('shimmer', tI + 0.1, 0.4);
  tl.to(post, { bloom: 0.4, duration: 0.8 }, tSi);
  camSet(t0, { x: 0, y: 1.2, z: 7.4, tx: 0, ty: 1.3, tz: 0, roll: 0, fov: 30 });
  camTo(t0, { z: 6.0, y: 1.25, roll: -2 }, nextStart('s03') - t0, 'power1.inOut');
});

// =====================================================================
// 4  PRICES — 2020 → 2024 row of category chips (camera pans the row)
// =====================================================================
shot(S('s04'), S('s05'), (g, h) => {
  const t0 = S('s04');
  resetLook(t0); cut(t0, 'zoom');
  const fig = figure({ glowOpacity: 0.5 }); fig.position.set(-1.3, 0, 0.15); g.add(fig);
  g.add(dashedLine(80, 0.75, 0, 0.35));
  const items = [['groceries', 'shopping-cart', 'Groceries', 150, 189, 0], ['rent', 'house', 'Rent', 1400, 1750, 0], ['gas', 'fuel', 'Gas', 2.6, 3.4, 2], ['insurance', 'shield', 'Insurance', 120, 153, 0]];
  const SP = 1.3;
  items.forEach(([word, ic, name, v0, v1, dec], i) => {
    const x = i * SP, tw = w('s04', word);
    panel(g, { w: 0.6, h: 0.6, x, y: 1.12, z: 0, ppu: 560, boost: 1.4, key: t => (t > tw ? 'r' : 'w'), draw: (c, t, P) => icon(c, ic, P.cw / 2, P.ch / 2, P.cw * 0.82, t > tw ? '#ffd9dd' : C.white, 1.2, 22) });
    panel(g, {
      w: 1.0, h: 0.4, x, y: 0.42, z: 0, ppu: 640, boost: 1.35, key: t => (t < tw ? 'a' : t < tw + 0.9 ? q(t) : 'b'),
      draw: (c, t, P) => {
        const k = prog(t, tw + 0.05, 0.75, E_INOUT), red = t > tw;
        neonRect(c, 10, 10, P.cw - 20, P.ch - 20, red ? C.red : C.white, { r: 30, lw: 6, glow: red ? 24 : 14 });
        lbl(c, name, P.cw / 2, 62, 24, red ? C.red : C.grey);
        big(c, '$' + money(lerp(v0, v1, k), dec), P.cw / 2, 160, 92, red ? C.red : C.white, { glow: red ? 18 : 8 });
        if (red) text(c, '▲', P.cw - 52, 54, { size: 34, color: C.red, glow: 12 });
      },
    });
    sfx('tick', tw, 0.5); sfx('pop', tw + 0.05, 0.4, { pitch: 1 + i * 0.12 });
  });
  // header: PRICES / year (camera-attached)
  const years = [[t0, 2020], [w('s04', 'groceries'), 2021], [w('s04', 'rent'), 2022], [w('s04', 'gas'), 2023], [w('s04', 'insurance'), 2024]];
  const yearAt = t => { let y = 2020; for (const [tt, yy] of years) if (t >= tt) y = yy; return y; };
  panel(h, {
    w: 0.8, h: 0.3, x: 0, y: 0.6, z: -3, ppu: 900, hud: true, boost: 1.25, key: t => yearAt(t) + ':' + (t - years.find(([, yy]) => yy === yearAt(t))[0] < 0.25 ? q(t) : ''),
    draw: (c, t, P) => {
      lbl(c, 'Prices', P.cw / 2, 40, 22, C.grey);
      const y = yearAt(t), tt = years.find(([, yy]) => yy === y)[0], k = prog(t, tt, 0.25);
      c.save(); c.globalAlpha = k; big(c, String(y), P.cw / 2, 165 - (1 - k) * 30, 120, C.white, { glow: 10, font: 'Inter', weight: 600 }); c.restore();
    },
  });
  years.slice(1).forEach(([tt]) => sfx('tick', tt, 0.6));
  camSet(t0, { x: -0.75, y: 1.05, z: 4.7, tx: -0.45, ty: 0.85, tz: 0, roll: -3, fov: 30 });
  items.forEach(([word], i) => camTo(w('s04', word) - 0.3, { x: i * SP + 0.15, tx: i * SP, ty: 0.8, z: 4.4 }, 0.55, 'power2.inOut'));
  const tEv = w('s04', 'everything');
  camTo(tEv - 0.2, { x: 1.95, y: 1.4, z: 8.6, tx: 1.95, ty: 0.75, roll: -4 }, 0.8, 'power3.inOut');
  shake(tEv + 0.1, 0.35, 0.4); sfx('boom', tEv, 0.5);
});

// =====================================================================
// 5  SAVINGS — tilted SAVINGS ACCOUNT panel behind the figure
// =====================================================================
shot(S('s05'), S('s06'), g => {
  const t0 = S('s05');
  resetLook(t0); cut(t0, 'zoom');
  const fig = figure({ glowOpacity: 0.6 }); fig.position.set(0.0, 0, 0.7); g.add(fig);
  const dl = dashedLine(80, 0, 0.42, 0.4); dl.position.z = 0.5; g.add(dl);
  const tP = w('s05', 'average'), tI = w('s05', 'pays'), tN = w('s05', 'nothing');
  panel(g, {
    w: 1.75, h: 1.2, x: 0.05, y: 1.72, z: -0.25, ry: -0.36, rx: 0.06, rz: 0.03, ppu: 640, boost: 1.3, key: t => (t < tN + 1 ? q(t) : 'd'),
    draw: (c, t, P) => {
      neonRect(c, 12, 12, P.cw - 24, P.ch - 24, C.white, { r: 26, lw: 6, glow: 16 });
      lbl(c, 'Savings account', 70, 92, 34, C.white, { align: 'left' }); lbl(c, 'Average', P.cw - 70, 92, 20, C.grey, { align: 'right' });
      lbl(c, 'Prices / year', 70, 230, 24, C.grey, { align: 'left' });
      bar(c, 70, 265, P.cw - 330, 46, 0.86 * prog(t, tP, 0.9), C.red, { glow: 22 });
      text(c, '+3%', P.cw - 230, 290, { size: 58, weight: 900, color: C.red, align: 'left', glow: 18, font: 'Inter Display' });
      lbl(c, 'Your interest', 70, 420, 24, C.grey, { align: 'left' });
      const flick = t > tN && t < tN + 0.6 ? (Math.floor(t * 20) % 2 ? 0.25 : 1) : 1;
      c.globalAlpha = flick; bar(c, 70, 455, P.cw - 330, 46, 0.1 * prog(t, tI, 0.6), C.mint, { glow: 22 }); c.globalAlpha = 1;
      if (t > tI) text(c, '~0.4%', P.cw - 230, 480, { size: 52, weight: 900, color: C.mint, align: 'left', glow: 16, font: 'Inter Display' });
      if (t > tN) { c.globalAlpha = prog(t, tN, 0.3); lbl(c, '≈  Almost nothing', 70, 600, 30, C.mint, { align: 'left', glow: 14 }); c.globalAlpha = 1; }
    },
  });
  sfx('swoosh', tP, 0.4); sfx('buzz', tN, 0.35);
  camSet(t0, { x: 0.75, y: 0.95, z: 6.0, tx: 0.05, ty: 1.4, tz: 0, roll: -7, fov: 31 });
  camTo(t0, { x: 0.3, z: 5.4 }, nextStart('s05') - t0, 'none');
});

// =====================================================================
// 6  BALANCE — $1,000 ✓ SAME, shelf empties, buying power drains
// =====================================================================
shot(S('s06'), S('s07'), g => {
  const t0 = S('s06');
  resetLook(t0); cut(t0, 'cut');
  g.add(dashedLine(80, 0.4, 0, 0.3));
  const tSame = w('s06', 'same'), tB = w('s06', 'buys'), tSh = w('s06', 'shrinking');
  panel(g, {
    w: 1.6, h: 0.75, x: 0, y: 2.38, z: 0, ppu: 640, key: t => (t < tSame + 0.6 ? q(t) : 'd'),
    draw: (c, t, P) => {
      lbl(c, 'Balance', P.cw / 2, 60, 22, C.grey);
      big(c, '$1,000', P.cw / 2 - 50, 230, 170, C.white, { glow: 16 });
      const k = prog(t, t0 + 0.2, 0.4);
      if (k > 0) { c.save(); c.strokeStyle = C.white; c.lineWidth = 20; c.lineCap = 'round'; c.lineJoin = 'round'; c.shadowColor = '#fff'; c.shadowBlur = 16;
        c.beginPath(); c.moveTo(800, 230); c.lineTo(800 + 40 * Math.min(1, k * 2), 230 + 40 * Math.min(1, k * 2)); if (k > 0.5) c.lineTo(840 + 80 * (k - 0.5) * 2, 270 - 110 * (k - 0.5) * 2); c.stroke(); c.restore(); }
      if (t > tSame) { c.globalAlpha = prog(t, tSame, 0.3); lbl(c, 'Same', P.cw / 2, 400, 24, C.white); c.globalAlpha = 1; }
    },
  });
  const ITEMS = [['milk', 'package', 'beer', 'croissant', 'sandwich'], ['milk', 'package', 'beer', 'croissant', 'sandwich']];
  const gone = [[1, 4, 0], [1, 3, 0.18], [0, 4, 0.36]];
  panel(g, {
    w: 2.3, h: 1.15, x: 0, y: 1.42, z: 0, ppu: 620, boost: 1.3, key: t => (t < tB || t > tSh + 1.2 ? (t > tSh ? 'e' : 's') + (t > tB ? 'v' : '') : q(t)),
    draw: (c, t, P) => {
      const rowY = [230, 520];
      rowY.forEach((y, r) => {
        c.save(); c.strokeStyle = 'rgba(244,247,255,.8)'; c.lineWidth = 4; c.shadowColor = '#fff'; c.shadowBlur = 10; c.beginPath(); c.moveTo(80, y + 110); c.lineTo(P.cw - 80, y + 110); c.stroke(); c.restore();
        ITEMS[r].forEach((n, i) => {
          const gi = gone.find(([gr, gc]) => gr === r && gc === i);
          let a = prog(t, tB - 0.2 + (r * 5 + i) * 0.03, 0.3), col = C.white, dy = 0;
          if (gi) { const k = prog(t, tSh + gi[2], 0.45); if (k > 0) { col = C.red; a *= 1 - k; dy = k * 60; } }
          c.globalAlpha = a; icon(c, n, 220 + i * 240, y + dy, 170, col, 1.25, 14); c.globalAlpha = 1;
        });
      });
      lbl(c, 'What $1,000 buys', P.cw / 2, 680, 24, C.grey);
    },
  });
  gone.forEach(([, , d]) => sfx('pop', tSh + d, 0.45, { pitch: 0.7 }));
  panel(g, {
    w: 2.1, h: 0.32, x: 0, y: 0.6, z: 0.05, ppu: 620, boost: 1.35, key: t => (t < tSh || t > tSh + 1.4 ? (t > tSh ? 'e' : 's') + (t > tB ? 'v' : '') : q(t)),
    draw: (c, t, P) => {
      if (t < tB - 0.1) return;
      const k = prog(t, tSh, 1.2, E_INOUT), pct = 100 - 20 * k, col = k > 0.05 ? C.red : C.mint;
      c.globalAlpha = prog(t, tB - 0.1, 0.3);
      bar(c, 30, 40, P.cw - 60, 60, pct / 100, col, { glow: 26 });
      lbl(c, 'Buying power', 40, 155, 22, C.grey, { align: 'left' });
      text(c, pct.toFixed(0) + '%', P.cw - 40, 150, { size: 46, weight: 900, color: col, align: 'right', font: 'Inter Display', glow: 12 });
    },
  });
  sfx('down', tSh, 0.45, { dur: 1.2 });
  camSet(t0, { x: 0, y: 1.6, z: 6.6, tx: 0, ty: 1.55, tz: 0, roll: -1.5, fov: 30 });
  camTo(t0, { z: 5.9, roll: -3 }, nextStart('s06') - t0, 'none');
});

// =====================================================================
// 7  STACK — $1,000 TODAY = $800 5 YEARS AGO, top bills disappear
// =====================================================================
shot(S('s07'), S('s08'), g => {
  const t0 = S('s07');
  resetLook(t0); cut(t0, 'zoom');
  const fig = figure({ glowOpacity: 0.5 }); fig.position.set(-1.15, 0, 0.3); g.add(fig);
  g.add(dashedLine(80, 0.55, 0.05, 0.35));
  const tA = w('s07', 'thousand') - 0.25, tB = w('s07', 'eight') - 0.15, tD = w('s07', 'disappeared');
  const billGeo = new THREE.BoxGeometry(0.66, 0.03, 0.38), edgeGeo = new THREE.EdgesGeometry(billGeo);
  const stack = (x, n, redTop, t) => {
    const bills = [];
    for (let i = 0; i < n; i++) {
      const red = i >= n - redTop, col = new THREE.Color(red ? C.red : C.mint);
      const b = new THREE.Group();
      b.add(new THREE.Mesh(billGeo, new THREE.MeshBasicMaterial({ color: col.clone().multiplyScalar(0.35), transparent: true, opacity: 0.55, toneMapped: false })));
      b.add(new THREE.LineSegments(edgeGeo, new THREE.LineBasicMaterial({ color: col.clone().multiplyScalar(1.6), toneMapped: false })));
      b.position.set(x, 0.05 + i * 0.058, 0); g.add(b); bills.push(b);
      tl.fromTo(b.position, { y: 0.05 + i * 0.058 + 0.9 }, { y: 0.05 + i * 0.058, duration: 0.35, ease: 'bounce.out' }, t + i * 0.045);
      tl.fromTo(b.scale, { x: 0.0001, y: 0.0001, z: 0.0001 }, { x: 1, y: 1, z: 1, duration: 0.12 }, t + i * 0.045);
    }
    sfx('swoosh', t, 0.4);
    return bills;
  };
  const left = stack(-0.18, 10, 2, tA), right = stack(0.95, 8, 0, tB);
  const label = (x, y, s, sub, t, col = C.white) => {
    const p = panel(g, { w: 0.9, h: 0.3, x, y, z: 0.05, ppu: 640, boost: 1.3, draw: (c, tt, P) => big(c, s, P.cw / 2, P.ch / 2, 120, col, { glow: 16 }) });
    popScale(p.mesh, t, { s: false });
    floorLabel(g, sub, { x, z: 0.42, w: 0.9, size: 28 });
  };
  label(-0.18, 0.88, '$1,000', 'Today', tA + 0.3);
  label(0.95, 0.76, '$800', '5 years ago', tB + 0.25, C.mint);
  const eq = hidden(panel(g, { w: 0.25, h: 0.25, x: 0.39, y: 0.42, z: 0.05, ppu: 600, draw: (c, t, P) => big(c, '=', P.cw / 2, P.ch / 2, 120, C.white, { glow: 14 }) }).mesh);
  popScale(eq, tB - 0.1, { s: false });
  // the top two (red) bills glitch out and vanish
  left.slice(8).forEach((b, i) => {
    tl.to(b.position, { x: '+=0.05', duration: 0.04, yoyo: true, repeat: 5 }, tD - 0.25);
    tl.to(b.scale, { x: 1.2, y: 0.0001, z: 0.0001, duration: 0.3, ease: 'power2.in' }, tD + i * 0.08);
  });
  const R = mulberry32(17), P = Array.from({ length: 70 }, () => [(R() - 0.5) * 0.66, (R() - 0.5) * 0.38, (R() - 0.5) * 2.2, R() * 2.2 + 0.4, (R() - 0.5) * 1.6]);
  g.add(particles({ count: P.length, texture: TEX.glow, size: 0.05, color: C.red, boost: 2.4, fn: (t, p, a) => P.forEach((d, i) => { const f = t - tD; p.set([-0.18 + d[0] + d[2] * f * 0.6, 0.55 + d[3] * f - 1.2 * f * f, d[1] + d[4] * f * 0.4], i * 3); a[i] = f > 0 && f < 1.2 ? 1 - f / 1.2 : 0; }) }));
  const dis = hidden(panel(g, { w: 1.1, h: 0.16, x: -0.18, y: 1.12, z: 0.05, ppu: 640, draw: (c, t, P) => lbl(c, 'Disappeared', P.cw / 2, P.ch / 2, 38, C.red, { glow: 16 }) }).mesh);
  popScale(dis, tD, { s: 'glitch', gain: 0.6 });
  shake(tD, 0.5, 0.4);
  camSet(t0, { x: 0.55, y: 1.2, z: 7.0, tx: 0.38, ty: 0.72, tz: 0, roll: -4, fov: 30 });
  camTo(t0, { x: 0.42, z: 6.3 }, nextStart('s07') - t0, 'none');
});

// =====================================================================
// 8  SCHOOL — ECONOMICS 101 board, struck through: NOT TAUGHT
// =====================================================================
shot(S('s08'), S('s09'), g => {
  const t0 = S('s08');
  resetLook(t0); cut(t0, 'flash');
  music(t0, 0.12, { filter: 1 }); sfx('riser', t0 + 0.2, 0.6, { dur: nextStart('s08') - t0 - 0.2 });
  const fig = figure({ glowOpacity: 0.7, glowSize: 2 }); fig.position.set(0, 0, 0.55); fig.scale.setScalar(1.15); g.add(fig);
  g.add(dashedLine(80, 0.9, 0.05, 0.35));
  const tDt = w('s08', 'dont'), tS = w('s08', 'school');
  const L1 = '1.  Save your money', L2 = '2.  Work hard', L3 = '3.  ???';
  panel(g, {
    w: 1.95, h: 1.12, x: 0, y: 2.05, z: -0.35, ppu: 640, boost: 1.3, key: t => (t < tS + 0.8 ? q(t) : 'd'),
    draw: (c, t, P) => {
      neonRect(c, 12, 12, P.cw - 24, P.ch - 24, C.white, { r: 24, lw: 6, glow: 16 });
      lbl(c, 'Economics 101', P.cw / 2, 130, 58, C.white, { glow: 8 });
      const ty = (s, y, t1) => { const n = Math.floor(clamp01((t - t1) * 26 / s.length) * s.length); lbl(c, s.slice(0, n), 130, y, 32, C.white, { align: 'left' }); };
      ty(L1, 300, t0 + 0.05); ty(L2, 400, t0 + 0.35); ty(L3, 500, t0 + 0.6);
      strikeLine(c, 110, 330, P.cw - 80, 250, prog(t, tDt, 0.35), C.red, 9);
      strikeLine(c, 110, 425, P.cw * 0.62, 375, prog(t, tDt + 0.18, 0.3), C.red, 9);
    },
  });
  for (let k = 0; k < 12; k++) sfx('type', t0 + 0.05 + k * 0.07, 0.3);
  sfx('swoosh', tDt, 0.4);
  const nt = hidden(panel(g, { w: 1.6, h: 0.22, x: 0, y: 1.38, z: -0.3, ppu: 640, boost: 1.4, draw: (c, t, P) => lbl(c, 'Not taught', P.cw / 2, P.ch / 2, 62, C.red, { glow: 20 }) }).mesh);
  popScale(nt, tS - 0.1, { s: 'stamp', gain: 0.8 });
  shake(tS, 0.7, 0.4);
  camSet(t0, { x: 0, y: 1.3, z: 5.9, tx: 0, ty: 1.65, tz: 0, roll: -2, fov: 30 });
  camTo(t0, { z: 5.0, y: 1.35, roll: -4 }, nextStart('s08') - t0, 'power1.in');
});

// =====================================================================
// 9  ENTRY — new money streams in, but NOT EVERYONE AT THE SAME TIME
// =====================================================================
shot(S('s09'), S('s10'), g => {
  const t0 = S('s09');
  resetLook(t0); cut(t0, 'flash'); flash(t0, 0.4, 0.4, C.mint);
  music(t0, 1.0, { drop: 1 }); sfx('drop', t0, 0.9);
  g.add(dashedLine(80, 0.3, 0.12, 0.35));
  const figs = [0.15, 0.75, 1.35].map((x, i) => { const f = figure({ glowOpacity: 0.25 }); f.position.set(x, 0, -i * 0.25); f.scale.setScalar(0.72); g.add(f); return f; });
  const tR = w('s09', 'reach'), tEv = w('s09', 'everyone'), tSame = w('s09', 'same');
  [tR, tEv, tSame].forEach((t, i) => { poolColor(figs[i], t, C.mint, 0.9); sfx('ding', t, 0.35); });
  const R = mulberry32(23), M = Array.from({ length: 90 }, () => [R() * 4, 0.6 + R() * 1.6, (R() - 0.5) * 1.6, 1.4 + R() * 1.2, R() * 6.28]);
  g.add(particles({
    count: M.length, texture: DOLLAR, size: 0.1, color: C.mint, boost: 1.7,
    fn: (t, p, a) => M.forEach((d, i) => { const f = t - t0; const x = -2.6 + ((d[0] + f * d[3]) % 5); p.set([x, d[1] + Math.sin(f * 2 + d[4]) * 0.08, d[2]], i * 3); a[i] = clamp01(f * 2) * clamp01((2.4 - x) * 2); }),
  }));
  const lab = panel(g, { w: 1.8, h: 0.16, x: 0.95, y: 1.55, z: -0.3, ppu: 640, draw: (c, t, P) => lbl(c, 'Not everyone at the same time', P.cw / 2, P.ch / 2, 34, C.white, { glow: 8 }) });
  fadeMat(lab.mat, tR - 0.1, 1, 0.4, 0);
  camSet(t0, { x: -1.0, y: 1.3, z: 5.6, tx: -0.4, ty: 1.15, tz: 0, roll: -6, fov: 31 });
  camTo(t0, { x: 0.9, tx: 0.85, ty: 0.9, z: 5.4 }, nextStart('s09') - t0, 'power2.inOut');
});

// =====================================================================
// 10+11  FLOW — banks → Wall Street → asset owners → you; they buy first
// =====================================================================
shot(S('s10'), S('s12'), (g, h) => {
  const t0 = S('s10');
  resetLook(t0); cut(t0, 'zoom');
  floorTint(t0, C.mint, 0.6);
  g.add(dashedLine(120, 0.75, 0, 0.35));
  const X = [0, 1.55, 3.1, 4.65];
  const tB = w('s10', 'banks'), tW = w('s10', 'wall'), tA = w('s10', 'assets'), tSp = w('s11', 'spend'), tUp = we('s11', 'up');
  const reach = [tB, tW, tA, 999];
  const icons = [['landmark', 'Banks'], ['building-2', 'Wall Street'], ['chart-line', 'Asset owners']];
  const pools = [];
  icons.forEach(([ic, name], i) => {
    const p = neonPlane(g, ic, { x: X[i], y: i === 1 ? 0.62 : 0.5, size: i === 1 ? 1.15 : 0.9 });
    fadeMat(p.mat, reach[i] - 0.5, 1, 0.4, 0.25);
    floorLabel(g, name, { x: X[i], z: 0.5, w: 1.2, color: C.mint, size: 30 });
    const pool = glowPool(g, { x: X[i], z: 0.1, size: 2.2, color: C.mint, opacity: 0 }); pools.push(pool);
    tl.to(pool.material, { opacity: 0.85, duration: 0.4 }, reach[i]);
    sfx('cash', reach[i], 0.4);
  });
  const you = figure({ glowOpacity: 0.25 }); you.position.set(X[3], 0, 0.1); g.add(you);
  floorLabel(g, 'You', { x: X[3], z: 0.55, w: 0.6, color: C.white, size: 30 });
  // money river: most money stops at the first stations
  const R = mulberry32(31), N = 150;
  const PM = Array.from({ length: N }, () => { const r = R(); return { stop: r < 0.46 ? 0 : r < 0.76 ? 1 : r < 0.95 ? 2 : 3, b: t0 - 0.6 + R() * 6.5, v: 1.9 + R() * 0.8, y: 0.35 + R() * 1.0, z: (R() - 0.5) * 0.7, ph: R() * 6.28, rr: 0.3 + R() * 0.35 }; });
  const front = t => { if (t < tB) return lerp(-1.5, X[0], clamp01((t - t0 + 0.6) / (tB - t0 + 0.6))); if (t < tW) return lerp(X[0], X[1], clamp01((t - tB) / (tW - tB))); if (t < tA) return lerp(X[1], X[2], clamp01((t - tW) / (tA - tW))); return lerp(X[2], X[3] - 0.6, clamp01((t - tA) / 4)); };
  g.add(particles({
    count: N, texture: DOLLAR, size: 0.1, color: C.mint, boost: 1.7,
    fn: (t, p, a) => PM.forEach((d, i) => {
      const f = t - d.b; if (f < 0) { a[i] = 0; return; }
      let x = -2.2 + f * d.v; const xs = X[d.stop];
      let y = d.y, z = d.z;
      if (x >= xs) { const o = (x - xs) * 1.6 + d.ph; x = xs + Math.cos(o) * d.rr; z = d.z * 0.5 + Math.sin(o) * d.rr * 0.6; y = 0.55 + d.y * 0.5 + Math.sin(o * 0.7) * 0.1; }
      p.set([x, y, z], i * 3); a[i] = x <= front(t) + 0.05 ? clamp01(f * 3) : 0;
    }),
  }));
  // they buy before prices move
  [[X[0], tSp], [X[1], tSp + 0.12], [X[2], tSp + 0.24]].forEach(([x, t]) => {
    const b = hidden(panel(g, { w: 0.9, h: 0.16, x, y: 1.35, z: 0, ppu: 640, draw: (c, tt, P) => lbl(c, '✓  Bought $100', P.cw / 2, P.ch / 2, 30, C.mint, { glow: 14 }) }).mesh);
    popScale(b, t, { s: 'cash', gain: 0.35 });
  });
  const tag = hidden(panel(g, { w: 1.1, h: 0.26, x: X[3] - 0.15, y: 1.6, z: 0, ppu: 640, boost: 1.35, key: t => (t < tUp + 0.6 ? q(t) : 'd'), draw: (c, t, P) => {
    neonRect(c, 8, 8, P.cw - 16, P.ch - 16, C.red, { r: 18, lw: 5, glow: 18 });
    const k = prog(t, tUp - 0.25, 0.5);
    lbl(c, `Prices  $100 → $${Math.round(lerp(100, 110, k))}`, P.cw / 2, P.ch / 2, 32, C.red, { glow: 10 });
  } }).mesh);
  popScale(tag, w('s11', 'prices') - 0.1, { s: 'hit', gain: 0.5 });
  camSet(t0, { x: -0.9, y: 0.9, z: 5.2, tx: -0.4, ty: 0.8, tz: 0, roll: -4, fov: 31 });
  [[tB, 0], [tW, 1], [tA, 2]].forEach(([t, i]) => camTo(t - 0.35, { x: X[i] + 0.3, tx: X[i] + 0.05, ty: 0.8, z: 5.0 }, 0.7, 'power2.inOut'));
  camTo(tSp - 0.35, { x: 2.35, y: 1.25, z: 6.6, tx: 2.35, ty: 0.9, tz: 0, roll: -4 }, 0.8, 'power3.inOut');
  camTo(w('s11', 'prices') - 0.25, { x: 4.05, tx: 4.1, z: 6.6 }, 0.75, 'power2.inOut');
});

// =====================================================================
// 12  PAYCHECK — +$100 arrives, everything COSTS MORE
// =====================================================================
shot(S('s12'), S('s13'), g => {
  const t0 = S('s12');
  resetLook(t0); cut(t0, 'zoom');
  floorTint(t0, C.mint, 0.8);
  const a = figure({ glow: C.mint, glowOpacity: 0.7, glowSize: 2.2 }); a.position.set(-0.5, 0, -0.1); g.add(a);
  const b = figure({ glow: C.mint, glowOpacity: 0.9, glowSize: 2.4 }); b.position.set(0.42, 0, 0.12); g.add(b);
  const tPay = w('s12', 'paycheck'), tC = w('s12', 'costs'), tM = w('s12', 'more');
  const card = hidden(panel(g, { w: 1.2, h: 0.55, x: 0.0, y: 2.1, z: -0.1, ry: -0.12, ppu: 640, boost: 1.35, key: t => (t > tM ? 'm' : 'p') + (t > tM && t < tM + 0.5 ? q(t) : ''), draw: (c, t, P) => {
    const dim = t > tM, col = dim ? '#7f8a99' : C.mint;
    neonRect(c, 10, 10, P.cw - 20, P.ch - 20, col, { r: 26, lw: 6, glow: dim ? 6 : 22 });
    lbl(c, 'Your paycheck', P.cw / 2, 80, 26, col);
    big(c, '+$100', P.cw / 2, 205, 110, col, { glow: dim ? 0 : 20 });
    if (dim) { c.globalAlpha = prog(t, tM, 0.3); lbl(c, '= $91 of stuff', P.cw / 2, 300, 24, C.red, { glow: 10 }); c.globalAlpha = 1; }
  } }).mesh);
  popScale(card, tPay - 0.15, { s: 'cash', gain: 0.7 });
  [[-0.95, 1.5, w('s12', 'everything')], [1.0, 1.65, w('s12', 'already')], [0.15, 1.12, tC]].forEach(([x, y, t]) => {
    const m = hidden(panel(g, { w: 0.85, h: 0.14, x, y, z: 0.1, ppu: 640, draw: (c, tt, P) => lbl(c, '▲  Costs more', P.cw / 2, P.ch / 2, 30, C.red, { glow: 16 }) }).mesh);
    popScale(m, t, { s: 'pop', gain: 0.5 });
  });
  poolColor(a, tM, C.red, 0.7); poolColor(b, tM, C.red, 0.8); floorTint(tM, C.red, 0.9);
  shake(tM, 0.7, 0.45); sfx('boom', tM, 0.6);
  camSet(t0, { x: 0.1, y: 1.25, z: 5.4, tx: 0, ty: 1.45, tz: 0, roll: -2, fov: 31 });
  camTo(t0, { z: 4.8, x: 0.25, roll: -4 }, nextStart('s12') - t0, 'none');
});

// =====================================================================
// 13  NAME — THE CANTILLON EFFECT over a line of figures
// =====================================================================
shot(S('s13'), S('s14'), g => {
  const t0 = S('s13');
  resetLook(t0); cut(t0, 'cut');
  music(t0, 0.05);
  g.add(dashedLine(80, 0.55, 0, 0.35));
  const figs = [-1.3, -0.78, -0.26, 0.26, 0.78, 1.3].map((x, i) => { const f = figure({ glow: i < 2 ? C.mint : i > 3 ? C.red : '#ffffff', glowOpacity: 0.55 }); f.position.set(x, 0, 0); f.scale.setScalar(0.5); g.add(f); return f; });
  const tc = w('s13', 'cantillon'), te = w('s13', 'effect');
  const R = mulberry32(5);
  panel(g, {
    w: 3.0, h: 0.62, x: 0, y: 1.32, z: -0.2, ppu: 650, boost: 1.4, key: t => (t < te + 1.4 ? q(t) : 'd'),
    draw: (c, t, P) => {
      const s = 'THE CANTILLON EFFECT'; c.font = '900 84px "Inter Display"';
      const sp = 14, ws = [...s].map(ch => c.measureText(ch).width), total = ws.reduce((x, y) => x + y, 0) + sp * (s.length - 1);
      let x = (P.cw - total) / 2;
      [...s].forEach((ch, i) => {
        const k = prog(t, (i < 3 ? w('s13', 'the') : i < 13 ? tc - 0.1 : te - 0.1) + (i % 10) * 0.03, 0.35, E_OUT);
        c.save(); c.globalAlpha = k; c.filter = `blur(${((1 - k) * 10).toFixed(1)}px)`; c.fillStyle = '#F4F7FF'; c.shadowColor = '#fff'; c.shadowBlur = 24; c.textBaseline = 'middle';
        c.fillText(ch, x, 150 + (1 - k) * 40); c.restore(); x += ws[i] + sp;
      });
      // glint sweep
      const gk = prog(t, tc + 0.45, 0.8, E_INOUT);
      if (gk > 0 && gk < 1) { c.save(); c.globalCompositeOperation = 'source-atop'; const gx = lerp(-200, P.cw + 200, gk); const gr = c.createLinearGradient(gx - 120, 0, gx + 120, 0); gr.addColorStop(0, 'rgba(255,255,255,0)'); gr.addColorStop(0.5, 'rgba(255,240,200,1)'); gr.addColorStop(1, 'rgba(255,255,255,0)'); c.fillStyle = gr; c.fillRect(0, 0, P.cw, 260); c.restore(); }
      if (t > te + 0.25) { c.globalAlpha = prog(t, te + 0.25, 0.4); lbl(c, 'Whoever gets new money first, wins', P.cw / 2, 320, 30, C.mint, { glow: 12 }); c.globalAlpha = 1; }
    },
  });
  flash(tc, 0.45, 0.4); shake(tc, 1.0, 0.55); sfx('boom', tc, 1); sfx('shimmer', tc + 0.4, 0.5);
  music(tc, 0.9, { hit: 1 });
  tl.fromTo(post, { bloom: 1.8 }, { bloom: 0.7, duration: 0.8, immediateRender: false }, tc);
  const red = hidden(panel(g, { w: 0.75, h: 0.18, x: -1.55, y: 0.85, z: 0.3, ppu: 640, draw: (c, t, P) => { neonRect(c, 6, 6, P.cw - 12, P.ch - 12, C.red, { r: 14, lw: 4 }); lbl(c, 'Prices $100 → $110', P.cw / 2, P.ch / 2, 26, C.red); } }).mesh);
  popScale(red, t0 + 0.2, { s: false });
  camSet(t0, { x: 0, y: 1.0, z: 8.2, tx: 0, ty: 1.0, tz: 0, roll: -3, fov: 30 });
  camTo(t0, { z: 7.3, roll: -1.5 }, nextStart('s13') - t0, 'power1.inOut');
});

// =====================================================================
// 14  RICHER — WHO GETS RICHER? homes & stocks vs salary
// =====================================================================
shot(S('s14'), S('s15'), g => {
  const t0 = S('s14');
  resetLook(t0); cut(t0, 'zoom');
  music(t0, 0.85);
  const tH = w('s14', 'homes') - 0.15, tRi = w('s14', 'richer'), tWh = w('s14', 'while'), tF = w('s14', 'fall'), tEnd = we('s14', 'behind');
  const dA = Math.max(1.8, tRi + 0.4 - tH), dS = tEnd - tWh;
  const curveA = k => [lerp(200, 1950, k), lerp(760, 170, Math.pow(k, 1.7))], curveS = k => [lerp(200, 1950, k), lerp(760, 700, k)];
  panel(g, {
    w: 3.5, h: 1.6, x: 1.05, y: 0.95, z: 0, ppu: 600, boost: 1.4, key: t => (t < tEnd + 0.6 ? q(t) : 'd'),
    draw: (c, t, P) => {
      lbl(c, 'Who gets richer?', 200, 70, 30, C.white, { align: 'left', glow: 8 });
      c.save(); c.strokeStyle = 'rgba(255,255,255,.08)'; c.lineWidth = 2; for (let y = 200; y <= 760; y += 140) { c.beginPath(); c.moveTo(200, y); c.lineTo(1950, y); c.stroke(); } c.restore();
      const kA = prog(t, tH, dA, E_INOUT), kS = prog(t, tWh, dS, E_INOUT), fk = prog(t, tF, 0.6);
      if (fk > 0 && kA > 0.99) { c.save(); c.beginPath(); for (let i = 0; i <= 60; i++) { const [x, y] = curveA(i / 60); i ? c.lineTo(x, y) : c.moveTo(x, y); } for (let i = 60; i >= 0; i--) { const [x, y] = curveS(i / 60 * kS); c.lineTo(x, y); } c.closePath(); const gr = c.createLinearGradient(0, 170, 0, 760); gr.addColorStop(0, `rgba(255,77,94,${0.45 * fk})`); gr.addColorStop(1, `rgba(255,77,94,${0.05 * fk})`); c.fillStyle = gr; c.fill(); c.restore(); }
      const line = (fn, k, col, lw) => { if (k <= 0) return; c.save(); c.strokeStyle = col; c.lineWidth = lw; c.lineCap = 'round'; c.shadowColor = col; c.shadowBlur = 24; c.beginPath(); for (let i = 0; i <= 80; i++) { const [x, y] = fn(i / 80 * k); i ? c.lineTo(x, y) : c.moveTo(x, y); } c.stroke(); const [hx, hy] = fn(k); c.fillStyle = col; c.beginPath(); c.arc(hx, hy, 14, 0, 7); c.fill(); c.restore(); return [hx, hy]; };
      const hA = line(curveA, kA, C.mint, 10), hS = line(curveS, kS, C.white, 9);
      if (hA) { icon(c, 'house', hA[0] - 150, hA[1] - 120, 90, C.mint, 1.4, 14); icon(c, 'trending-up', hA[0] - 40, hA[1] - 120, 90, C.mint, 1.4, 14); lbl(c, 'Homes & stocks', Math.min(hA[0], 1700), hA[1] + 60, 24, C.mint, { glow: 8 }); }
      if (t > tRi && hA) { c.globalAlpha = prog(t, tRi, 0.3); lbl(c, '▲ Richer', Math.min(hA[0] + 40, 1880), hA[1] - 10, 28, C.mint, { align: 'left', glow: 12 }); c.globalAlpha = 1; }
      if (hS) lbl(c, 'Salary', Math.min(hS[0], 1760), hS[1] + 55, 24, C.white);
      if (t > tF && hS) { c.globalAlpha = prog(t, tF, 0.3); lbl(c, '▼ Fall behind', Math.min(hS[0] - 60, 1700), hS[1] - 55, 28, C.red, { glow: 12 }); c.globalAlpha = 1; }
    },
  });
  sfx('riser', tH, 0.35, { dur: dA }); sfx('cash', tRi, 0.5); sfx('down', tF, 0.5, { dur: 0.9 });
  shake(tF, 0.35, 0.4);
  camSet(t0, { x: 0.25, y: 1.05, z: 5.0, tx: 0.25, ty: 1.1, tz: 0, roll: -4, fov: 31 });
  camTo(tH, { x: 2.3, tx: 2.0, ty: 1.15 }, dA, 'power2.inOut');
  camTo(tWh - 0.1, { x: 1.2, tx: 1.05, ty: 1.0, z: 5.3, y: 1.15, roll: -3 }, 1.2, 'power3.inOut');
});

// =====================================================================
// 15  WORK — 50+ HRS / WEEK under a hard spotlight
// =====================================================================
shot(S('s15'), S('s16'), g => {
  const t0 = S('s15');
  resetLook(t0); cut(t0, 'cut');
  const fig = figure({ glowOpacity: 1, glowSize: 2.4 }); fig.scale.setScalar(1.12); g.add(fig);
  const cone = new THREE.Mesh(new THREE.CylinderGeometry(0.35, 1.25, 5, 48, 1, true), new THREE.ShaderMaterial({
    uniforms: {}, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide,
    vertexShader: 'varying vec2 vUv; varying vec3 vN; varying vec3 vV; void main(){ vUv = uv; vec4 mv = modelViewMatrix*vec4(position,1.0); vN = normalize(normalMatrix*normal); vV = normalize(-mv.xyz); gl_Position = projectionMatrix*mv; }',
    fragmentShader: 'varying vec2 vUv; varying vec3 vN; varying vec3 vV; void main(){ float edge = pow(abs(dot(vN, vV)), 1.6); gl_FragColor = vec4(vec3(1.0), 0.09 * edge * smoothstep(0.0, 0.6, vUv.y) * (0.4 + 0.6 * vUv.y)); }',
  }));
  cone.position.y = 2.5; g.add(cone);
  const tL = w('s15', 'less');
  panel(g, { w: 1.7, h: 0.25, x: 0, y: 2.35, z: -0.3, ppu: 640, boost: 1.3, key: t => (t < tL + 0.3 ? q(t) : 'd'), draw: (c, t, P) => {
    const n = Math.round(lerp(0, 50, prog(t, t0, Math.max(0.6, tL - t0), E_OUT)));
    lbl(c, `${n}${n >= 50 ? '+' : ''} hrs  /  week`, P.cw / 2, P.ch / 2, 56, C.white, { glow: 14 });
  } });
  for (let t = t0; t < tL; t += 0.12) sfx('tick', t, 0.3);
  camSet(t0, { x: 0, y: 1.3, z: 6.0, tx: 0, ty: 1.5, tz: 0, roll: 0, fov: 31 });
  camTo(t0, { z: 5.2, roll: -1.5 }, nextStart('s15') - t0, 'none');
});

// =====================================================================
// 16  DOLLAR — neon bill, FED TARGET ~2%/YR, value bleeds every year
// =====================================================================
shot(S('s16'), S('s17'), g => {
  const t0 = S('s16');
  resetLook(t0); cut(t0, 'zoom');
  g.add(dashedLine(80, 0.4, 0.3, 0.35));
  const tD = w('s16', 'designed'), tLo = w('s16', 'lose'), tE = w('s16', 'every'), tSi = w('s16', 'single'), tY = w('s16', 'year');
  const steps = [[tE, '$0.98', '2027'], [tSi, '$0.96', '2028'], [tY, '$0.94', '2029']];
  const step = t => { let s = ['$1.00', '2026'], n = 0; for (const [tt, v, y] of steps) if (t >= tt) { s = [v, y]; n++; } return [s, n]; };
  const bill = panel(g, { w: 1.5, h: 0.7, x: 0.05, y: 1.75, z: 0, ry: -0.3, rx: 0.05, rz: 0.05, ppu: 640, boost: 1.45, key: t => (t < tD + 1.2 ? q(t) : 'd') + step(t)[1], draw: (c, t, P) => {
    const k = prog(t, t0 + 0.05, 0.9, E_INOUT), [, n] = step(t), col = n ? (n > 1 ? '#ff8b96' : '#9cf7de') : C.mint;
    c.save(); c.globalAlpha = 0.25 + 0.75 * k;
    neonRect(c, 14, 14, (P.cw - 28), (P.ch - 28), col, { r: 22, lw: 7, glow: 26 - n * 6 });
    neonRect(c, 60, 56, P.cw - 120, P.ch - 112, col, { r: 12, lw: 3, glow: 10, fill: null });
    c.strokeStyle = col; c.lineWidth = 7; c.shadowColor = col; c.shadowBlur = 20; c.beginPath(); c.arc(P.cw / 2, P.ch / 2, 120, 0, Math.PI * 2 * k); c.stroke();
    big(c, '$', P.cw / 2, P.ch / 2 + 6, 170, col, { glow: 20 }); big(c, '1', 110, 120, 80, col); big(c, '1', P.cw - 110, P.ch - 110, 80, col);
    c.restore();
  } });
  sfx('swoosh', t0 + 0.05, 0.4);
  const hdr = hidden(panel(g, { w: 1.6, h: 0.14, x: 0.05, y: 2.32, z: -0.1, ry: -0.2, ppu: 640, draw: (c, t, P) => lbl(c, 'Fed target: lose ~2% a year', P.cw / 2, P.ch / 2, 34, C.red, { glow: 16 }) }).mesh);
  popScale(hdr, tLo - 0.1, { s: 'hit', gain: 0.5 });
  panel(g, { w: 1.3, h: 0.39, x: 0.05, y: 1.18, z: 0.1, ry: -0.2, ppu: 640, key: t => step(t)[1] + (steps.some(([tt]) => t > tt && t < tt + 0.3) ? q(t) : ''), draw: (c, t, P) => {
    const [[v, y], n] = step(t), last = steps[n - 1], pk = last ? prog(t, last[0], 0.3) : 1;
    lbl(c, 'Value', P.cw / 2 - 150, 80, 32, C.white, { align: 'right' });
    big(c, v, P.cw / 2 - 120, 82, 92 * (1 + (1 - pk) * 0.25), n ? C.red : C.white, { align: 'left', glow: 14 });
    lbl(c, y, P.cw / 2, 200, 30, C.grey);
  } });
  steps.forEach(([tt]) => { tl.to(bill.mesh.scale, { x: '-=0.07', y: '-=0.07', duration: 0.25, ease: 'back.out(3)' }, tt); shake(tt, 0.45, 0.3); flash(tt, 0.12, 0.2, C.red); sfx('hit', tt, 0.85); });
  const R = mulberry32(41), M = Array.from({ length: 36 }, (_, i) => [steps[i % 3][0] + R() * 0.25, (R() - 0.5) * 0.5, (R() - 0.5) * 0.5, 0.9 + R() * 0.8]);
  g.add(particles({ count: M.length, texture: MINUS2, size: 0.15, color: C.red, boost: 1.7, fn: (t, p, a) => M.forEach((d, i) => { const f = t - d[0]; p.set([-0.3 - f * d[3] * 1.2, 1.75 + d[1] + f * 0.15, d[2]], i * 3); a[i] = f > 0 && f < 1.5 ? 1 - f / 1.5 : 0; }) }));
  camSet(t0, { x: 0.6, y: 1.5, z: 5.6, tx: 0.05, ty: 1.65, tz: 0, roll: -6, fov: 31 });
  camTo(t0, { x: 0.3, z: 5.0 }, nextStart('s16') - t0, 'none');
});

// =====================================================================
// 17+18  SAFE → NOT SAFE, then the crowd you're paying for
// =====================================================================
shot(S('s17'), S('s19'), g => {
  const t0 = S('s17');
  resetLook(t0); cut(t0, 'zoom');
  music(t0, 0.7);
  g.add(dashedLine(120, 0.55, 0, 0.35));
  const you = figure({ glowOpacity: 0.7 }); you.position.set(-0.5, 0, 0.1); g.add(you);
  const tSit = w('s17', 'sitting'), tNot = w('s17', 'not'), tC = S('s18'), tFirst = w('s18', 'first');
  panel(g, { w: 0.82, h: 0.95, x: 0.42, y: 0.5, z: 0.05, ppu: 620, boost: 1.35, key: t => (t > tNot ? 'n' : 's'), draw: (c, t, P) => {
    const col = t > tNot ? C.red : C.white;
    neonRect(c, 12, 12, P.cw - 24, P.cw - 24, col, { r: 26, lw: 7, glow: 20 });
    const cx = P.cw / 2, cy = (P.cw - 24) / 2 + 12; c.save(); c.strokeStyle = col; c.lineWidth = 7; c.shadowColor = col; c.shadowBlur = 14;
    c.beginPath(); c.arc(cx, cy, 95, 0, 7); c.stroke(); for (let i = 0; i < 6; i++) { const a = i / 6 * Math.PI * 2 + 0.3; c.beginPath(); c.moveTo(cx, cy); c.lineTo(cx + Math.cos(a) * 95, cy + Math.sin(a) * 95); c.stroke(); } c.restore();
    lbl(c, '$1,000', P.cw / 2, P.ch - 50, 40, C.mint, { glow: 10 });
  } });
  const safe = panel(g, { w: 0.9, h: 0.3, x: 0.42, y: 1.12, z: 0.05, ppu: 640, key: t => (t < tNot + 0.6 ? q(t) : 'd'), draw: (c, t, P) => {
    lbl(c, 'Safe', P.cw / 2, 140, 46, t > tNot ? C.red : C.white, { glow: 10 });
    strikeLine(c, P.cw / 2 - 130, 140, P.cw / 2 + 130, 140, prog(t, tNot, 0.25), C.red, 7);
    if (t > tNot) { c.globalAlpha = prog(t, tNot + 0.1, 0.25); lbl(c, 'Not safe', P.cw / 2, 50, 46, C.red, { glow: 16 }); c.globalAlpha = 1; }
  } });
  const sit = panel(g, { w: 0.9, h: 0.14, x: -0.5, y: 1.48, z: 0.1, ppu: 640, draw: (c, t, P) => lbl(c, 'Sitting still', P.cw / 2, P.ch / 2, 32, C.white, { glow: 8 }) });
  fadeMat(sit.mat, tSit - 0.05, 1, 0.3, 0);
  sfx('stamp', tNot, 0.7); shake(tNot, 0.6, 0.4); floorTint(tNot, C.red, 0.9);
  // crowd reveal: everyone else gains, you pay
  const R = mulberry32(57), crowd = [];
  for (let i = 0; i < 18; i++) {
    const f = figure({ glow: C.mint, glowOpacity: 0.55 }); const x = (R() - 0.5) * 6.5, z = -1.2 - R() * 5.5;
    f.position.set(x, 0, z); f.scale.setScalar(0.55 + R() * 0.2); g.add(f); crowd.push(f);
    tl.fromTo(f.position, { y: -1.5 }, { y: 0, duration: 0.5, ease: 'power3.out' }, tC + 0.1 + i * 0.03);
  }
  g.add(particles({ count: crowd.length, texture: UP, size: 0.12, color: C.mint, boost: 2, fn: (t, p, a) => crowd.forEach((f, i) => { p.set([f.position.x, f.position.y + 1.35 * f.scale.x + 0.15 + Math.sin(t * 3 + i) * 0.03, f.position.z], i * 3); a[i] = clamp01((t - tC - 0.4 - i * 0.03) * 3); }) }));
  const flow = Array.from({ length: 80 }, () => [Math.floor(R() * crowd.length), R() * 1.3, 0.8 + R() * 0.6]);
  g.add(particles({ count: flow.length, texture: DOLLAR, size: 0.08, color: C.red, boost: 1.6, fn: (t, p, a) => flow.forEach(([k, off, sp], i) => {
    const f = ((t - tC - 0.5) * sp + off) % 1.3; if (t < tC + 0.5 || f > 1) { a[i] = 0; return; }
    const tgt = crowd[k].position, x = lerp(0.42, tgt.x, f), z = lerp(0.1, tgt.z, f), y = 0.6 + Math.sin(f * Math.PI) * 1.4;
    p.set([x, y, z], i * 3); a[i] = Math.sin(f * Math.PI);
  }) }));
  const minus = hidden(panel(g, { w: 0.8, h: 0.3, x: -0.5, y: 1.85, z: 0.1, ppu: 640, draw: (c, t, P) => big(c, '−$200', P.cw / 2, P.ch / 2, 130, C.red, { glow: 24 }) }).mesh);
  popScale(minus, w('s18', 'paying'), { s: 'boom', gain: 0.6 });
  sfx('down', tC + 0.4, 0.5, { dur: 1.4 });
  music(tC, 0.5);
  camSet(t0, { x: 0.15, y: 1.1, z: 5.2, tx: 0, ty: 0.95, tz: 0, roll: -3, fov: 31 });
  camTo(t0, { z: 4.7 }, tC - t0, 'none');
  camTo(tC - 0.1, { x: 0.6, y: 3.1, z: 6.8, tx: -0.1, ty: 0.4, tz: -1.8, roll: -4, fov: 34 }, 1.8, 'power3.inOut');
  camTo(tC + 1.7, { x: 0.3, z: 6.3 }, Math.max(0.5, nextStart('s18') - tC - 1.7), 'none');
});

// =====================================================================
// 19  CTA — PART 2: how to protect your money
// =====================================================================
shot(S('s19'), DUR + 1, g => {
  const t0 = S('s19');
  resetLook(t0); cut(t0, 'flash'); flash(t0, 0.3, 0.4, C.mint);
  music(t0, 0.9);
  floorTint(t0, C.mint, 0.7);
  const you = figure({ glow: C.mint, glowOpacity: 1, glowSize: 2.6 }); g.add(you);
  g.add(dashedLine(80, 0.55, 0, 0.35));
  const tF = w('s19', 'follow'), tP = w('s19', 'part'), tPr = w('s19', 'protect');
  const p2 = hidden(panel(g, { w: 2.1, h: 0.62, x: 0, y: 2.3, z: -0.3, ppu: 640, boost: 1.0, draw: (c, t, P) => { lbl(c, 'Next episode', P.cw / 2, 40, 24, C.mint); big(c, 'PART 2', P.cw / 2, 230, 250, C.mint, { glow: 12 }); } }).mesh);
  popScale(p2, tP - 0.05, { ease: 'expo.out', dur: 0.4, s: 'boom', gain: 0.7 });
  shake(tP, 0.6, 0.4); flash(tP, 0.25, 0.3, C.mint);
  const how = panel(g, { w: 2.2, h: 0.16, x: 0, y: 1.82, z: -0.3, ppu: 640, draw: (c, t, P) => lbl(c, 'How to protect your money', P.cw / 2, P.ch / 2, 40, C.white, { glow: 10 }) });
  fadeMat(how.mat, tPr - 0.2, 1, 0.4, 0);
  const fb = hidden(panel(g, { w: 1.0, h: 0.28, x: 0, y: 1.42, z: 0.2, ppu: 640, boost: 1.3, key: t => (t > tF + 0.45 ? 'on' : 'off'), draw: (c, t, P) => {
    const on = t > tF + 0.45;
    c.save(); c.beginPath(); c.roundRect(10, 10, P.cw - 20, P.ch - 20, (P.ch - 20) / 2); c.fillStyle = on ? 'rgba(255,255,255,.08)' : C.gold; c.shadowColor = C.gold; c.shadowBlur = on ? 0 : 30; c.fill();
    if (on) { c.strokeStyle = '#fff'; c.lineWidth = 4; c.stroke(); } c.restore();
    text(c, on ? '✓  FOLLOWING' : '+  FOLLOW', P.cw / 2, P.ch / 2 + 4, { size: 64, weight: 900, color: on ? '#fff' : '#120d02', spacing: 4 });
  } }).mesh);
  popScale(fb, tF - 0.1, { s: 'pop' });
  tl.fromTo(fb.scale, { x: 1.12, y: 1.12 }, { x: 1, y: 1, duration: 0.3, ease: 'back.out(3)', immediateRender: false }, tF + 0.45);
  sfx('click', tF + 0.45, 0.8); sfx('ding', tF + 0.5, 0.6);
  const R = mulberry32(77), M = Array.from({ length: 70 }, () => [(R() - 0.5) * 5, R() * 3, -R() * 4, 0.2 + R() * 0.4]);
  g.add(particles({ count: M.length, texture: TEX.glow, size: 0.04, color: C.mint, boost: 2, fn: (t, p, a) => M.forEach((d, i) => { const f = t - t0; p.set([d[0], (d[1] + f * d[3]) % 3.2, d[2]], i * 3); a[i] = clamp01(f) * 0.8; }) }));
  camSet(t0, { x: 0, y: 1.35, z: 5.6, tx: 0, ty: 1.55, tz: 0, roll: -2, fov: 30 });
  camTo(t0, { z: 5.0, roll: 0 }, DUR - t0, 'power1.out');
  music(DUR - 1.2, 0.9); music(DUR, 0);
});

tl.set({}, {}, DUR);
