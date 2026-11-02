
// ================================================================== MOVEMENTS (3D + radar)
function pickInset() {
  const ev = []; const rate = AP.insetRate || 2.3;
  for (const type of ['A', 'D']) for (let h = 0; h < 24; h++) {
    const fs = FL.filter(f => f.type === type && Math.floor(f.t / 60) === h);
    if (!fs.length) continue;
    const len = vidT((h + 1) * 60) - vidT(h * 60);
    const k = Math.min(fs.length, Math.max(1, Math.floor(len * rate)));
    for (let i = 0; i < k; i++) { const f = fs[Math.min(fs.length - 1, Math.floor((i + 0.5) * fs.length / k))]; ev.push({ type, t: vidT(f.t), m: f.t, rw: f.rw, r: f.r, cs: f.cs, cat: ROUTES[f.r].cat, wide: WIDE.has(f.ac), seed: (f.t * 13.7) % 1 }); }
  }
  return ev.sort((a, b) => a.t - b.t);
}
const INSET = pickInset();
const GA_EV = (AP.goArounds || []).map(g => { const f = FL.filter(x => x.type === 'A').reduce((a, b) => Math.abs(b.t - g.m) < Math.abs(a.t - g.m) ? b : a);
  return { type: 'G', t: vidT(g.m), m: g.m, rw: g.rw, r: f.r, cs: f.cs, cat: ROUTES[f.r].cat, wide: WIDE.has(f.ac), seed: 0.35 }; });
const INTRO_EV = AP.introEvents.map(e => ({ ...e, seed: 0.4, intro: true }));
const ALL_EV = INTRO_EV.concat(INSET, GA_EV).sort((a, b) => a.t - b.t);
const drawRadar = makeRadar(INSET.concat(GA_EV));

function goPose(tau, rw) {
  if (tau < -0.06) return arrPose(tau, rw);
  const R = RW[rw]; const xtd = R.e - 400; const u = tau + 0.06;
  return { x: xtd + 195 - (3300 * u + 400 * u * u), y: 17 + 480 * Math.pow(u, 1.2), z: R.z, hd: Math.PI, pitch: (3 + 8 * smooth(0, 0.3, u)) * D2R, alpha: 1 - smooth(1.6, 2.2, u), land: 1 - smooth(0.6, 1.0, u) };
}

const SHOTS = AP.shots;
const CUTS = SHOTS.slice(1).map(s => s.t0);
const V3 = a => new THREE.Vector3(a[0], a[1], a[2]);
function airportCam(t) {
  const IC = AP.introCam;
  if (t < T_RISE + 1.7) {
    const P0 = V3(IC.P0), P1 = V3(IC.P1), Q0 = V3(IC.Q0), Q1 = V3(IC.Q1);
    if (t <= T_RISE) { const u = smooth(0, 1, t / T_RISE) * 0.6 + (t / T_RISE) * 0.4; return { p: P0.lerp(P1, u), q: Q0.lerp(Q1, u), fov: 44, sc: 2.0, sf: 0.5 }; }
    const k = ease((t - T_RISE) / 1.5);
    return { p: new THREE.Vector3(lerp(P1.x, 400, k), P1.y * Math.pow(13, k), lerp(P1.z, 0, k)), q: new THREE.Vector3(lerp(Q1.x, -300, k), 0, lerp(Q1.z, 0, k)), fov: 44, sc: 2.0, sf: 0.5 };
  }
  let s = SHOTS[SHOTS.length - 1]; for (const x of SHOTS) if (t < x.t1) { s = x; break; }
  const u = clamp((t - s.t0) / (s.t1 - s.t0), 0, 1);
  if (s.orbit) { const O = s.orbit; const a = lerp(O.a0, O.a1, clamp((t - s.t0) / 15, 0, 1)); return { ...s, p: new THREE.Vector3(O.c[0] + O.r * Math.cos(a), O.h, O.c[2] + O.r * Math.sin(a)), q: V3(O.c) }; }
  return { ...s, p: V3(s.p0).lerp(V3(s.p1), u), q: V3(s.q0).lerp(V3(s.q1), u) };
}

function updateAirport(t, night, cam) {
  let pi = 0; const la = acLtGeo.attributes; let nl = 0; const v = new THREE.Vector3();
  for (const e of ALL_EV) {
    const tau = t - e.t; const sf = e.intro ? 0.5 : cam.sf; const te = tau * sf;
    let p = null;
    if (e.type === 'A') { if (te > -2.2 && te < 1.5) p = arrPose(te, e.rw); }
    else if (e.type === 'G') { if (te > -2.2 && te < 2.3) p = goPose(te, e.rw); }
    else if (te > -0.5 && te < 3.4) p = depPose(te, e.rw, e.seed);
    if (!p || p.alpha <= 0.001 || pi >= POOL.length) continue;
    const o = POOL[pi++]; const g = o.g; g.visible = true;
    const sc = (e.wide ? 1.85 : 1.0) * (e.intro ? 2.0 : cam.sc);
    g.scale.setScalar(sc); g.position.set(p.x, p.y + 2.6 * sc, p.z); g.rotation.set(0, p.hd, p.pitch, 'YZX');
    o.bm.opacity = o.tm.opacity = p.alpha; o.bm.depthWrite = o.tm.depthWrite = p.alpha > 0.95;
    o.tm.color.copy(CATC[e.cat]); o.tm.emissive.copy(CATC[e.cat]); o.tm.emissiveIntensity = 0.25 + 0.45 * night;
    o.bm.emissiveIntensity = 0.35 * night;
    g.updateMatrixWorld(true);
    for (const L of AC_LIGHTS) {
      let a = 1;
      if (L[5] === 1) a = (((t * 1.3 + e.seed) % 1) < 0.08) ? 1.4 : 0;
      else if (L[5] === 2) a = (((t * 1.0 + e.seed * 0.7) % 1) < 0.25) ? 1 : 0.1;
      else if (L[5] === 3) a = p.land * (0.3 + 0.9 * night);
      a *= p.alpha * (0.45 + 0.7 * night);
      if (a <= 0.01 || nl >= POOL.length * 8) continue;
      v.set(L[0], L[1], L[2]).applyMatrix4(g.matrixWorld);
      la.position.setXYZ(nl, v.x, v.y, v.z); la.acol.setXYZ(nl, ...L[3]); la.size.setX(nl, L[4] * (L[5] === 3 ? 1 : 1.6)); la.alpha.setX(nl, a); nl++;
    }
  }
  for (; pi < POOL.length; pi++) POOL[pi].g.visible = false;
  acLtGeo.setDrawRange(0, nl); for (const k of ['position', 'acol', 'size', 'alpha']) la[k].needsUpdate = true;
  const lt = ltGeo.attributes;
  for (let i = 0; i < LT.length; i++) {
    const L = LT[i]; let a = 0.35 + 0.85 * night;
    if (L.kind === 1) a = 0.15 + 0.95 * night;
    if (L.kind === 3) { const d = Math.abs(L.x - L.ref); const ph = ((t * 2.0) % 1); a = Math.abs(1 - d / 900 - ph) < 0.035 ? 1.6 * (0.3 + night) : 0; }
    if (L.kind === 4) a = ((t % 1.2) < 0.6 ? 1 : 0.2) * (0.5 + night);
    lt.alpha.setX(i, a);
  }
  lt.alpha.needsUpdate = true;
}

const CAMR = { x: 70, y: 1160, w: 426, h: 350 };
let aMode = '';
function setAMode(mode) {
  if (mode === aMode) return; aMode = mode; const c = $('glA');
  if (mode === 'full') { rA.setSize(W, H, false); Object.assign(c.style, { left: '0px', top: '0px', width: W + 'px', height: H + 'px', borderRadius: '0px' }); }
  else { rA.setSize(CAMR.w, CAMR.h, false); Object.assign(c.style, { left: CAMR.x + 'px', top: CAMR.y + 'px', width: CAMR.w + 'px', height: CAMR.h + 'px', borderRadius: '18px' }); }
}

const GK = AP.globe.keys, VIEWS = AP.globe.views;
function globeCam(t) {
  if (t <= GK[0][0]) return GK[0].slice(1);
  for (let i = 0; i < GK.length - 1; i++) if (t < GK[i + 1][0]) {
    const a = GK[i], b = GK[i + 1]; const k = ease((t - a[0]) / (b[0] - a[0]));
    return [lerp(a[1], b[1], k), lerp(a[2], b[2], k), Math.exp(lerp(Math.log(a[3]), Math.log(b[3]), k)), lerp(a[4], b[4], k)];
  }
  return GK[GK.length - 1].slice(1);
}
