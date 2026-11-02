
// ================================================================== ATC RADAR (2D)
const topo10 = await (await fetch('node_modules/world-atlas/land-10m.json')).json();
function makeRadar(EV) {
  const RC = AP.radar; const cv = $('radar'); const ctx = cv.getContext('2d');
  const Wd = cv.width, Hd = cv.height, cx = Wd / 2, cy = Hd / 2 + 8, Rpx = 156, ppn = Rpx / RC.range;
  const rot = (270 - RC.rwyTrue) * D2R;
  const toNM = (x, z) => { const xn = x / 1852, yn = -z / 1852; return [xn * Math.cos(rot) - yn * Math.sin(rot), xn * Math.sin(rot) + yn * Math.cos(rot)]; };
  const px = p => [cx + p[0] * ppn, cy - p[1] * ppn];
  const add2 = (a, b, k = 1) => [a[0] + b[0] * k, a[1] + b[1] * k];
  const uA = [Math.cos(rot), Math.sin(rot)], uD = [-uA[0], -uA[1]], perp = [-uA[1], uA[0]];
  const bvec = b => [Math.sin(b * D2R), Math.cos(b * D2R)];
  const bearingTo = (lat2, lon2) => { const f1 = AP.lat * D2R, f2 = lat2 * D2R, dl = (lon2 - AP.lon) * D2R; return (Math.atan2(Math.sin(dl) * Math.cos(f2), Math.cos(f1) * Math.sin(f2) - Math.sin(f1) * Math.cos(f2) * Math.cos(dl)) / D2R + 360) % 360; };
  // coastline rings near the airport (north-up NM)
  const land = feature(topo10, topo10.objects.land); const kx = Math.cos(AP.lat * D2R) * 60;
  const rings = [];
  for (const f of land.features) { const polys = f.geometry.type === 'Polygon' ? [f.geometry.coordinates] : f.geometry.coordinates;
    for (const poly of polys) for (const ring of poly) { const pts = ring.map(([lo, la]) => [(lo - AP.lon) * kx, (la - AP.lat) * 60]); if (pts.some(p => Math.hypot(p[0], p[1]) < RC.range * 1.6)) rings.push(pts); } }
  function fly(start, h0, wps, opt = {}) {
    const pts = [start.slice()]; let [x, y] = start; let h = h0; const ds = 0.2; const mt = (opt.turnRate || 24) * D2R * ds; let wi = 0, guard = 0;
    while (wi < wps.length && guard++ < 3000) {
      const [tx, ty] = wps[wi]; const dx = tx - x, dy = ty - y;
      if (Math.hypot(dx, dy) < (opt.capture || 0.9)) { wi++; continue; }
      let d = Math.atan2(dx, dy) - h; d = Math.atan2(Math.sin(d), Math.cos(d));
      if (opt.forceDir && Math.abs(d) > 1.75) d = opt.forceDir * Math.abs(d);
      h += clamp(d, -mt, mt); x += Math.sin(h) * ds; y += Math.cos(h) * ds; pts.push([x, y]);
      if (opt.maxLen && pts.length * ds > opt.maxLen) break;
    }
    return pts;
  }
  const straight = (pts, to) => { const a = pts[pts.length - 1]; const L = Math.hypot(to[0] - a[0], to[1] - a[1]); const n = Math.max(1, Math.round(L / 0.2)); for (let i = 1; i <= n; i++) pts.push([lerp(a[0], to[0], i / n), lerp(a[1], to[1], i / n)]); return pts; };
  const cum = pts => { const c = [0]; for (let i = 1; i < pts.length; i++) c.push(c[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1])); return c; };
  const at = (P, C, s) => { s = clamp(s, 0, C[C.length - 1]); let lo = 0, hi = C.length - 1; while (lo < hi - 1) { const m = (lo + hi) >> 1; if (C[m] <= s) lo = m; else hi = m; } const k = (s - C[lo]) / Math.max(1e-6, C[hi] - C[lo]); return [lerp(P[lo][0], P[hi][0], k), lerp(P[lo][1], P[hi][1], k)]; };
  const fixes = RC.fixes.map(f => ({ ...f, p: add2([0, 0], bvec(f.brg), f.dist) }));
  function arrivalPath(rw, brg, hold, seed) {
    const R = RW[rw]; const thr = toNM(R.e, R.z);
    const E = add2([0, 0], bvec(brg), RC.range + 3);
    const side = Math.sign(E[0] * uA[1] - E[1] * uA[0]) || 1; // which side of the final we come from
    const IP = add2(add2(thr, uA, 15), perp, -side * 4), FAF = add2(thr, uA, 10);
    const wps = []; let holdLoop = null;
    const dirE = Math.atan2(E[0], E[1]); const dirA = Math.atan2(uA[0], uA[1]);
    const straightIn = Math.abs(Math.atan2(Math.sin(dirE - dirA), Math.cos(dirE - dirA))) < 0.5;
    if (!straightIn) {
      let best = null, bd = 1e9; for (const f of fixes) { let d = Math.abs(((f.brg - brg) % 360 + 540) % 360 - 180); if (d < bd) { bd = d; best = f; } }
      if (best && bd < 75) { wps.push(best.p); if (hold && best.hold) { const out = [best.p[0] / Math.hypot(...best.p), best.p[1] / Math.hypot(...best.p)]; const sd = [-out[1], out[0]]; holdLoop = [add2(best.p, sd, 2), add2(add2(best.p, sd, 2), out, 4), add2(best.p, out, 4), best.p]; wps.push(...holdLoop); } }
    }
    wps.push(IP, FAF);
    const h0 = Math.atan2(-E[0], -E[1]);
    const P = straight(fly(E, h0, wps, { turnRate: 26 }), thr);
    return { P, C: cum(P), thr };
  }
  function departurePath(rw, brg) {
    const R = RW[rw]; const s0 = toNM(R.e - 60, R.z), P1 = add2(toNM(R.w, R.z), uD, RC.straightOut || 4);
    const P = straight([s0], P1);
    const tgt = add2([0, 0], bvec(brg), RC.range + 6);
    const more = fly(P1, Math.atan2(uD[0], uD[1]), [tgt], { turnRate: 18, forceDir: (RC.depTurn || {})[rw] || 0, capture: 2, maxLen: 80 });
    return { P: P.concat(more.slice(1)), C: null };
  }
  function goAroundPath(rw, side) {
    const R = RW[rw]; const thr = toNM(R.e, R.z);
    const G1 = add2(thr, uD, 4), G2 = add2(G1, perp, side * 4), G3 = add2(add2(thr, uA, 7), perp, side * 4), G4 = add2(thr, uA, 9);
    const P = straight(fly(thr, Math.atan2(uD[0], uD[1]), [G1, G2, G3, G4], { turnRate: 30 }), thr);
    return { P, C: cum(P) };
  }
  // build radar tracks for every movement shown at the airport (+ go-arounds)
  const TR = [];
  for (const e of EV) {
    if (e.intro || !e.r && e.r !== 0) continue;
    const rt = ROUTES[e.r]; const brg = bearingTo(rt.lat, rt.lon);
    const hold = hourRate(dayMin(e.t)) > RC.holdRate && e.seed < 0.55;
    if (e.type === 'A' || e.type === 'G') {
      const A = arrivalPath(e.rw, brg, hold, e.seed);
      const tr = { e, kind: e.type, A, code: rt.code, cs: e.cs };
      if (e.type === 'G') tr.G = goAroundPath(e.rw, e.seed < 0.5 ? 1 : -1);
      TR.push(tr);
    } else { const D = departurePath(e.rw, brg); D.C = cum(D.P); TR.push({ e, kind: 'D', D, code: rt.code, cs: e.cs }); }
  }
  const arrD = tau => tau <= 10 / 7 ? tau * 7 : 10 + (tau - 10 / 7) * 12;
  const depD = tau => tau < 1.4 ? 5 * tau * tau : 9.8 + (tau - 1.4) * 14;
  function state(tr, t) { // -> {p, prevFn, alt, col, ga}
    if (tr.kind === 'D') {
      const tau = t - tr.e.t; if (tau < 0) return null; const D = depD(tau); const L = tr.D.C[tr.D.C.length - 1]; if (D > L) return null;
      return { p: at(tr.D.P, tr.D.C, D), q: at(tr.D.P, tr.D.C, D + 1.2), hist: k => at(tr.D.P, tr.D.C, depD(Math.max(0, tau - k * 0.09))), alt: Math.min(17000, D * 850), col: '#38C8FF', dep: true };
    }
    const tau = tr.e.t - t; const L = tr.A.C[tr.A.C.length - 1];
    if (tau >= 0) { const D = arrD(tau); if (D > L) return null; const s = L - D;
      return { p: at(tr.A.P, tr.A.C, s), q: at(tr.A.P, tr.A.C, s + 1.2), hist: k => at(tr.A.P, tr.A.C, L - arrD(tau + k * 0.09)), alt: D < 10 ? D * 318 : Math.min(12000, 3200 + (D - 10) * 320), col: tr.kind === 'G' ? '#3DF5A0' : '#3DF5A0' }; }
    if (tr.kind === 'A') return null;
    const s2 = -tau * 9; const LG = tr.G.C[tr.G.C.length - 1]; if (s2 > LG) return null;
    const ga = s2 < LG * 0.55;
    return { p: at(tr.G.P, tr.G.C, s2), q: at(tr.G.P, tr.G.C, s2 + 1.2), hist: k => at(tr.G.P, tr.G.C, Math.max(0, s2 - k * 0.8)), alt: Math.min(3000, s2 * 700) * (s2 < LG * 0.7 ? 1 : (LG - s2) / (LG * 0.3)), col: '#FFB547', ga, gaAge: -tau };
  }
  // static map layer
  const base = document.createElement('canvas'); base.width = Wd; base.height = Hd; const b = base.getContext('2d');
  { const gr = b.createRadialGradient(cx, cy, 0, cx, cy, Rpx * 1.3); gr.addColorStop(0, '#061a1f'); gr.addColorStop(1, '#020a0d'); b.fillStyle = gr; b.fillRect(0, 0, Wd, Hd);
    b.save(); b.beginPath(); b.rect(0, 0, Wd, Hd); b.clip();
    b.fillStyle = 'rgba(40,90,80,0.22)'; b.strokeStyle = 'rgba(80,190,170,0.55)'; b.lineWidth = 1.1;
    for (const ring of rings) { b.beginPath(); ring.forEach((p, i) => { const [X, Y] = px(p); i ? b.lineTo(X, Y) : b.moveTo(X, Y); }); b.closePath(); b.fill(); b.stroke(); }
    b.restore();
    b.strokeStyle = 'rgba(90,200,180,0.22)'; b.lineWidth = 1; b.fillStyle = 'rgba(120,210,190,0.55)'; b.font = '600 10px Inter';
    for (let rr = 10; rr <= RC.range; rr += 10) { b.beginPath(); b.arc(cx, cy, rr * ppn, 0, 6.283); b.stroke(); b.fillText(rr + '', cx + rr * ppn * 0.707 + 3, cy - rr * ppn * 0.707 - 3); }
    for (let a = 0; a < 360; a += 10) { const v = bvec(a); const r0 = Rpx - (a % 30 === 0 ? 8 : 4); b.beginPath(); b.moveTo(cx + v[0] * r0, cy - v[1] * r0); b.lineTo(cx + v[0] * Rpx, cy - v[1] * Rpx); b.stroke(); }
    b.fillStyle = 'rgba(150,230,210,0.8)'; b.font = '700 11px Inter'; b.textAlign = 'center'; b.textBaseline = 'middle';
    for (const [l, a] of [['N', 0], ['E', 90], ['S', 180], ['W', 270]]) { const v = bvec(a); b.fillText(l, cx + v[0] * (Rpx + 10), cy - v[1] * (Rpx + 10)); }
    // places
    b.font = '600 10px Inter'; b.fillStyle = 'rgba(140,200,190,0.55)';
    for (const pl of RC.places || []) { const p = px(add2([0, 0], bvec(pl.brg), pl.dist)); b.fillText(pl.name, p[0], p[1]); }
    // final approach courses
    const arrR = [...new Set(EV.filter(e => e.type === 'A').map(e => e.rw))];
    b.setLineDash([4, 4]); b.strokeStyle = 'rgba(61,245,160,0.35)';
    for (const rw of arrR) { const R = RW[rw]; const thr = toNM(R.e, R.z); const a = px(thr), c = px(add2(thr, uA, 16)); b.beginPath(); b.moveTo(a[0], a[1]); b.lineTo(c[0], c[1]); b.stroke(); }
    b.setLineDash([]);
    // fixes + holding patterns
    for (const f of fixes) { const [X, Y] = px(f.p); b.strokeStyle = 'rgba(200,220,255,0.6)'; b.beginPath(); b.moveTo(X, Y - 5); b.lineTo(X + 4.5, Y + 3.5); b.lineTo(X - 4.5, Y + 3.5); b.closePath(); b.stroke();
      if (f.hold) { const out = [f.p[0] / Math.hypot(...f.p), f.p[1] / Math.hypot(...f.p)]; const sd = [-out[1], out[0]]; b.setLineDash([3, 3]); b.strokeStyle = 'rgba(255,181,71,0.35)'; b.beginPath();
        const A1 = px(f.p), A2 = px(add2(f.p, out, 4)), A3 = px(add2(add2(f.p, out, 4), sd, 2)), A4 = px(add2(f.p, sd, 2));
        b.moveTo(...A1); b.lineTo(...A2); b.quadraticCurveTo(...px(add2(add2(f.p, out, 5.2), sd, 1)), ...A3); b.lineTo(...A4); b.quadraticCurveTo(...px(add2(add2(f.p, out, -1.2), sd, 1)), ...A1); b.stroke(); b.setLineDash([]); }
      b.fillStyle = 'rgba(200,220,255,0.7)'; b.font = '600 9px Inter'; b.fillText(f.name, X, Y + 12); }
    // runways
    b.strokeStyle = '#e8f2ff'; b.lineWidth = 2.4; b.lineCap = 'round';
    for (const k in RW) { const R = RW[k]; const a = px(toNM(R.w, R.z)), c = px(toNM(R.e, R.z)); b.beginPath(); b.moveTo(...a); b.lineTo(...c); b.stroke(); }
  }
  return function draw(t, m) {
    ctx.drawImage(base, 0, 0);
    // sweep
    const sw = ((t * 360 / 3.2) % 360);
    const g = ctx.createConicGradient((sw - 90) * D2R - 0.9, cx, cy);
    g.addColorStop(0, 'rgba(80,255,200,0)'); g.addColorStop(0.14, 'rgba(80,255,200,0.16)'); g.addColorStop(0.1435, 'rgba(80,255,200,0.0)'); g.addColorStop(1, 'rgba(80,255,200,0)');
    ctx.save(); ctx.beginPath(); ctx.arc(cx, cy, Rpx, 0, 6.283); ctx.clip(); ctx.fillStyle = g; ctx.fillRect(0, 0, Wd, Hd);
    const lv = bvec(sw); ctx.strokeStyle = 'rgba(120,255,210,0.55)'; ctx.lineWidth = 1.2; ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(cx + lv[0] * Rpx, cy - lv[1] * Rpx); ctx.stroke(); ctx.restore();
    // targets
    let alert = null;
    ctx.font = '700 10.5px Inter'; ctx.textAlign = 'left'; ctx.textBaseline = 'alphabetic';
    const labels = [];
    for (const tr of TR) {
      const s = state(tr, t); if (!s) continue;
      const [X, Y] = px(s.p); if (Math.hypot(X - cx, Y - cy) > Rpx + 2) continue;
      const ang = (Math.atan2(s.p[0], s.p[1]) / D2R + 360) % 360; const since = ((sw - ang) % 360 + 360) % 360;
      const br = 0.62 + 0.38 * Math.exp(-since / 50);
      ctx.fillStyle = s.col;
      for (let k = 1; k <= 5; k++) { const hp = px(s.hist(k)); ctx.globalAlpha = br * (0.55 - k * 0.09); ctx.beginPath(); ctx.arc(hp[0], hp[1], 1.4, 0, 6.283); ctx.fill(); }
      ctx.globalAlpha = br; const [QX, QY] = px(s.q); const dx = QX - X, dy = QY - Y, dl = Math.hypot(dx, dy) || 1;
      ctx.strokeStyle = s.col; ctx.lineWidth = 1.1; ctx.beginPath(); ctx.moveTo(X, Y); ctx.lineTo(X + dx / dl * 11, Y + dy / dl * 11); ctx.stroke();
      ctx.shadowColor = s.col; ctx.shadowBlur = 6; ctx.fillRect(X - 2.6, Y - 2.6, 5.2, 5.2); ctx.shadowBlur = 0;
      labels.push({ X, Y, s, tr, br });
      if (s.ga && s.gaAge < 1.8) alert = tr;
    }
    // data blocks (callsign / altitude + origin or destination), greedy placement to avoid overlaps
    const placed = [{ x0: cx - 22, y0: cy - 16, x1: cx + 22, y1: cy + 16 }, { x0: 0, y0: 0, x1: Wd, y1: 28 }, { x0: 0, y0: Hd - 24, x1: Wd, y1: Hd }];
    labels.sort((a, b) => Math.hypot(b.X - cx, b.Y - cy) - Math.hypot(a.X - cx, a.Y - cy));
    for (const L of labels) {
      const { X, Y, s, tr } = L; let lx = 0, ly = 0, ok = false;
      for (const [ox, oy] of [[8, -9], [8, 15], [-58, -9], [-58, 15]]) {
        const bx = { x0: X + ox - 1, y0: Y + oy - 10, x1: X + ox + 54, y1: Y + oy + 13 };
        if (bx.x0 < 2 || bx.x1 > Wd - 2) continue;
        if (!placed.some(p => !(bx.x1 < p.x0 || bx.x0 > p.x1 || bx.y1 < p.y0 || bx.y0 > p.y1))) { placed.push(bx); lx = X + ox; ly = Y + oy; ok = true; break; }
      }
      if (!ok) continue;
      ctx.globalAlpha = L.br * 0.95; ctx.strokeStyle = s.col; ctx.lineWidth = 0.8; ctx.beginPath(); ctx.moveTo(X + (lx > X ? 3 : -3), Y - 3); ctx.lineTo(lx + (lx > X ? -1 : 50), ly + 2); ctx.stroke();
      ctx.fillStyle = s.col; ctx.font = '700 10.5px Inter'; ctx.fillText(tr.cs, lx, ly);
      ctx.fillStyle = 'rgba(225,240,245,0.9)'; ctx.font = '600 9.5px Inter';
      const alt = String(Math.max(0, Math.round(s.alt / 100))).padStart(3, '0');
      ctx.fillText(s.ga ? `${alt} GO AROUND` : `${alt} ${s.dep ? '▸' : '◂'}${tr.code}`, lx, ly + 11);
    }
    ctx.globalAlpha = 1;
    // header / footer overlays
    ctx.fillStyle = 'rgba(4,14,18,0.78)'; ctx.fillRect(0, 0, Wd, 26); ctx.fillRect(0, Hd - 22, Wd, 22);
    ctx.font = '800 12px Inter'; ctx.fillStyle = '#7dffd6'; ctx.textBaseline = 'middle'; ctx.fillText('ATC RADAR · ' + RC.name, 12, 14);
    const utc = ((Math.floor(m) - AP.utcOff * 60) % 1440 + 1440) % 1440;
    ctx.textAlign = 'right'; ctx.fillStyle = '#c9f5ea'; ctx.fillText(`${RC.range} NM · ${pad2(Math.floor(utc / 60))}${pad2(utc % 60)}Z`, Wd - 12, 14);
    ctx.textAlign = 'left'; ctx.font = '700 10px Inter';
    let x = 12; for (const [c, l] of [['#3DF5A0', 'ARRIVAL'], ['#38C8FF', 'DEPARTURE'], ['#FFB547', 'GO-AROUND']]) { ctx.fillStyle = c; ctx.fillRect(x, Hd - 14, 7, 7); ctx.fillStyle = '#cfe9e4'; ctx.fillText(l, x + 11, Hd - 10); x += ctx.measureText(l).width + 26; }
    ctx.textAlign = 'right'; ctx.fillStyle = '#9fc9c2'; ctx.fillText(AP.rwyText(m), Wd - 12, Hd - 10); ctx.textAlign = 'left';
    if (alert) { const on = (t * 3) % 1 < 0.6; ctx.fillStyle = `rgba(255,181,71,${on ? 0.92 : 0.6})`; ctx.fillRect(Wd / 2 - 120, 32, 240, 22); ctx.fillStyle = '#1a1000'; ctx.font = '800 11.5px Inter'; ctx.textAlign = 'center'; ctx.fillText(`⚠ GO-AROUND · ${alert.cs} · RWY ${alert.e.rw}`, Wd / 2, 43.5); ctx.textAlign = 'left'; }
  };
}
