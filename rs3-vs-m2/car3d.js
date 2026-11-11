// Parametric 3D cars + studio, rendered with three.js (WebGL; SwiftShader when headless).
// Bodies are lofted from cross-sections built from each car's real dimensions and
// silhouette; glass, wheels, lights, grilles and badges are added on top. These are
// close approximations for motion graphics, not manufacturer CAD.
import * as THREE from 'three';

/* ---------------------------------------------------------------- maths */
function monotone(pts) { // Fritsch–Carlson monotone cubic through [[x, y], ...] (any x order)
  const P = [...pts].sort((a, b) => a[0] - b[0]), n = P.length;
  const dx = [], m = [], d = [];
  for (let i = 0; i < n - 1; i++) { dx[i] = P[i + 1][0] - P[i][0]; d[i] = (P[i + 1][1] - P[i][1]) / dx[i]; }
  m[0] = d[0]; m[n - 1] = d[n - 2];
  for (let i = 1; i < n - 1; i++) m[i] = d[i - 1] * d[i] <= 0 ? 0 : (d[i - 1] + d[i]) / 2;
  for (let i = 0; i < n - 1; i++) {
    if (d[i] === 0) { m[i] = m[i + 1] = 0; continue; }
    const a = m[i] / d[i], b = m[i + 1] / d[i], s = a * a + b * b;
    if (s > 9) { const t = 3 / Math.sqrt(s); m[i] = t * a * d[i]; m[i + 1] = t * b * d[i]; }
  }
  return x => {
    if (x <= P[0][0]) return P[0][1];
    if (x >= P[n - 1][0]) return P[n - 1][1];
    let i = 0; while (x > P[i + 1][0]) i++;
    const h = dx[i], t = (x - P[i][0]) / h, t2 = t * t, t3 = t2 * t;
    return (2 * t3 - 3 * t2 + 1) * P[i][1] + (t3 - 2 * t2 + t) * h * m[i] + (-2 * t3 + 3 * t2) * P[i + 1][1] + (t3 - t2) * h * m[i + 1];
  };
}
function chaikin(pts, iters = 2) { // pts: [{z, y, tag}]; keeps end points
  let p = pts;
  for (let k = 0; k < iters; k++) {
    const q = [p[0]];
    for (let i = 0; i < p.length - 1; i++) {
      const a = p[i], b = p[i + 1];
      if (a.sharp || b.sharp) { if (i > 0) q.push(a); continue; }
      q.push({ z: 0.75 * a.z + 0.25 * b.z, y: 0.75 * a.y + 0.25 * b.y, tag: a.tag });
      q.push({ z: 0.25 * a.z + 0.75 * b.z, y: 0.25 * a.y + 0.75 * b.y, tag: a.tag });
    }
    q.push(p[p.length - 1]);
    p = q;
  }
  return p;
}
function resample(pts, M) { // arc-length resample a polyline to M points, carrying tags
  const L = [0];
  for (let i = 1; i < pts.length; i++) L[i] = L[i - 1] + Math.hypot(pts[i].z - pts[i - 1].z, pts[i].y - pts[i - 1].y);
  const total = L[L.length - 1] || 1, out = [];
  let j = 0;
  for (let k = 0; k < M; k++) {
    const s = total * k / (M - 1);
    while (j < pts.length - 2 && L[j + 1] < s) j++;
    const seg = L[j + 1] - L[j] || 1, f = Math.min(1, Math.max(0, (s - L[j]) / seg));
    out.push({ z: pts[j].z + (pts[j + 1].z - pts[j].z) * f, y: pts[j].y + (pts[j + 1].y - pts[j].y) * f, tag: f < 0.5 ? pts[j].tag : pts[j + 1].tag });
  }
  return out;
}
const inRanges = (x, rs) => rs.some(([a, b]) => x >= a && x <= b);

/* ---------------------------------------------------------------- body */
function buildBody(S) {
  const top = monotone(S.top), bot = monotone(S.bottom), belt = monotone(S.belt);
  const half = S.W / 2, Lh = S.L / 2;
  const axles = [{ x: S.xf, R: S.Rf }, { x: S.xr, R: S.Rr }];
  // plan view: straight flanks with rounded corners (radius rF / rR) at the ends,
  // returned as a fraction of the half width
  const base = x => {
    const r = x >= 0 ? S.rF : S.rR, d = Math.max(0, Lh - Math.abs(x));
    if (d >= r) return 1;
    const t = 1 - d / r, h = S.Wb / 2;
    return ((h - r * 0.8) + r * 0.8 * Math.pow(Math.max(0, 1 - Math.pow(t, S.cornerP || 2.2)), 1 / (S.cornerP || 2.2))) / h;
  };
  const fn = v => Array.isArray(v) ? monotone(v) : () => v;
  const creaseIn = fn(S.creaseIn), roofRatio = fn(S.roofRatio), ledge = fn(S.ledge);
  const widthBase = x => S.Wb / 2 * base(x);   // body width between the arches
  const flareAt = x => axles.reduce((f, a, i) => f + (i ? S.flareR : S.flareF) * Math.exp(-Math.pow((x - a.x) / S.flareLen, 2)), 0) * Math.pow(base(x), 0.25);
  const width = x => widthBase(x) + flareAt(x);  // widest point (the crease), including the arch flares
  const crease = S.crease ? monotone(S.crease) : null;
  const section = x => {
    const yb = bot(x), yt = Math.max(top(x), yb + 0.02), w = width(x), wb = widthBase(x);
    const inGh = x <= S.gh[1] && x >= S.gh[0];
    const yBelt = inGh ? Math.min(belt(x), yt) : yt;
    const ghH = yt - yBelt;
    const ySh = inGh ? yBelt : yt - Math.min(0.09, (yt - yb) * 0.25);
    const yC = Math.max(yb + 0.08, Math.min(ySh - 0.045, crease ? crease(x) : ySh - 0.14));
    let arch = null;
    for (const a of axles) {
      const ra = a.R + S.archGap, dx = x - a.x;
      if (Math.abs(dx) < ra) arch = { y: a.R + Math.sqrt(ra * ra - dx * dx) * S.archRound, well: S.track / 2 - S.tyreW / 2 - 0.03 };
    }
    // lower half: underside -> (wheel arch) -> door -> crease; upper half: crease -> shoulder -> glass -> roof.
    // Each half is resampled separately so the crease stays a crisp line along the car.
    const under = [{ z: 0, y: yb, tag: 'under' }];
    let archY = -1, lip;
    if (arch && arch.y > yb + 0.03) {
      const wl = Math.min(arch.well, w - 0.05);
      archY = Math.min(arch.y, yC - 0.012);
      under.push({ z: wl, y: yb, tag: 'well', sharp: true }, { z: wl, y: archY, tag: 'well', sharp: true });
      lip = { z: w - 0.008, y: archY, tag: 'side' };
    } else {
      under.push({ z: w - 0.11, y: yb, tag: 'under' });
      lip = { z: w - 0.045, y: yb + 0.018, tag: 'side' };
    }
    under.push(lip);
    const lower = [lip];
    for (const q of [{ z: w - 0.032, y: yb + 0.1 }, { z: w - 0.022, y: yb + (yC - yb) * 0.55 }, { z: w - 0.007, y: yC - 0.07 }])
      if (q.y > archY + 0.015 && q.y < yC - 0.01) lower.push({ ...q, tag: 'side' });
    lower.push({ z: w, y: yC, tag: 'side' });
    const wu = wb + flareAt(x) * 0.25 - creaseIn(x) * base(x);
    const upper = [{ z: w, y: yC, tag: 'side' }, { z: wu, y: yC + (ySh - yC) * 0.45, tag: 'side' }, { z: wu - 0.012, y: ySh - 0.03, tag: 'side' }];
    if (inGh && ghH > 0.03) {
      const wg = wu - ledge(x), wr = wb * roofRatio(x);
      upper.push({ z: wu - ledge(x) * 0.6, y: ySh, tag: 'side' });
      upper.push({ z: wg, y: ySh + 0.012, tag: 'gh' });
      upper.push({ z: wr + 0.035, y: yt - 0.05, tag: 'gh' });
      upper.push({ z: wr - 0.03, y: yt - 0.012, tag: 'edge' });
      upper.push({ z: wr - 0.09, y: yt - 0.001, tag: 'roof' });
      upper.push({ z: 0, y: yt + 0.006, tag: 'roof' });
    } else {
      upper.push({ z: wu - 0.1, y: yt - 0.012, tag: 'top' });
      upper.push({ z: 0, y: yt + 0.008, tag: 'top' });
    }
    const nUn = Math.round(S.M * 0.16), nLo = Math.round(S.M * 0.3);
    const un = resample(chaikin(under, 1), nUn), lo = resample(chaikin(lower, 2), nLo), up = resample(chaikin(upper, 2), S.M - nUn - nLo + 2);
    return [...un, ...lo.slice(1), ...up.slice(1)];
  };
  // stations along the length, denser at the ends and around the arches
  const xs = [];
  const N = S.N;
  for (let i = 0; i <= N; i++) { const u = i / N; xs.push(-Lh + S.L * (0.5 - 0.5 * Math.cos(Math.PI * u))); }
  const M = S.M, ring = 2 * M - 1;
  const pos = new Float32Array(xs.length * ring * 3), tags = [];
  xs.forEach((x, i) => {
    const sec = section(x);
    const full = [...sec.slice().reverse().map(p => ({ ...p, z: -p.z })), ...sec.slice(1)];
    const cap = i === 0 || i === xs.length - 1;
    full.forEach((p, k) => {
      const o = (i * ring + k) * 3;
      pos[o] = x; pos[o + 1] = cap ? (sec[0].y + sec[sec.length - 1].y) / 2 : p.y; pos[o + 2] = cap ? 0 : p.z;
      tags.push(classify(S, x, p));
    });
  });
  const groups = { paint: [], glass: [], black: [], roof: [] };
  for (let i = 0; i < xs.length - 1; i++) {
    for (let k = 0; k < ring - 1; k++) {
      const a = i * ring + k, b = a + 1, c = a + ring, d = c + 1;
      for (const tri of [[a, c, b], [b, c, d]]) {
        const t = tri.map(v => tags[v]);
        const g = t.filter(v => v === 'glass').length >= 2 ? 'glass' : t.filter(v => v === 'roof').length >= 2 ? 'roof' : t.filter(v => v === 'black').length >= 2 ? 'black' : 'paint';
        groups[g].push(...tri);
      }
    }
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  const index = [], order = ['paint', 'glass', 'black', 'roof'];
  order.forEach((g, gi) => { geo.addGroup(index.length, groups[g].length, gi); index.push(...groups[g]); });
  geo.setIndex(index);
  geo.computeVertexNormals();
  return { geo, width, widthBase, top, bot, belt, ledge, roofRatio, creaseIn,
    upperWidth: x => widthBase(x) + flareAt(x) * 0.25 - creaseIn(x) * base(x) };
}
function classify(S, x, p) {  // glass, trim and badges are decals; the shell is paint
  return p.tag === 'under' || p.tag === 'well' ? 'black' : 'paint';
}

/* ---------------------------------------------------------------- decals */
function canvasTex(w, h, draw, flip = false) {
  const c = document.createElement('canvas'); c.width = w; c.height = h;
  const g = c.getContext('2d');
  if (flip) { g.translate(w, 0); g.scale(-1, 1); }
  draw(g, w, h);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4;
  return t;
}
// Fast projection onto the body: triangles are binned on a grid in the projection plane,
// so each ray only tests the few triangles under it.
const AX = { '+x': [2, 1, 0, 1], '-x': [2, 1, 0, -1], '+z': [0, 1, 2, 1], '-z': [0, 1, 2, -1], '+y': [0, 2, 1, 1] }; // u axis, v axis, depth axis, sign
function projector(geo) {
  const P = geo.attributes.position.array, I = geo.index.array, cache = {};
  return axis => {
    if (cache[axis]) return cache[axis];
    const [ua, va, da, sg] = AX[axis], cell = 0.05, bins = new Map();
    for (let t = 0; t < I.length; t += 3) {
      let u0 = 1e9, u1 = -1e9, v0 = 1e9, v1 = -1e9;
      for (let k = 0; k < 3; k++) { const o = I[t + k] * 3; u0 = Math.min(u0, P[o + ua]); u1 = Math.max(u1, P[o + ua]); v0 = Math.min(v0, P[o + va]); v1 = Math.max(v1, P[o + va]); }
      for (let i = Math.floor(u0 / cell); i <= Math.floor(u1 / cell); i++) for (let j = Math.floor(v0 / cell); j <= Math.floor(v1 / cell); j++) {
        const key = i * 4096 + j; let l = bins.get(key); if (!l) bins.set(key, l = []); l.push(t);
      }
    }
    // returns [x, y, z, facing] of the outermost surface point at (u, v), or null
    return cache[axis] = (u, v) => {
      const l = bins.get(Math.floor(u / cell) * 4096 + Math.floor(v / cell)); if (!l) return null;
      let best = null, bd = -1e9;
      for (const t of l) {
        const a = I[t] * 3, b = I[t + 1] * 3, c = I[t + 2] * 3;
        const au = P[a + ua], av = P[a + va], bu = P[b + ua], bv = P[b + va], cu = P[c + ua], cv = P[c + va];
        const den = (bv - cv) * (au - cu) + (cu - bu) * (av - cv); if (Math.abs(den) < 1e-12) continue;
        const l1 = ((bv - cv) * (u - cu) + (cu - bu) * (v - cv)) / den, l2 = ((cv - av) * (u - cu) + (au - cu) * (v - cv)) / den, l3 = 1 - l1 - l2;
        if (l1 < -1e-6 || l2 < -1e-6 || l3 < -1e-6) continue;
        const dep = sg * (l1 * P[a + da] + l2 * P[b + da] + l3 * P[c + da]);
        if (dep > bd) {
          bd = dep;
          const e1 = [P[b] - P[a], P[b + 1] - P[a + 1], P[b + 2] - P[a + 2]], e2 = [P[c] - P[a], P[c + 1] - P[a + 1], P[c + 2] - P[a + 2]];
          const n = [e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0]], nl = Math.hypot(...n) || 1;
          best = { l1, l2, l3, a, b, c, f: Math.abs(n[da]) / nl };
        }
      }
      if (!best) return null;
      const { l1, l2, l3, a, b, c } = best;
      return [0, 1, 2].map(k => l1 * P[a + k] + l2 * P[b + k] + l3 * P[c + k]).concat(best.f);
    };
  };
}
// Project a textured patch onto the body along an axis. rect = [u0, v0, u1, v1] in the
// plane perpendicular to `axis`: (z, y) for '+x' front / '-x' rear, (x, y) for '+z' / '-z'
// sides, (x, z) for '+y' top. Cells where the surface turns away at a grazing angle are
// dropped, so a front or rear decal never smears down the flanks.
const decalGeoCache = new Map();
function decal(body, rect, axis, mats, segs = [40, 20], minFacing = 0.3, reach = 9) {
  // reach: how far in from the outermost hit a surface may still take the decal
  const key = [body.uuid, axis, ...rect, ...segs, minFacing, reach].join(',');
  if (decalGeoCache.has(key)) return new THREE.Mesh(decalGeoCache.get(key), mats);
  const [u0, v0, u1, v1] = rect, [nu, nv] = segs, [ua, va, da, sg] = AX[axis];
  const proj = (body.userData.proj ||= projector(body.geometry))(axis);
  const pos = [], uv = [], idx = [], face = [];
  for (let j = 0; j <= nv; j++) for (let i = 0; i <= nu; i++) {
    const u = u0 + (u1 - u0) * i / nu, v = v0 + (v1 - v0) * j / nv;
    const h = proj(u, v), p = [0, 0, 0];
    if (h) { p[0] = h[0]; p[1] = h[1]; p[2] = h[2]; p[da] += sg * 0.003; } else { p[ua] = u; p[va] = v; }
    pos.push(...p); uv.push(i / nu, j / nv); face.push(h ? h[3] : 0);
  }
  let outer = -1e9;
  for (let k = 0; k < face.length; k++) if (face[k] > 0) outer = Math.max(outer, sg * pos[k * 3 + da]);
  for (let k = 0; k < face.length; k++) if (sg * pos[k * 3 + da] < outer - reach) face[k] = 0;
  const flipWinding = axis === '-x' || axis === '+z';
  for (let j = 0; j < nv; j++) for (let i = 0; i < nu; i++) {
    const a = j * (nu + 1) + i, b = a + 1, c = a + nu + 1, e = c + 1;
    if (Math.min(face[a], face[b], face[c], face[e]) < minFacing) continue;
    if (flipWinding) idx.push(a, b, c, b, e, c); else idx.push(a, c, b, b, c, e);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  g.setIndex(idx); g.computeVertexNormals();
  decalGeoCache.set(key, g);
  return new THREE.Mesh(g, mats);
}

/* ---------------------------------------------------------------- wheels */
function buildWheel(S, R) {
  const g = new THREE.Group();
  const tw = S.tyreW, rimR = S.rimR;
  const prof = [];
  for (let i = 0; i <= 16; i++) { const a = -Math.PI / 2 + Math.PI * i / 16; prof.push(new THREE.Vector2(R - 0.035 + Math.cos(a) * 0.035, Math.sin(a) * tw / 2)); }
  prof.unshift(new THREE.Vector2(rimR, -tw / 2)); prof.push(new THREE.Vector2(rimR, tw / 2));
  const tyre = new THREE.Mesh(new THREE.LatheGeometry(prof, 48), new THREE.MeshStandardMaterial({ color: 0x0c0c0e, roughness: 0.85 }));
  tyre.rotation.x = Math.PI / 2; g.add(tyre);
  const barrel = new THREE.Mesh(new THREE.CylinderGeometry(rimR, rimR, tw * 0.9, 40, 1, true), new THREE.MeshStandardMaterial({ color: 0x1a1b1e, roughness: 0.5, metalness: 0.6, side: THREE.DoubleSide }));
  barrel.rotation.x = Math.PI / 2; g.add(barrel);
  const disc = new THREE.Mesh(new THREE.CylinderGeometry(rimR * 0.82, rimR * 0.82, 0.03, 40), new THREE.MeshStandardMaterial({ color: 0x6d7076, roughness: 0.35, metalness: 0.8 }));
  disc.rotation.x = Math.PI / 2; disc.position.z = 0.02; g.add(disc);
  const cal = new THREE.Mesh(new THREE.TorusGeometry(rimR * 0.7, 0.045, 10, 16, 1.1), new THREE.MeshStandardMaterial({ color: S.caliper, roughness: 0.35, metalness: 0.2 }));
  cal.rotation.z = Math.PI * 0.55; cal.position.z = 0.06; cal.userData.static = true; g.add(cal);
  // spokes: extruded face
  const sh = new THREE.Shape(); sh.absarc(0, 0, rimR, 0, Math.PI * 2, false);
  const n = S.spokes, hubR = rimR * 0.22;
  for (let i = 0; i < n; i++) {
    const a0 = (i / n) * Math.PI * 2, gap = (Math.PI * 2 / n) * (1 - S.spokeFill);
    const hole = new THREE.Path();
    const r1 = hubR + 0.02, r2 = rimR - 0.018, a = a0 + Math.PI / n;
    hole.moveTo(Math.cos(a - gap / 2 * 0.55) * r1, Math.sin(a - gap / 2 * 0.55) * r1);
    hole.lineTo(Math.cos(a - gap / 2) * r2, Math.sin(a - gap / 2) * r2);
    hole.absarc(0, 0, r2, a - gap / 2, a + gap / 2, false);
    hole.lineTo(Math.cos(a + gap / 2 * 0.55) * r1, Math.sin(a + gap / 2 * 0.55) * r1);
    hole.closePath(); sh.holes.push(hole);
    if (S.splitSpoke) { // thin slot down the middle of each spoke
      const s2 = new THREE.Path(), b = a0, sw = 0.012;
      s2.moveTo(Math.cos(b) * (r1 + 0.03) - Math.sin(b) * sw, Math.sin(b) * (r1 + 0.03) + Math.cos(b) * sw);
      s2.lineTo(Math.cos(b) * (r2 - 0.03) - Math.sin(b) * sw, Math.sin(b) * (r2 - 0.03) + Math.cos(b) * sw);
      s2.lineTo(Math.cos(b) * (r2 - 0.03) + Math.sin(b) * sw, Math.sin(b) * (r2 - 0.03) - Math.cos(b) * sw);
      s2.lineTo(Math.cos(b) * (r1 + 0.03) + Math.sin(b) * sw, Math.sin(b) * (r1 + 0.03) - Math.cos(b) * sw);
      s2.closePath(); sh.holes.push(s2);
    }
  }
  const face = new THREE.Mesh(new THREE.ExtrudeGeometry(sh, { depth: 0.03, bevelEnabled: true, bevelThickness: 0.008, bevelSize: 0.006, bevelSegments: 2, curveSegments: 48 }),
    new THREE.MeshPhysicalMaterial({ color: S.wheelColor, roughness: S.wheelRough, metalness: 0.85, clearcoat: 0.6 }));
  face.position.z = tw / 2 - 0.05; g.add(face);
  const hub = new THREE.Mesh(new THREE.CylinderGeometry(hubR, hubR, 0.05, 24), face.material);
  hub.rotation.x = Math.PI / 2; hub.position.z = tw / 2 - 0.03; g.add(hub);
  return g;
}

/* ---------------------------------------------------------------- car */
export function buildCar(S) {
  const car = new THREE.Group();
  const paint = new THREE.MeshPhysicalMaterial({ color: S.paint, metalness: 0.55, roughness: 0.32, clearcoat: 1, clearcoatRoughness: 0.04 });
  const glass = new THREE.MeshPhysicalMaterial({ color: 0x05080b, metalness: 0.1, roughness: 0.03, clearcoat: 1, clearcoatRoughness: 0.0 });
  const black = new THREE.MeshPhysicalMaterial({ color: 0x08090b, metalness: 0.3, roughness: 0.35, clearcoat: 0.6 });
  const roofM = new THREE.MeshPhysicalMaterial({ color: 0x0c0d10, metalness: 0.4, roughness: 0.28, clearcoat: 1 });
  const B = buildBody(S);
  const body = new THREE.Mesh(B.geo, [paint, glass, black, roofM]);
  body.castShadow = true; car.add(body); car.updateMatrixWorld(true);
  const decalMat = (tex, emi, kind) => new THREE.MeshPhysicalMaterial({ map: tex, transparent: true, alphaTest: 0.02,
    roughness: kind === 'glass' ? 0.04 : 0.25, metalness: kind === 'glass' ? 0.0 : 0.3, clearcoat: 1, clearcoatRoughness: kind === 'glass' ? 0 : 0.05,
    emissive: emi ? 0xffffff : 0x000000, emissiveMap: emi || null, emissiveIntensity: emi ? 2.2 : 0, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2 });
  for (const d of S.decals) {
    // draw functions get the body (B.width etc.) and use outside-view coordinates; side decals
    // are drawn once in body x and projected onto both flanks
    const flip = d.flip ?? (d.axis === '+x' || d.axis === '-z');
    const tex = canvasTex(d.tw || 1024, d.th || 512, (g, W, H) => d.draw(g, W, H, B), flip);
    const emi = d.glow ? canvasTex(d.tw || 1024, d.th || 512, (g, W, H) => d.glow(g, W, H, B), flip) : null;
    const mat = decalMat(tex, emi, d.kind);
    for (const axis of d.axis === '±z' ? ['+z', '-z'] : [d.axis]) {
      const m = decal(body, d.rect, axis, mat, d.segs, d.minFacing, d.reach ?? (axis[1] === 'x' ? 0.55 : 9));
      m.renderOrder = d.order || 1; car.add(m);
    }
  }
  // wheels
  const wheels = [];
  for (const [x, R] of [[S.xf, S.Rf], [S.xr, S.Rr]]) for (const side of [1, -1]) {
    const w = buildWheel(S, R); w.position.set(x, R, side * (S.track / 2)); if (side < 0) w.rotation.y = Math.PI;
    w.traverse(o => { if (o.isMesh) o.castShadow = true; }); car.add(w); wheels.push(w);
  }
  // mirrors
  for (const side of [1, -1]) {
    const m = new THREE.Mesh(new THREE.SphereGeometry(1, 24, 12), S.mirrorPaint ? paint : black);
    m.scale.set(0.09, 0.065, 0.13); m.position.set(S.mirror[0], S.mirror[1], side * (B.width(S.mirror[0]) + 0.08)); car.add(m);
    const st = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.03, 0.1), black); st.position.set(S.mirror[0] + 0.02, S.mirror[1] - 0.02, side * (B.width(S.mirror[0]) + 0.01)); car.add(st);
  }
  // exhausts
  for (const e of S.exhausts) for (const side of [1, -1]) {
    const tip = new THREE.Mesh(new THREE.CylinderGeometry(1, 1, 0.14, 32, 1, true), new THREE.MeshStandardMaterial({ color: 0xb8bcc3, metalness: 1, roughness: 0.25, side: THREE.DoubleSide }));
    let ex = -S.L / 2; while (B.width(ex) < e.z + e.rz && ex < 0) ex += 0.005;
    e.x = ex + 0.035;
    tip.rotation.z = Math.PI / 2; tip.scale.set(e.ry, 1, e.rz); tip.position.set(e.x, e.y, side * e.z); car.add(tip);
    const inner = new THREE.Mesh(new THREE.CircleGeometry(1, 32), new THREE.MeshBasicMaterial({ color: 0x020202 }));
    inner.rotation.y = -Math.PI / 2; inner.scale.set(e.rz * 0.85, e.ry * 0.85, 1); inner.position.set(e.x - 0.03, e.y, side * e.z); car.add(inner);
  }
  if (S.extra) S.extra(car, { paint, black, glass, B });
  car.userData = { S, wheels, B, paint };
  return car;
}

/* ---------------------------------------------------------------- studio */
export function makeStudio(canvas, W, H) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(1); renderer.setSize(W, H, false);
  renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.05;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFShadowMap;
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x05070b);
  scene.fog = new THREE.Fog(0x05070b, 14, 34);
  // HDR studio environment: dark room with softboxes, baked to PMREM for reflections
  const env = new THREE.Scene();
  env.add(new THREE.Mesh(new THREE.SphereGeometry(30, 32, 16), new THREE.MeshBasicMaterial({ color: 0x0b0d12, side: THREE.BackSide })));
  const box = (w, h, x, y, z, rx, ry, k, col = 0xffffff) => {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ color: new THREE.Color(col).multiplyScalar(k), side: THREE.DoubleSide }));
    m.position.set(x, y, z); m.rotation.set(rx, ry, 0); env.add(m);
  };
  box(14, 3, 0, 9, 0, Math.PI / 2, 0, 6);            // big overhead softbox -> long roof/bonnet highlight
  box(16, 0.5, 0, 4, -9, 0, 0, 10);                  // long strip behind -> sharp shoulder line
  box(16, 0.5, 0, 4, 9, 0, 0, 10);
  box(0.6, 6, -10, 3, 0, 0, Math.PI / 2, 8, 0xdfe8ff); // vertical strips at the ends
  box(0.6, 6, 10, 3, 0, 0, Math.PI / 2, 8, 0xffeedd);
  box(30, 6, 0, -1, 0, Math.PI / 2, 0, 0.22, 0x404650); // soft floor bounce
  for (const zz of [-11, 11]) {                     // long wall strips -> light lines along the flanks
    box(26, 0.35, 0, 0.9, zz, 0, 0, 5);
    box(26, 1.2, 0, 3.0, zz, 0, 0, 2.2, 0xd8e2ee);
  }
  for (const xx of [-11, 11]) box(8, 2.5, xx, 2.2, 0, 0, Math.PI / 2, 2.2);   // softboxes front and rear
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(env, 0.02).texture;
  // floor: dark gloss + spotlight pool
  const floor = new THREE.Mesh(new THREE.CircleGeometry(40, 64), new THREE.MeshPhysicalMaterial({ color: 0x030304, roughness: 0.7, metalness: 0.0, clearcoat: 0.25, clearcoatRoughness: 0.15, transparent: true, opacity: 0.92 }));
  floor.material.envMapIntensity = 0.08; floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true; scene.add(floor);
  const pool = new THREE.Mesh(new THREE.PlaneGeometry(14, 14), new THREE.MeshBasicMaterial({ map: canvasTex(512, 512, (g, w, h) => {
    const r = g.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, w / 2); r.addColorStop(0, 'rgba(120,140,170,0.22)'); r.addColorStop(1, 'rgba(0,0,0,0)'); g.fillStyle = r; g.fillRect(0, 0, w, h);
  }), transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }));
  pool.rotation.x = -Math.PI / 2; pool.position.y = 0.002; scene.add(pool);
  const key = new THREE.DirectionalLight(0xffffff, 2.0); key.position.set(3, 9, 4); key.castShadow = true;
  key.shadow.mapSize.set(2048, 2048); Object.assign(key.shadow.camera, { left: -6, right: 6, top: 6, bottom: -6, near: 1, far: 25 }); key.shadow.radius = 6; key.shadow.bias = -0.0004;
  scene.add(key);
  scene.add(new THREE.HemisphereLight(0x8090a0, 0x101014, 0.35));
  const camera = new THREE.PerspectiveCamera(30, W / H, 0.1, 100);
  return { renderer, scene, camera, floor, pool, key };
}
// a car plus its reflection in the floor (mirrored copy seen through the semi-transparent floor)
export function placeCar(studio, car, x = 0, z = 0, rotY = 0) {
  const root = new THREE.Group(); root.position.set(x, 0, z); root.rotation.y = rotY;
  root.add(car);
  const refl = car.clone(true); refl.scale.y = -1;
  refl.traverse(o => { if (o.isMesh) { o.castShadow = false; o.material = Array.isArray(o.material) ? o.material.map(m => m.clone()) : o.material.clone(); for (const m of [].concat(o.material)) { m.side = THREE.DoubleSide; } } });
  root.add(refl);
  const { S } = car.userData;
  const shadow = new THREE.Mesh(new THREE.PlaneGeometry(S.L + 0.9, S.W + 0.8), new THREE.MeshBasicMaterial({ transparent: true, depthWrite: false, map: canvasTex(512, 256, (g, w, h) => {
    g.filter = 'blur(14px)'; g.fillStyle = 'rgba(0,0,0,0.92)'; g.beginPath(); g.roundRect(w * 0.1, h * 0.17, w * 0.8, h * 0.66, h * 0.2); g.fill();
  }) }));
  shadow.rotation.x = -Math.PI / 2; shadow.position.y = 0.004; shadow.renderOrder = 0; root.add(shadow);
  studio.scene.add(root);
  return { root, car, refl, shadow };
}
