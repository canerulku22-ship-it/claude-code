// Crispy chicken burger: eight quick shots with lots of cat-and-food action, plus 2D motion graphics.
// Registered by main.js, which passes in the shared kit (the cat, kitchen, materials and helpers).
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import { mergeVertices } from 'three/addons/utils/BufferGeometryUtils.js';
import { starburst, actionLines, comicText, sticker, speedLines, rays, ringFx, twinkleStar, thermoIcon, clockIcon, flameIcon, checkIcon } from './fx2d.js';

export function chickenScenes(k) {
  const { THREE, V, vlerp, clamp, lerp, seg, smooth, easeOut, easeIn, easeInOut, backOut, mulberry32, noise1, std, phys, canvasTex, lathe,
    crumbTex, softDot, starTex, heartTex, makePickles, biteWarp, warpGeo, prop, shadowy, emitter, rise, twinkle,
    cat, camera, bokeh, shoot, blink, breathe, behindCounter, show, board, fx, toScreen } = k;

  // ---------------------------------------------------------------- motion helpers
  const pop = (t, t0, d = 0.3) => (t < t0 ? 0 : backOut(seg(t, t0, t0 + d)));
  const wob = (t, t0, f = 26, decay = 9) => (t < t0 ? 0 : Math.exp(-(t - t0) * decay) * Math.sin((t - t0) * f));
  const bump = (t, t0, t1) => Math.sin(Math.PI * seg(t, t0, t1));
  const shake = (t, hits, amp = 0.006) => hits.reduce((v, h) => v.add(V(wob(t, h, 71, 13) * amp, wob(t, h + 0.013, 59, 13) * amp, 0)), V());
  const arc = (a, b, s, h) => vlerp(a, b, s).add(V(0, Math.sin(Math.PI * s) * h, 0));
  function h3(x, y, z) { const s = Math.sin(x * 127.1 + y * 311.7 + z * 74.7) * 43758.5453; return s - Math.floor(s); }
  function vn3(x, y, z) {
    const xi = Math.floor(x), yi = Math.floor(y), zi = Math.floor(z), xf = x - xi, yf = y - yi, zf = z - zi;
    const u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf), w = zf * zf * (3 - 2 * zf);
    const c = (a, b, d) => h3(xi + a, yi + b, zi + d);
    return lerp(lerp(lerp(c(0, 0, 0), c(1, 0, 0), u), lerp(c(0, 1, 0), c(1, 1, 0), u), v),
      lerp(lerp(c(0, 0, 1), c(1, 0, 1), u), lerp(c(0, 1, 1), c(1, 1, 1), u), v), w);
  }

  // ---------------------------------------------------------------- the chicken: raw -> floured -> fried
  // One mesh that morphs from a smooth raw thigh (0) to a shaggy, craggy coated one (1); colour follows state.
  function makeChicken(seed = 1) {
    let geo = new THREE.SphereGeometry(1, 150, 104);
    geo.deleteAttribute('uv'); geo.deleteAttribute('normal');
    geo = mergeVertices(geo);
    const pos = geo.attributes.position, n = pos.count, R = [0.087, 0.026, 0.066];
    const base = new Float32Array(n * 3), crag = new Float32Array(n * 3), amt = new Float32Array(n);
    for (let i = 0; i < n; i++) {
      const x = pos.getX(i), y = pos.getY(i), z = pos.getZ(i);
      const lobe = 1 + 0.34 * (vn3(x * 1.7 + seed, y * 1.7, z * 1.7) - 0.5) + 0.12 * (vn3(x * 4 + 9, y * 4, z * 4 + seed) - 0.5);
      const bx = x * R[0] * lobe, bz = z * R[2] * lobe;
      const by = y * R[1] * (0.85 + 0.3 * vn3(x * 2 + 3, z * 2, seed)) * (0.62 + 0.38 * Math.sqrt(Math.max(0, 1 - (x * x + z * z) * 0.65)));
      const gx = bx / (R[0] * R[0]), gy = by / (R[1] * R[1]), gz = bz / (R[2] * R[2]), gl = Math.hypot(gx, gy, gz) || 1;
      const ridge = Math.pow(1 - Math.abs(2 * vn3(x * 11 + seed, y * 11, z * 11) - 1), 2.2);
      const ridge2 = Math.pow(1 - Math.abs(2 * vn3(x * 24, y * 24 + seed, z * 24) - 1), 3);
      const d = 0.0062 * ridge + 0.0022 * ridge2 + 0.0012 * vn3(x * 60, y * 60, z * 60 + seed) + 0.001;
      base.set([bx, by, bz], i * 3);
      crag.set([bx + gx / gl * d, by + gy / gl * d, bz + gz / gl * d], i * 3);
      amt[i] = clamp(d / 0.0095);
    }
    pos.array.set(base); pos.needsUpdate = true;
    geo.setAttribute('crag', new THREE.BufferAttribute(amt, 1));
    geo.computeVertexNormals();
    const tg = new THREE.BufferGeometry(); tg.setAttribute('position', new THREE.BufferAttribute(crag, 3)); tg.setIndex(geo.index); tg.computeVertexNormals();
    geo.morphAttributes.position = [tg.attributes.position]; geo.morphAttributes.normal = [tg.attributes.normal];
    const u = { uFloured: { value: 0 }, uFried: { value: 0 } };
    const mat = phys('#ffffff', { roughness: 0.3, clearcoat: 0.8, clearcoatRoughness: 0.25 });
    mat.onBeforeCompile = sh => {
      Object.assign(sh.uniforms, u);
      sh.vertexShader = 'attribute float crag; varying float vCrag; varying vec3 vP;\n' + sh.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\n vCrag = crag; vP = position;');
      sh.fragmentShader = 'uniform float uFloured, uFried; varying float vCrag; varying vec3 vP;\n'
        + 'float hh(vec3 p){ p = fract(p * 0.3183099 + 0.1); p *= 17.0; return fract(p.x * p.y * p.z * (p.x + p.y + p.z)); }\n'
        + sh.fragmentShader.replace('#include <color_fragment>', `#include <color_fragment>
          float nz = hh(floor(vP * 900.0));
          vec3 raw = mix(vec3(0.95, 0.72, 0.68), vec3(0.88, 0.56, 0.54), smoothstep(0.45, 0.95, nz));
          vec3 flour = mix(vec3(0.97, 0.94, 0.88), vec3(0.84, 0.78, 0.66), clamp(vCrag * 0.8 + nz * 0.15, 0.0, 1.0));
          vec3 fried = mix(vec3(0.88, 0.6, 0.22), vec3(0.5, 0.24, 0.06), clamp(pow(vCrag, 1.2) + (nz - 0.5) * 0.16, 0.0, 1.0));
          diffuseColor.rgb *= pow(mix(mix(raw, flour, uFloured), fried, uFried), vec3(2.2));`);
    };
    mat.customProgramCacheKey = () => 'chicken-v2';
    const mesh = new THREE.Mesh(geo, mat);
    mesh.castShadow = mesh.receiveShadow = true;
    mesh.morphTargetInfluences = [0];
    mesh.userData.state = ({ floured = 0, fried = 0, crag = 0 } = {}) => {
      u.uFloured.value = floured; u.uFried.value = fried; mesh.morphTargetInfluences[0] = crag;
      mat.roughness = lerp(lerp(0.28, 0.95, floured), 0.5, fried);
      mat.clearcoat = lerp(lerp(0.85, 0.0, floured), 0.55, fried);
      const puffUp = 1 + 0.05 * fried;
      mesh.scale.set(puffUp, puffUp * 1.08, puffUp);
    };
    return mesh;
  }

  // ---------------------------------------------------------------- bowls, liquids, particles
  function makeBowl(color, s = 1) {
    const prof = [[0, 0], [0.06, 0], [0.082, 0.01], [0.097, 0.04], [0.102, 0.062], [0.098, 0.065], [0.092, 0.052], [0.078, 0.018], [0.055, 0.008], [0, 0.008]];
    const mesh = new THREE.Mesh(new THREE.LatheGeometry(prof.map(([x, y]) => new THREE.Vector2(x * s, y * s)), 80),
      phys(color, { roughness: 0.22, clearcoat: 0.9, side: THREE.DoubleSide }));
    mesh.castShadow = mesh.receiveShadow = true;
    const g = new THREE.Group(); g.add(mesh); return g;
  }
  function makeSurface(R, color, opts = {}) {
    const geo = new THREE.RingGeometry(0.0004, R, 96, 30).rotateX(-Math.PI / 2);
    const base = geo.attributes.position.array.slice();
    const mesh = new THREE.Mesh(geo, phys(color, { roughness: 0.14, clearcoat: 1, clearcoatRoughness: 0.08, ...opts }));
    mesh.receiveShadow = true;
    mesh.userData.wave = fn => {
      const p = geo.attributes.position.array;
      for (let i = 0; i < p.length; i += 3) p[i + 1] = fn(base[i], base[i + 2]);
      geo.attributes.position.needsUpdate = true; geo.computeVertexNormals();
    };
    return mesh;
  }
  // Ballistic bits: droplets, oil spits, crumbs.
  function makeBits(count, material, geometry, size, seed) {
    const inst = new THREE.InstancedMesh(geometry, material, count);
    const r = mulberry32(seed), d = [], m = new THREE.Matrix4(), q = new THREE.Quaternion(), e = new THREE.Euler();
    for (let i = 0; i < count; i++) d.push([r(), r(), r(), r(), r(), r()]);
    inst.frustumCulled = false; inst.castShadow = true;
    inst.userData.burst = (t, t0, o, { power = 1, life = 0.8, spread = 1, up = 1, floor = -0.02, dir = null } = {}) => {
      for (let i = 0; i < count; i++) {
        const [a, b, c, ee, f, g] = d[i], dt = t - t0 - a * 0.05;
        let s = 0, x = o.x, y = o.y, z = o.z;
        if (dt > 0 && dt < life) {
          const ang = b * Math.PI * 2, sp = (0.22 + c * 0.6) * power * spread;
          const dx = dir ? dir.x : 0, dz = dir ? dir.z : 0;
          x += (Math.cos(ang) * sp + dx * power) * dt; z += (Math.sin(ang) * sp * 0.8 + dz * power) * dt;
          y += (0.45 + ee * 0.9) * power * up * dt - 2.4 * dt * dt;
          s = y < o.y + floor ? 0 : size * (0.5 + f) * (1 - (dt / life) * 0.4);
        }
        e.set(g * 6 + dt * 8 * (b - 0.5), a * 6, c * 6); q.setFromEuler(e);
        m.compose(V(x, y, z), q, V(s, s * 1.1, s)); inst.setMatrixAt(i, m);
      }
      inst.instanceMatrix.needsUpdate = true;
    };
    inst.userData.burst(0, 10, V());
    return inst;
  }
  // Soft clouds that burst outward and drift up (flour).
  function puff(em, t, t0, o, { size = 1, life = 1.2, spread = 0.18, up = 0.1, toward = null } = {}) {
    em.visible = true;
    for (const s of em.userData.parts) {
      const [a, b, c, d, e] = s.userData.r, dt = t - t0 - a * 0.08;
      if (dt < 0 || dt > life) { s.material.opacity = 0; continue; }
      const p = easeOut(dt / life), ang = b * Math.PI * 2;
      const drift = toward ? toward.clone().multiplyScalar(p * (0.3 + 0.7 * c)) : V();
      s.position.set(o.x + Math.cos(ang) * spread * p * (0.4 + c) + drift.x, o.y + 0.01 + up * p * (0.5 + d) + drift.y, o.z + Math.sin(ang) * spread * 0.7 * p * (0.4 + c) + drift.z);
      s.scale.setScalar(em.userData.size * size * (0.5 + p * 1.8) * (0.7 + e * 0.6));
      s.material.opacity = 0.8 * (1 - dt / life) * Math.min(1, dt * 14);
      s.material.rotation = b * 6 + p;
    }
  }
  // Bubbles in hot oil: a foamy ring hugging the food plus a few across the surface.
  function makeBubbles(count, seed) {
    const inst = new THREE.InstancedMesh(new THREE.SphereGeometry(1, 10, 8), phys('#fff2c8', { roughness: 0.04, clearcoat: 1, transparent: true, opacity: 0.85 }), count);
    const r = mulberry32(seed), d = [], m = new THREE.Matrix4(), q = new THREE.Quaternion();
    for (let i = 0; i < count; i++) d.push([r(), r(), r(), r(), r()]);
    inst.frustumCulled = false;
    inst.userData.boil = (t, c, rx, rz, y, amount, potC = c, potR = 0.13) => {
      for (let i = 0; i < count; i++) {
        const [a, b, cc, dd, ee] = d[i], phase = (t * (1.4 + cc * 2.4) + a) % 1;
        let x, z;
        if (ee < 0.75) { const ang = b * Math.PI * 2 + t * 0.4 * (cc - 0.5), rim = 0.95 + 0.25 * dd; x = c.x + Math.cos(ang) * rx * rim; z = c.z + Math.sin(ang) * rz * rim; }
        else { const ang = b * Math.PI * 2, rr = Math.sqrt(dd) * potR * 0.9; x = potC.x + Math.cos(ang) * rr; z = potC.z + Math.sin(ang) * rr; }
        const s = amount * 0.0048 * (0.35 + dd) * Math.sin(Math.PI * phase);
        m.compose(V(x, y + s * 0.3, z), q, V(s, s * 0.8, s)); inst.setMatrixAt(i, m);
      }
      inst.instanceMatrix.needsUpdate = true;
    };
    return inst;
  }

  // ---------------------------------------------------------------- tools
  const metal = std('#dde1e6', { metalness: 1, roughness: 0.26 });
  function makeTongs() {
    const g = new THREE.Group(), arms = [];
    for (const s of [-1, 1]) {
      const pivot = new THREE.Group(); g.add(pivot);
      const arm = new THREE.Mesh(new RoundedBoxGeometry(0.2, 0.004, 0.013, 2, 0.0015), metal); arm.position.x = 0.1; pivot.add(arm);
      const tip = new THREE.Mesh(new RoundedBoxGeometry(0.032, 0.007, 0.022, 2, 0.0025), metal); tip.position.set(0.19, -s * 0.003, 0); pivot.add(tip);
      pivot.userData.s = s; arms.push(pivot);
    }
    g.add(new THREE.Mesh(new THREE.CylinderGeometry(0.009, 0.009, 0.018, 16).rotateX(Math.PI / 2), metal));
    g.userData.open = a => arms.forEach(p => { p.rotation.z = p.userData.s * a; });
    g.userData.open(0.05);
    return shadowy(g);
  }
  // Point the tongs (hinge -> tips along local +x) so the tips sit at `tip`, coming from direction `from`.
  function aimTongs(tongs, tip, from) {
    const dir = from.clone().normalize();
    tongs.quaternion.setFromUnitVectors(V(1, 0, 0), dir);
    tongs.position.copy(tip.clone().sub(dir.clone().multiplyScalar(0.19)));
  }
  function dialTexture() {
    return canvasTex(256, 256, (g, w, h) => {
      g.fillStyle = '#ffffff'; g.beginPath(); g.arc(128, 128, 124, 0, 7); g.fill();
      g.lineWidth = 10; g.strokeStyle = '#ff5a36'; g.beginPath(); g.arc(128, 128, 96, -Math.PI * 0.25, Math.PI * 0.05); g.stroke();
      g.strokeStyle = '#222'; g.lineWidth = 4;
      for (let i = 0; i <= 12; i++) { const a = -Math.PI * 1.25 + i / 12 * Math.PI * 1.5; g.beginPath(); g.moveTo(128 + Math.cos(a) * 104, 128 + Math.sin(a) * 104); g.lineTo(128 + Math.cos(a) * (i % 3 ? 90 : 80), 128 + Math.sin(a) * (i % 3 ? 90 : 80)); g.stroke(); }
      g.fillStyle = '#222'; g.font = 'bold 40px sans-serif'; g.textAlign = 'center'; g.fillText('°F', 128, 190);
    });
  }
  function makeDialThermo() {
    const g = new THREE.Group();
    const probe = new THREE.Mesh(new THREE.CylinderGeometry(0.0026, 0.0026, 0.15, 10), metal); probe.position.y = -0.075; g.add(probe);
    const rim = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.03, 0.012, 32).rotateX(Math.PI / 2), metal); g.add(rim);
    const face = new THREE.Mesh(new THREE.CircleGeometry(0.026, 40), new THREE.MeshBasicMaterial({ map: dialTexture() })); face.position.z = 0.0062; g.add(face);
    const needle = new THREE.Group(); needle.position.z = 0.0068; g.add(needle);
    const nm = new THREE.Mesh(new THREE.BoxGeometry(0.002, 0.021, 0.001), new THREE.MeshBasicMaterial({ color: 0xd32f2f })); nm.position.y = 0.0095; needle.add(nm);
    g.userData.set = deg => { needle.rotation.z = lerp(Math.PI * 0.75, -Math.PI * 0.75, clamp((deg - 100) / 400)); };
    return shadowy(g);
  }
  function makeProbe() {
    const g = new THREE.Group();
    const body = new THREE.Mesh(new RoundedBoxGeometry(0.022, 0.1, 0.012, 3, 0.005), phys('#e8402c', { roughness: 0.35, clearcoat: 0.6 })); body.position.y = 0.05; g.add(body);
    const screen = new THREE.Mesh(new THREE.PlaneGeometry(0.016, 0.022), new THREE.MeshBasicMaterial({ map: canvasTex(128, 176, gg => {
      gg.fillStyle = '#d9f2c9'; gg.fillRect(0, 0, 128, 176); gg.fillStyle = '#1e2a1a'; gg.font = 'bold 54px monospace'; gg.textAlign = 'center';
      gg.fillText('165', 64, 92); gg.font = 'bold 34px monospace'; gg.fillText('°F', 64, 140);
    }) }));
    screen.position.set(0, 0.07, 0.0062); g.add(screen);
    const probe = new THREE.Mesh(new THREE.CylinderGeometry(0.0018, 0.0012, 0.07, 10), metal); probe.position.y = -0.035; g.add(probe);
    return shadowy(g);
  }
  function makeBottle() {
    const g = new THREE.Group();
    const body = new THREE.Mesh(new THREE.CylinderGeometry(0.024, 0.026, 0.1, 32), phys('#e0412c', { roughness: 0.3, clearcoat: 0.8 })); body.position.y = 0.068; g.add(body);
    const band = new THREE.Mesh(new THREE.CylinderGeometry(0.0255, 0.0265, 0.032, 32, 1, true), phys('#fff3e0', { roughness: 0.5 })); band.position.y = 0.064; g.add(band);
    const cap = new THREE.Mesh(new THREE.CylinderGeometry(0.016, 0.024, 0.016, 28), phys('#ffffff', { roughness: 0.4 })); cap.position.y = 0.01; g.add(cap);
    const nozzle = new THREE.Mesh(new THREE.ConeGeometry(0.008, 0.02, 20).rotateX(Math.PI), phys('#ffffff', { roughness: 0.4 })); nozzle.position.y = -0.008; g.add(nozzle);
    g.userData.squeeze = s => body.scale.set(1 - s * 0.14, 1, 1 + s * 0.06);
    return shadowy(g);
  }

  // ---------------------------------------------------------------- burger parts
  const B_TOP = new THREE.Color('#8e3d0c'), B_MID = new THREE.Color('#d07a28'), B_PALE = new THREE.Color('#f0cb8c');
  const briMat = phys('#ffffff', { vertexColors: true, roughness: 0.3, clearcoat: 1, clearcoatRoughness: 0.12, side: THREE.DoubleSide });
  const cutMat = std('#ffffff', { map: crumbTex, roughness: 0.85 });
  function makeBriocheTop() {
    const g = new THREE.Group();
    g.add(new THREE.Mesh(lathe([[0.0015, 0.072], [0.03, 0.07], [0.06, 0.06], [0.08, 0.044], [0.093, 0.024], [0.096, 0.01], [0.092, 0.0]],
      (x, y, z, c) => c.copy(B_PALE).lerp(B_MID, smooth(y / 0.02)).lerp(B_TOP, smooth((y - 0.022) / 0.045))), briMat));
    const cut = new THREE.Mesh(new THREE.CircleGeometry(0.092, 64).rotateX(Math.PI / 2), cutMat); cut.position.y = 0.0005; g.add(cut);
    return shadowy(g);
  }
  function makeBriocheBottom() {
    const g = new THREE.Group();
    g.add(new THREE.Mesh(lathe([[0.088, 0.03], [0.093, 0.024], [0.094, 0.012], [0.09, 0.003], [0.078, 0.0], [0.0015, 0.0]],
      (x, y, z, c) => c.copy(B_PALE).lerp(B_MID, 0.45 + y * 6)), briMat));
    const cut = new THREE.Mesh(new THREE.CircleGeometry(0.089, 64).rotateX(-Math.PI / 2), cutMat); cut.position.y = 0.03; g.add(cut);
    return shadowy(g);
  }
  function makeLettuce(count, seed, R = 0.074) {
    const geo = new THREE.PlaneGeometry(0.038, 0.0055, 12, 1);
    const p = geo.attributes.position;
    for (let i = 0; i < p.count; i++) { const x = p.getX(i); p.setZ(i, 0.0035 * Math.sin(x * 150)); p.setY(i, p.getY(i) + 0.0022 * Math.sin(x * 80)); }
    geo.rotateX(-Math.PI / 2); geo.computeVertexNormals();
    const inst = new THREE.InstancedMesh(geo, phys('#ffffff', { roughness: 0.45, clearcoat: 0.45, side: THREE.DoubleSide, emissive: new THREE.Color('#0c1404') }), count);
    const r = mulberry32(seed), items = [], col = new THREE.Color(), m = new THREE.Matrix4(), q = new THREE.Quaternion(), e = new THREE.Euler();
    for (let i = 0; i < count; i++) {
      const a = r() * Math.PI * 2, d = Math.sqrt(r()) * R;
      items.push({ x: Math.cos(a) * d, z: Math.sin(a) * d, y: 0.002 + r() * 0.012, ry: r() * 6.28, rx: (r() - 0.5) * 0.7, rz: (r() - 0.5) * 0.7, delay: r() });
      inst.setColorAt(i, col.setHSL(0.24 + r() * 0.05, 0.62, 0.42 + r() * 0.22));
    }
    inst.castShadow = true; inst.frustumCulled = false;
    inst.userData.layout = prog => {
      for (let i = 0; i < count; i++) {
        const it = items[i], pr = clamp((prog - it.delay * 0.6) / 0.4), fallY = (1 - easeIn(pr)) * 0.13;
        e.set(it.rx + (1 - pr) * 3 * (it.delay - 0.5), it.ry + (1 - pr) * 4, it.rz); q.setFromEuler(e);
        m.compose(V(it.x * (1 + (1 - pr) * 0.4), it.y + fallY, it.z * (1 + (1 - pr) * 0.4)), q, V(1, 1, 1).multiplyScalar(pr > 0 ? 1 : 0.0001));
        inst.setMatrixAt(i, m);
      }
      inst.instanceMatrix.needsUpdate = true;
    };
    inst.userData.layout(1);
    return inst;
  }
  function makeDrizzle(R = 0.07, zig = 7) {
    const pts = [], N = zig * 8;
    for (let i = 0; i <= N; i++) {
      const u = i / N, x = lerp(-R, R, u), z = Math.sin(u * Math.PI * zig) * Math.sqrt(Math.max(0, R * R - x * x)) * 0.86;
      pts.push(V(x, 0.0025 + 0.0006 * Math.sin(u * 47), z));
    }
    const curve = new THREE.CatmullRomCurve3(pts);
    const geo = new THREE.TubeGeometry(curve, 420, 0.0034, 8, false);
    const mesh = new THREE.Mesh(geo, phys('#f08648', { roughness: 0.14, clearcoat: 1, clearcoatRoughness: 0.06 }));
    const total = geo.index.count;
    mesh.userData.curve = curve;
    mesh.userData.progress = pr => { geo.setDrawRange(0, Math.floor((total * clamp(pr)) / 3) * 3); mesh.visible = pr > 0.003; };
    mesh.castShadow = true;
    return mesh;
  }
  function makeChickenBurger(seed, biteable = false) {
    const g = new THREE.Group();
    const L = { bottom: makeBriocheBottom(), mayo: makeDrizzle(0.07), lettuce: makeLettuce(90, seed), chicken: makeChicken(seed), pickles: makePickles(3, seed + 2), top: makeBriocheTop() };
    const rest = { bottom: 0, mayo: 0.03, lettuce: 0.03, chicken: 0.07, pickles: 0.1, top: 0.103 };
    for (const [key, o] of Object.entries(L)) { g.add(o); o.position.y = rest[key]; }
    L.mayo.userData.progress(1);
    L.chicken.userData.state({ floured: 1, fried: 1, crag: 1 });
    L.chicken.rotation.y = seed;
    g.userData.layers = L; g.userData.rest = rest;
    if (biteable) {
      const f = biteWarp(-1.27);
      const swaps = [];
      for (const key of ['bottom', 'top', 'chicken']) L[key].traverse(o => { if (o.isMesh) swaps.push([o, o.geometry, warpGeo(o.geometry, f)]); });
      g.userData.bite = on => swaps.forEach(([o, a, b]) => { o.geometry = on ? b : a; });
    }
    return g;
  }

  // ---------------------------------------------------------------- props (hidden until a scene shows them)
  const heroBurger = prop(makeChickenBurger(4));
  const stackBurger = prop(makeChickenBurger(6));
  const biteBurger = prop(makeChickenBurger(8, true));
  const chicken = prop(makeChicken(2));
  const milkBowl = prop(makeBowl('#7fb2d9'));
  const milk = prop(makeSurface(0.092, '#f8f3e8', { emissive: new THREE.Color('#141210') }));
  const flourBowl = prop(makeBowl('#9cbf8f'));
  const flour = prop(new THREE.Mesh(new THREE.CircleGeometry(0.09, 64).rotateX(-Math.PI / 2), std('#f6f0e2', { roughness: 1 })));
  flour.receiveShadow = true;
  const pot = prop(new THREE.Group());
  {
    const prof = [[0, 0], [0.13, 0], [0.146, 0.012], [0.152, 0.1], [0.154, 0.114], [0.146, 0.116], [0.139, 0.103], [0.135, 0.012], [0.122, 0.006], [0, 0.006]];
    const geo = lathe(prof, (x, y, z, c) => c.set(Math.hypot(x, z) > 0.142 || y > 0.11 ? '#cf4a2f' : '#2b2523'));
    const shell = new THREE.Mesh(geo, phys('#ffffff', { vertexColors: true, roughness: 0.25, clearcoat: 0.9, side: THREE.DoubleSide }));
    shell.castShadow = shell.receiveShadow = true; pot.add(shell);
    for (const s of [-1, 1]) {
      const h = new THREE.Mesh(new THREE.TorusGeometry(0.022, 0.006, 10, 24, Math.PI), phys('#cf4a2f', { roughness: 0.25, clearcoat: 0.9 }));
      h.position.set(s * 0.155, 0.09, 0); h.rotation.set(0, s > 0 ? -Math.PI / 2 : Math.PI / 2, 0); pot.add(h);
    }
  }
  const oil = prop(makeSurface(0.137, '#d4952f', { roughness: 0.08, emissive: new THREE.Color('#3a1e02') }));
  const bubbles = prop(makeBubbles(170, 21));
  const tongs = prop(makeTongs());
  const dial = prop(makeDialThermo());
  const probe = prop(makeProbe());
  const bottle = prop(makeBottle());
  const sauceBun = prop(makeBriocheBottom());
  const drizzle = prop(makeDrizzle(0.07));
  const milkDrops = prop(makeBits(46, phys('#fbf7ee', { roughness: 0.1, clearcoat: 1 }), new THREE.SphereGeometry(1, 10, 8), 0.0045, 31));
  const oilDrops = prop(makeBits(30, phys('#e3a136', { roughness: 0.05, clearcoat: 1 }), new THREE.SphereGeometry(1, 8, 6), 0.0026, 33));
  const crumbs = prop(makeBits(70, std('#d68b34', { roughness: 0.7 }), new RoundedBoxGeometry(1, 0.8, 0.9, 1, 0.25), 0.0045, 35));
  const flourPuffs = [0, 1, 2].map(i => emitter(softDot, 18, { color: 0xfffaf0, size: 0.06 + i * 0.01 }));
  const steamC = emitter(softDot, 22, { color: 0xffffff, size: 0.05 });
  const smokeC = emitter(softDot, 30, { color: 0xe8e1d8, size: 0.08 });
  const sparkC = emitter(starTex, 8, { color: 0xfff1c0, size: 0.03, blending: THREE.AdditiveBlending });
  const heartC = emitter(heartTex, 6, { size: 0.03 });

  // ---------------------------------------------------------------- shared camera and overlay helpers
  function cam(pos, target, { fov = 36, aperture = 0.022, maxblur = 0.011, focusAt = null, jolt = V() } = {}) {
    shoot(pos.clone().add(jolt), target.clone().add(jolt.clone().multiplyScalar(0.5)), { fov, aperture, maxblur });
    bokeh.uniforms.focus.value = camera.position.distanceTo(focusAt || target);
  }
  const scr = v => toScreen(v);
  function impact(t, t0, at, { r0 = 60, r1 = 380, life = 0.45, lines = true, color = '#ffffff' } = {}) {
    if (t < t0 || t > t0 + life) return;
    const p = scr(at), s = seg(t, t0, t0 + life);
    ringFx(fx, p.x, p.y, lerp(r0, r1, easeOut(s)), { alpha: 1 - s, width: 14, color });
    if (lines) actionLines(fx, p.x, p.y, lerp(r0 * 1.4, r1 * 0.8, easeOut(s)), lerp(r0 * 2.2, r1 * 1.15, easeOut(s)), { alpha: 1 - s, color, seed: Math.floor(t0 * 10) });
  }
  function stickerAt(t, t0, at, text, { dx = 0, dy = 0, scale = 1, rot = -0.06, ...rest } = {}) {
    if (t < t0) return;
    const p = scr(at), sc = pop(t, t0, 0.32);
    sticker(fx, p.x + dx, p.y + dy, text, { ...rest, scale: sc * scale, rot: rot + wob(t, t0, 22, 6) * 0.12, t });
  }
  const eyesOf = () => [cat.headWorld(V(-0.05, 0.03, 0.12)), cat.headWorld(V(0.05, 0.03, 0.12))];

  // ---------------------------------------------------------------- the scenes
  return {
    // 1. Hook: the finished burger spins on its board; Chef Whiskers pops up behind it.
    chick_hero: {
      setup() { show(board, heroBurger, steamC, sparkC); board.position.set(0, 0.011, 0.0); heroBurger.position.set(0, 0.022, 0.0); },
      update(t, D) {
        heroBurger.rotation.y = 0.6 + t * 0.5;
        const up = backOut(seg(t, 0.25, 0.62));
        cat.root.position.set(0.03, lerp(-0.6, -0.18, up), -0.27); cat.root.rotation.set(0, -0.05, 0);
        const lick = seg(t, 1.45, 2.2);
        cat.pose({ squash: t < 0.25 ? -0.1 : wob(t, 0.62, 30, 8) * 0.12, lean: 0.12, headX: 0.14, headZ: 0.07 * Math.sin(t * 3), sparkle: smooth(seg(t, 0.55, 0.9)),
          tongue: Math.sin(lick * Math.PI), mouth: 0.25 * Math.sin(lick * Math.PI), look: [0, -0.8], ears: 1, tail: Math.sin(t * 3) * 0.5, open: blink(t, 2.1, 0.9), bob: breathe(t) });
        cat.relax('R', 0.3); cat.relax('L', 0.3);
        rise(steamC, t, V(0, 0.19, 0), { amount: 0.55, spread: 0.07, height: 0.14 });
        const push = easeOut(seg(t, 0, 0.8)) * 0.75 + 0.25 * seg(t, 0.8, D);
        cam(V(0, lerp(0.25, 0.24, push), lerp(1.0, 0.64, push)), V(0, 0.19, 0), { fov: 34, aperture: 0.025, maxblur: 0.012, focusAt: V(0, 0.11, 0) });
        twinkle(sparkC, t, eyesOf(), { amount: smooth(seg(t, 0.7, 1.0)), size: 0.9 });
        const c = scr(V(0, 0.11, 0));
        rays(fx, c.x, c.y, t, { alpha: 0.11 * smooth(seg(t, 0, 0.35)) });
        impact(t, 0.02, V(0, 0.1, 0), { r0: 120, r1: 700, life: 0.5, lines: false });
        for (let i = 0; i < 5; i++) {
          const a = i * 1.3 + 0.5, ph = (t * 1.3 + i * 0.37) % 1;
          twinkleStar(fx, c.x + Math.cos(a) * 300, c.y + Math.sin(a) * 210, 28 * Math.sin(Math.PI * ph), { alpha: Math.sin(Math.PI * ph), rot: t });
        }
      },
      events: () => [{ t: 0, type: 'room', dur: 2.6 }, { t: 0, type: 'sizzle', dur: 2.6, level: 0.15 }, { t: 0.02, type: 'whoosh' }, { t: 0.45, type: 'pop' }, { t: 0.75, type: 'sparkle' }, { t: 1.6, type: 'lick' }],
    },

    // 2. Toss the raw chicken into buttermilk: splash, ripples, and a startled cat.
    chick_brine: {
      setup() { show(milkBowl, milk, chicken, milkDrops); milkBowl.position.set(0, 0, -0.1); milk.position.set(0, 0.046, -0.1); },
      update(t, D) {
        behindCounter(0, -0.34, 0);
        const B = V(0, 0.046, -0.1), hold = V(0, 0.095, -0.19), tHit = 0.66;
        const lift = easeOut(seg(t, 0.08, 0.38)) * 0.025, air = seg(t, 0.42, tHit);
        let p;
        if (t < 0.42) p = hold.clone().add(V(0, lift, 0));
        else if (t < tHit) p = arc(hold.clone().add(V(0, 0.025, 0)), B.clone().add(V(0, 0.004, 0)), easeIn(air), 0.04);
        else p = B.clone().add(V(0, -0.006 + 0.007 * wob(t, tHit, 16, 4), 0));
        chicken.position.copy(p); chicken.rotation.set(t < 0.42 ? -0.35 : lerp(-0.35, 0.1, air), 0.5, t > tHit ? 0.08 * wob(t, tHit, 12, 4) : 0);
        chicken.userData.state({ floured: 0, fried: 0, crag: 0 });
        milk.userData.wave((x, z) => {
          if (t < tHit) return 0;
          const dt = t - tHit, r = Math.hypot(x, z), front = dt * 0.2, amp = 0.0045 * Math.exp(-dt * 2.4);
          return amp * Math.sin((r - front) * 150) * Math.exp(-Math.pow((r - front) * 28, 2)) + amp * 0.35 * Math.sin(r * 110 - dt * 22) * Math.exp(-r * 18);
        });
        milkDrops.userData.burst(t, tHit, B.clone().add(V(0, 0.01, 0)), { power: 1.15, life: 0.75 });
        const startle = t > tHit ? Math.exp(-(t - tHit) * 3) : 0;
        cat.pose({ lean: 0.18 - 0.3 * startle, headX: 0.22 - 0.15 * startle, squash: t > tHit ? wob(t, tHit, 24, 6) * 0.14 : -0.05 * bump(t, 0.08, 0.42), earsBack: startle,
          sparkle: t > tHit ? 1 : 0.3, mouth: 0.45 * startle, look: [0, -0.7], open: 1, tail: Math.sin(t * 4) * 0.6, tailLift: 0.05 * startle, bob: breathe(t) });
        if (t < 0.45) { chicken.updateMatrixWorld(true); cat.reach('R', chicken.localToWorld(V(-0.07, 0.01, 0)), V(-0.9, -0.3, -0.5)); cat.reach('L', chicken.localToWorld(V(0.07, 0.01, 0)), V(0.9, -0.3, -0.5)); }
        else { cat.relax('R', 1.2 * startle + 0.4); cat.relax('L', 1.2 * startle + 0.4); }
        const punch = t > tHit ? 1 - seg(t, tHit, tHit + 0.5) : 0;
        cam(V(0.07, 0.31, 0.5), V(0, 0.11, -0.15), { fov: 36 - 5 * punch * (t > tHit ? 1 : 0), jolt: shake(t, [tHit], 0.007), focusAt: V(0, 0.07, -0.12) });
        impact(t, tHit, B, { r0: 50, r1: 330 });
        stickerAt(t, 0.95, B, '1 HR+', { dx: 150, dy: 190, size: 76, icon: clockIcon, iconColor: '#2f80ed' });
      },
      events: () => [{ t: 0, type: 'room', dur: 2.2 }, { t: 0.0, type: 'whoosh' }, { t: 0.45, type: 'whoosh', gain: 0.6 }, { t: 0.66, type: 'splash' }, { t: 0.72, type: 'mrrp', gain: 0.4 }, { t: 0.95, type: 'pop' }],
    },

    // 3. Toss it in seasoned flour three times; the last puff dusts the cat's nose.
    chick_dredge: {
      setup() { show(flourBowl, flour, chicken, ...flourPuffs); flourBowl.position.set(0, 0, -0.1); },
      update(t, D) {
        behindCounter(0, -0.35, 0);
        const lands = [0.5, 1.12, 1.74];
        const bowlJerk = bump(t, 0.66, 0.8) + bump(t, 1.28, 1.42);
        flourBowl.position.set(0, 0.01 * bowlJerk, -0.1); flourBowl.rotation.set(-0.06 * bowlJerk, 0, 0);
        const S = V(0, 0.056 + 0.01 * bowlJerk, -0.1);
        flour.position.copy(S);
        let p, rx = 0;
        if (t < lands[0]) p = vlerp(V(0, 0.1, -0.19), S.clone().add(V(0, 0.02, 0)), easeIn(seg(t, 0.18, lands[0])));
        else if (t < 0.68) p = S.clone().add(V(0, 0.022 - 0.005 * wob(t, lands[0], 20, 7), 0));
        else if (t < lands[1]) { const s = seg(t, 0.68, lands[1]); p = arc(S.clone().add(V(0, 0.022, 0)), S.clone().add(V(0, 0.022, 0)), s, 0.07); rx = Math.PI * easeInOut(s); }
        else if (t < 1.3) { p = S.clone().add(V(0, 0.022 - 0.005 * wob(t, lands[1], 20, 7), 0)); rx = Math.PI; }
        else if (t < lands[2]) { const s = seg(t, 1.3, lands[2]); p = arc(S.clone().add(V(0, 0.022, 0)), S.clone().add(V(0, 0.022, 0)), s, 0.075); rx = Math.PI + Math.PI * easeInOut(s); }
        else { const s = easeInOut(seg(t, 2.05, 2.45)); p = vlerp(S.clone().add(V(0, 0.022, 0)), V(0, 0.1, -0.15), s); rx = 2 * Math.PI - 0.5 * s; }
        chicken.position.copy(p); chicken.rotation.set(rx, 0.3, 0);
        const fl = smooth(seg(t, lands[0], lands[0] + 0.15)) * 0.6 + smooth(seg(t, lands[1], lands[1] + 0.15)) * 0.28 + smooth(seg(t, lands[2], lands[2] + 0.15)) * 0.12;
        chicken.userData.state({ floured: fl, fried: 0, crag: fl });
        puff(flourPuffs[0], t, lands[0], S, { spread: 0.16, up: 0.08 });
        puff(flourPuffs[1], t, lands[1], S, { spread: 0.18, up: 0.1 });
        puff(flourPuffs[2], t, lands[2], S, { spread: 0.2, up: 0.14, size: 1.2, toward: V(0, 0.12, -0.2) });
        const dusted = t > lands[2] + 0.2, sneeze = bump(t, 2.12, 2.32);
        cat.pose({ lean: 0.22 + 0.12 * sneeze, headX: 0.25 + 0.25 * sneeze, squash: -0.08 * sneeze + wob(t, 2.32, 26, 7) * 0.08, squint: dusted ? 0.6 * (1 - seg(t, 2.35, 2.6)) : 0.15,
          flour: dusted ? smooth(seg(t, lands[2] + 0.2, lands[2] + 0.35)) : 0, mouth: 0.4 * sneeze, earsBack: sneeze, sparkle: t > 2.4 ? 0.7 : 0, look: [0, -0.8], tail: Math.sin(t * 3) * 0.5, bob: breathe(t) });
        if (t < lands[0]) { chicken.updateMatrixWorld(true); cat.reach('R', chicken.localToWorld(V(-0.07, 0.01, 0)), V(-0.9, -0.3, -0.5)); cat.reach('L', chicken.localToWorld(V(0.07, 0.01, 0)), V(0.9, -0.3, -0.5)); }
        else if (t < 2.05) { flourBowl.updateMatrixWorld(true); cat.reach('R', flourBowl.localToWorld(V(-0.08, 0.06, -0.06)), V(-0.9, -0.4, -0.4)); cat.reach('L', flourBowl.localToWorld(V(0.08, 0.06, -0.06)), V(0.9, -0.4, -0.4)); }
        else { chicken.updateMatrixWorld(true); cat.reach('R', chicken.localToWorld(V(-0.07, 0.0, 0)), V(-0.9, -0.3, -0.5)); cat.reach('L', chicken.localToWorld(V(0.07, 0.0, 0)), V(0.9, -0.3, -0.5)); }
        const orbit = lerp(0.25, 0.05, easeInOut(seg(t, 0, D)));
        cam(V(Math.sin(orbit) * 0.6, 0.32, -0.12 + Math.cos(orbit) * 0.6), V(0, 0.13, -0.15), { fov: 36, jolt: shake(t, lands, 0.005), focusAt: V(0, 0.08, -0.12) });
        const flying = Math.max(bump(t, 0.68, lands[1]), bump(t, 1.3, lands[2]));
        if (flying > 0.05) { const c = scr(chicken.position); speedLines(fx, c.x, c.y, t, { alpha: 0.35 * flying, inner: 330 }); }
        lands.forEach(l => impact(t, l, S, { r0: 40, r1: 260, life: 0.35, color: '#fffaf0' }));
      },
      events: () => [{ t: 0, type: 'room', dur: 2.6 }, { t: 0.0, type: 'whoosh' }, { t: 0.5, type: 'puff' }, { t: 0.7, type: 'whoosh', gain: 0.5 }, { t: 1.12, type: 'puff' },
        { t: 1.32, type: 'whoosh', gain: 0.5 }, { t: 1.74, type: 'puff' }, { t: 2.18, type: 'sneeze' }],
    },

    // 4. Into the hot oil with tongs: it bubbles hard, the thermometer swings to 350 F.
    chick_fry: {
      setup() { show(pot, oil, bubbles, tongs, chicken, dial, smokeC, oilDrops); pot.position.set(0, 0, -0.1); oil.position.set(0, 0.08, -0.1); },
      update(t, D) {
        behindCounter(0, -0.37, 0);
        const P = V(0, 0.08, -0.1), tIn = 0.9, tRel = 1.12;
        const lower = easeInOut(seg(t, 0.15, tIn));
        const tip = t < tRel ? vlerp(V(0.0, 0.17, -0.13), P.clone().add(V(0, 0.006, 0)), lower) : vlerp(P.clone().add(V(0, 0.006, 0)), V(-0.06, 0.2, -0.2), easeInOut(seg(t, tRel, 1.7)));
        aimTongs(tongs, tip, V(0.15, -0.38, 0.9));
        tongs.userData.open(t < tRel ? 0.035 : 0.035 + 0.16 * bump(t, tRel, 1.5));
        const cp = t < tRel ? tip.clone().add(V(0, -0.004, 0)) : P.clone().add(V(0, -0.006 + 0.003 * Math.sin(t * 7) + 0.008 * wob(t, tIn, 14, 4), 0));
        chicken.position.copy(cp); chicken.rotation.set(0.12, 0.4, 0);
        chicken.userData.state({ floured: 1, crag: 1, fried: 0.18 * seg(t, tIn, D) });
        const boil = t < tIn ? 0 : 1.15 * Math.exp(-(t - tIn) * 1.3) + 0.75;
        bubbles.userData.boil(t, cp, 0.1, 0.078, P.y, boil, P);
        oil.userData.wave((x, z) => { const dt = t - tIn; if (dt < 0) return 0; const r = Math.hypot(x - (cp.x - P.x), z - (cp.z - P.z)); return 0.0018 * Math.exp(-dt * 2) * Math.sin(r * 160 - dt * 30) * Math.exp(-r * 8); });
        oilDrops.userData.burst(t, tIn, cp.clone().add(V(0, 0.01, 0)), { power: 0.8, life: 0.5 });
        rise(smokeC, t, P.clone().add(V(0, 0.02, 0)), { amount: t < tIn ? 0.2 : 0.75, spread: 0.2, height: 0.3, rate: 1.1, life: 2.0 });
        dial.position.set(0.118, 0.13, -0.035); dial.rotation.set(0, -0.35, 0); dial.userData.set(lerp(180, 350, easeOut(seg(t, 0.0, 1.4))));
        const flinch = t > tIn ? Math.exp(-(t - tIn) * 3.2) : 0, curious = smooth(seg(t, 1.6, 2.2));
        cat.pose({ lean: 0.22 - 0.3 * flinch + 0.12 * curious, headX: 0.3 - 0.2 * flinch, squash: wob(t, tIn, 26, 6) * 0.12, earsBack: flinch, sparkle: curious, squint: t < tIn ? 0.35 : 0,
          tongue: t < tIn ? 0.5 * bump(t, 0.2, 0.85) : 0, mouth: 0.4 * flinch, look: [0, -0.9], tail: Math.sin(t * 5) * 0.7, tailLift: 0.05 * flinch, bob: breathe(t) });
        tongs.updateMatrixWorld(true);
        cat.reach('R', tongs.localToWorld(V(0.03, 0, 0)), V(-0.9, -0.2, -0.5));
        cat.relax('L', 0.3 + 1.0 * flinch);
        const push = easeInOut(seg(t, 0, D));
        cam(V(lerp(0.2, 0.17, push), lerp(0.42, 0.39, push), lerp(0.47, 0.4, push)), V(0, 0.13, -0.13), { fov: 38, jolt: shake(t, [tIn], 0.006), focusAt: P });
        if (t > tIn && t < tIn + 0.5) { const c = scr(cp), s = seg(t, tIn, tIn + 0.5); starburst(fx, c.x, c.y, lerp(90, 230, easeOut(s)), { fill: null, stroke: '#fff4c2', lineWidth: 7, alpha: 1 - s, points: 14, inner: 0.55 }); }
        stickerAt(t, 1.3, dial.position.clone().add(V(0, 0.03, 0)), '350°F', { dx: -250, dy: 120, size: 76, icon: thermoIcon, rot: 0.05 });
      },
      events: () => [{ t: 0, type: 'room', dur: 2.8 }, { t: 0.0, type: 'whoosh' }, { t: 0.2, type: 'clink' }, { t: 0.9, type: 'sizzle', dur: 1.9, level: 1.0, attack: 0.03 },
        { t: 0.9, type: 'bubbles', dur: 1.9 }, { t: 1.12, type: 'clink' }, { t: 1.3, type: 'pop' }, { t: 1.4, type: 'ding' }],
    },

    // 5. Golden in seconds (time-lapse), flipped, lifted out, checked at 165 F.
    chick_golden: {
      setup() { show(pot, oil, bubbles, tongs, chicken, probe, smokeC, oilDrops, sparkC); pot.position.set(0, 0, -0.1); oil.position.set(0, 0.08, -0.1); },
      update(t, D) {
        behindCounter(0, -0.37, 0);
        const P = V(0, 0.08, -0.1);
        const fried = lerp(0.2, 1, smooth(seg(t, 0.0, 0.85)));
        const flip = seg(t, 0.85, 1.3), lift = easeInOut(seg(t, 1.4, 1.85));
        let cp = P.clone().add(V(0, -0.006 + 0.003 * Math.sin(t * 7), 0)), rx = 0.12;
        if (t > 0.85 && t < 1.3) { cp = arc(cp, cp, flip, 0.035); rx = 0.12 + Math.PI * easeInOut(flip); }
        if (t >= 1.3) rx = 0.12 + Math.PI;
        if (t >= 1.4) cp = vlerp(cp, V(0.0, 0.155, -0.13), lift);
        chicken.position.copy(cp); chicken.rotation.set(rx, 0.4, 0.15 * lift);
        chicken.userData.state({ floured: 1, crag: 1, fried });
        const engaged = (t > 0.7 && t < 1.32) || t > 1.35;
        const tip = engaged ? cp.clone().add(V(0, 0.004, 0)) : vlerp(V(-0.03, 0.22, -0.18), cp, 0.3);
        aimTongs(tongs, tip, V(0.15, -0.38, 0.9));
        tongs.userData.open(engaged ? 0.035 : 0.15);
        bubbles.userData.boil(t, t < 1.4 ? cp : P, 0.1, 0.078, P.y, t < 1.4 ? 0.85 : 0.6 * (1 - lift) + 0.3, P);
        oil.userData.wave((x, z) => 0.0008 * Math.sin(Math.hypot(x, z) * 140 - t * 18));
        oilDrops.userData.burst(t, 1.85, cp.clone().add(V(0, -0.03, 0)), { power: 0.12, life: 0.55, up: -0.2, spread: 0.3 });
        rise(smokeC, t, P.clone().add(V(0, 0.02, 0)), { amount: 0.6, spread: 0.2, height: 0.28, rate: 1.1, life: 2.0 });
        probe.visible = t > 1.85;
        const stab = easeOut(seg(t, 1.9, 2.12));
        probe.position.copy(cp.clone().add(V(lerp(0.12, 0.04, stab), 0.05 + lerp(0.06, 0.0, stab), 0.02))); probe.rotation.set(0, 0, 0.6);
        const hop = Math.max(wob(t, 1.0, 24, 7), wob(t, 2.15, 24, 7));
        cat.pose({ lean: 0.25, headX: 0.3, squash: hop * 0.12, sparkle: smooth(seg(t, 0.4, 0.8)), mouth: 0.35 * bump(t, 0.5, 1.2), look: [0, -0.9], ears: 1, tail: Math.sin(t * 6) * 0.8, bob: breathe(t) });
        tongs.updateMatrixWorld(true);
        cat.reach('R', tongs.localToWorld(V(0.03, 0, 0)), V(-0.9, -0.2, -0.5));
        cat.relax('L', 0.6 + 0.4 * Math.sin(t * 5));
        cam(V(0.15, 0.38, 0.4), V(0, lerp(0.12, 0.15, lift), -0.12), { fov: 36, focusAt: cp });
        twinkle(sparkC, t, [cp.clone().add(V(-0.04, 0.03, 0.03)), cp.clone().add(V(0.05, 0.02, 0.02))], { amount: bump(t, 0.5, 1.4), size: 1.2 });
        if (t > 0.6 && t < 1.2) { const c = scr(cp); for (let i = 0; i < 4; i++) { const ph = (t * 2.2 + i * 0.25) % 1; twinkleStar(fx, c.x + Math.cos(i * 1.7) * 160, c.y + Math.sin(i * 1.7) * 90, 36 * Math.sin(Math.PI * ph), { alpha: Math.sin(Math.PI * ph) }); } }
        stickerAt(t, 2.05, cp, '165°F', { dx: 150, dy: 250, size: 76, icon: checkIcon, iconColor: '#2fbf5b' });
      },
      events: () => [{ t: 0, type: 'room', dur: 2.4 }, { t: 0, type: 'sizzle', dur: 1.5, level: 0.7 }, { t: 0, type: 'bubbles', dur: 1.5 }, { t: 0.0, type: 'whoosh' },
        { t: 0.6, type: 'sparkle' }, { t: 0.85, type: 'clink' }, { t: 0.95, type: 'whoosh', gain: 0.5 }, { t: 1.4, type: 'clink' }, { t: 2.1, type: 'ding' }, { t: 2.05, type: 'pop' }],
    },

    // 6. A quick zigzag of spicy mayo, tongue out in concentration.
    chick_sauce: {
      setup() { show(board, sauceBun, drizzle, bottle); board.position.set(0, 0.011, -0.13); sauceBun.position.set(0, 0.022, -0.13); drizzle.position.set(0, 0.052, -0.13); },
      update(t, D) {
        behindCounter(0, -0.33, 0);
        const pr = easeInOut(seg(t, 0.15, 1.55));
        drizzle.userData.progress(pr);
        drizzle.updateMatrixWorld(true);
        const head = drizzle.localToWorld(drizzle.userData.curve.getPointAt(clamp(pr, 0.001, 1)));
        const away = seg(t, 1.6, 2.0);
        bottle.position.copy(head.clone().add(V(0, 0.028 + 0.004 * Math.sin(t * 22) + away * 0.08, -away * 0.05)));
        bottle.rotation.set(-0.35, 0, 0.25 * Math.sin(pr * Math.PI * 7));
        bottle.userData.squeeze(t > 0.15 && t < 1.55 ? 0.8 + 0.2 * Math.sin(t * 30) : 0);
        bottle.updateMatrixWorld(true);
        const proud = smooth(seg(t, 1.65, 1.9));
        cat.pose({ lean: 0.3 - 0.15 * proud, headX: 0.38 - 0.2 * proud, tongue: 0.7 * (1 - proud), squint: 0.35 * (1 - proud), sparkle: proud, squash: wob(t, 1.7, 22, 6) * 0.12,
          look: [0, -1], ears: 1, tail: Math.sin(t * 4) * 0.6, bob: breathe(t) });
        cat.reach('R', bottle.localToWorld(V(-0.03, 0.07, 0)), V(-0.9, -0.3, -0.5));
        cat.reach('L', bottle.localToWorld(V(0.03, 0.07, 0)), V(0.9, -0.3, -0.5));
        const push = easeInOut(seg(t, 0, D));
        cam(V(0.04, lerp(0.42, 0.39, push), lerp(0.24, 0.19, push)), V(0, 0.07, -0.15), { fov: 38, focusAt: V(0, 0.05, -0.13) });
        stickerAt(t, 1.0, V(0, 0.05, -0.13), 'SPICY', { dx: 170, dy: 230, size: 76, icon: flameIcon, rot: 0.08 });
      },
      events: () => [{ t: 0, type: 'room', dur: 2.2 }, { t: 0.0, type: 'whoosh' }, { t: 0.15, type: 'squirt', dur: 1.4 }, { t: 1.0, type: 'pop' }, { t: 1.72, type: 'mrrp', gain: 0.5 }],
    },

    // 7. Fast stack: lettuce rains, chicken slams, pickles pop, the top bun lands; proud pats.
    chick_stack: {
      setup() { show(board, stackBurger, sparkC); board.position.set(0, 0.011, -0.14); stackBurger.position.set(0, 0.022, -0.14); stackBurger.rotation.set(0, 0.3, 0); },
      update(t, D) {
        behindCounter(0, -0.36, 0);
        const L = stackBurger.userData.layers, R = stackBurger.userData.rest, base = V(0, 0.022, -0.14);
        L.lettuce.visible = t > 0.05; L.lettuce.userData.layout(seg(t, 0.05, 0.7));
        const tC = 0.95, tTop = 1.62;
        L.chicken.visible = t > 0.72;
        L.chicken.position.y = R.chicken + (1 - easeIn(seg(t, 0.72, tC))) * 0.22;
        const cs = t > tC ? wob(t, tC, 30, 8) : 0;
        L.chicken.scale.set(1 + cs * 0.12, 1 - cs * 0.22, 1 + cs * 0.12);
        L.pickles.children.forEach((pk, i) => { const s = pop(t, 1.12 + i * 0.1, 0.25); pk.scale.setScalar(Math.max(0.0001, s)); });
        L.top.visible = t > 1.4;
        L.top.position.y = R.top + (1 - easeIn(seg(t, 1.4, tTop))) * 0.16;
        const pat = Math.max(bump(t, 1.85, 2.02), bump(t, 2.15, 2.32));
        const ts = (t > tTop ? wob(t, tTop, 30, 8) * 0.12 : 0) + pat * 0.1;
        L.top.scale.set(1 + ts * 0.4, 1 - ts, 1 + ts * 0.4);
        cat.pose({ lean: 0.24 + 0.08 * pat, headX: 0.3, sparkle: t > 1.7 ? 1 : 0.4, squash: wob(t, tC, 26, 7) * 0.1 + wob(t, tTop, 26, 7) * 0.06, earsBack: t > tC ? 0.5 * Math.exp(-(t - tC) * 4) : 0,
          mouth: t > 1.75 ? 0.2 : 0, look: [0, -0.8], ears: 1, tail: Math.sin(t * 5) * 0.7, bob: breathe(t) });
        stackBurger.updateMatrixWorld(true);
        if (t > 1.72) {
          const top = stackBurger.localToWorld(V(0, R.top + 0.07 - pat * 0.012, 0));
          cat.reach('R', top.clone().add(V(-0.02, 0.012 + 0.03 * (1 - pat), 0.0)), V(-0.9, -0.3, -0.5));
          cat.relax('L', 0.9);
        } else { cat.relax('R', 0.5); cat.relax('L', 0.5); }
        const orbit = lerp(-0.4, 0.25, easeInOut(seg(t, 0, D)));
        cam(V(Math.sin(orbit) * 0.56, 0.29, -0.14 + Math.cos(orbit) * 0.56), V(0, 0.12, -0.15), { fov: 36, jolt: shake(t, [tC, tTop], 0.006), focusAt: base.clone().add(V(0, 0.08, 0)) });
        impact(t, tC, base.clone().add(V(0, 0.07, 0)), { r0: 70, r1: 420 });
        L.pickles.children.forEach((pk, i) => impact(t, 1.12 + i * 0.1, stackBurger.localToWorld(pk.position.clone().add(V(0, R.pickles, 0))), { r0: 20, r1: 110, life: 0.3, lines: false, color: '#c9f27a' }));
        impact(t, tTop, base.clone().add(V(0, 0.15, 0)), { r0: 60, r1: 330, life: 0.4 });
        if (t > tC && t < tC + 0.35) { const c = scr(base.clone().add(V(0, 0.07, 0))); speedLines(fx, c.x, c.y, t, { alpha: 0.45 * (1 - seg(t, tC, tC + 0.35)), inner: 380 }); }
        twinkle(sparkC, t, [stackBurger.localToWorld(V(-0.07, 0.2, 0.03)), stackBurger.localToWorld(V(0.08, 0.17, 0.03))], { amount: smooth(seg(t, 1.7, 1.9)), size: 1 });
      },
      events: () => [{ t: 0, type: 'room', dur: 2.6 }, { t: 0.0, type: 'whoosh' }, { t: 0.05, type: 'rustle', dur: 0.7 }, { t: 0.75, type: 'whoosh', gain: 0.6 }, { t: 0.95, type: 'thump' },
        { t: 1.12, type: 'pop' }, { t: 1.22, type: 'pop' }, { t: 1.32, type: 'pop' }, { t: 1.62, type: 'place' }, { t: 1.92, type: 'squish' }, { t: 2.22, type: 'squish' }, { t: 1.9, type: 'sparkle' }],
    },

    // 8. The bite: CRUNCH!
    chick_bite: {
      setup() { show(board, biteBurger, heartC, crumbs); board.position.set(0, 0.011, -0.13); biteBurger.position.set(0, 0.022, -0.13); },
      update(t, D) {
        behindCounter(0, -0.33, 0);
        const B = V(0, 0.022, -0.13), tCrunch = 0.86;
        const lift = easeInOut(seg(t, 0.08, 0.5)), into = easeInOut(seg(t, 0.55, tCrunch - 0.02)), back = easeInOut(seg(t, 0.98, 1.4));
        const mouthW = cat.headWorld(V(0, -0.07, 0.11));
        const hold = mouthW.clone().add(V(-0.01, -0.09, 0.14)), bitePos = mouthW.clone().add(V(-0.01, -0.07, 0.092)), showP = mouthW.clone().add(V(-0.035, -0.13, 0.09));
        biteBurger.position.copy(vlerp(B, hold, lift).lerp(bitePos, into * (1 - back)).lerp(showP, back));
        biteBurger.rotation.set(0.15 * lift * (1 - back) + 0.2 * back, 0.3 + 1.45 * back, 0);
        biteBurger.userData.bite(t > tCrunch);
        crumbs.userData.burst(t, tCrunch, mouthW.clone().add(V(0, -0.03, 0.06)), { power: 0.9, life: 0.8, dir: V(0, 0, 0.25) });
        const happy = t > tCrunch + 0.05 ? 1 : 0, chew = t > 1.0 ? Math.abs(Math.sin((t - 1.0) * 11)) : 0;
        cat.pose({ lean: 0.2 - 0.14 * lift, headX: lerp(0.3, 0.05, lift), headZ: happy * Math.sin(t * 4) * 0.07, mouth: Math.sin(Math.PI * seg(t, 0.5, tCrunch + 0.02)), chew: chew * happy, happy,
          crumb: happy, squash: wob(t, tCrunch, 30, 7) * 0.12, look: [0, lerp(-1, -0.3, lift)], open: blink(t, 2.6, 0.2), tail: Math.sin(t * (happy ? 7 : 2)) * (happy ? 0.9 : 0.4),
          tailLift: happy * 0.05, ears: 1, bob: breathe(t) + happy * Math.abs(Math.sin(t * 6)) * 0.004 });
        biteBurger.updateMatrixWorld(true);
        cat.reach('R', biteBurger.localToWorld(V(-0.09, 0.05, 0.0)), V(-0.9, -0.5, -0.3));
        cat.reach('L', biteBurger.localToWorld(V(0.09, 0.05, 0.0)), V(0.9, -0.5, -0.3));
        rise(heartC, t, cat.headWorld(V(0.06, 0.12, 0.05)), { amount: happy * smooth(seg(t, 1.2, 1.5)), spread: 0.16, height: 0.12, rate: 1.0, life: 1.2 });
        const punch = t > tCrunch ? 1 - seg(t, tCrunch, tCrunch + 0.45) : 0;
        cam(V(0.11, 0.25, 0.5), V(0, lerp(0.18, 0.2, lift), -0.22), { fov: 38 - 5 * punch, jolt: shake(t, [tCrunch], 0.009), focusAt: V(0, 0.17, -0.25) });
        if (t > tCrunch && t < tCrunch + 0.85) {
          const c = scr(mouthW.clone().add(V(0.0, -0.02, 0.1))), s = seg(t, tCrunch, tCrunch + 0.85), sc = pop(t, tCrunch, 0.25);
          speedLines(fx, c.x, c.y, t, { alpha: 0.55 * (1 - s), inner: 360 });
          starburst(fx, c.x + 170, c.y + 230, 220 * sc, { rot: -0.2 + t * 0.4, alpha: 1 - smooth(seg(s, 0.7, 1)), points: 13 });
          comicText(fx, c.x + 170, c.y + 230, 'CRUNCH!', { size: 110, rot: -0.14 + wob(t, tCrunch, 20, 5) * 0.12, scale: sc, fill: '#ffffff', alpha: 1 - smooth(seg(s, 0.7, 1)) });
        }
      },
      events: () => [{ t: 0, type: 'room', dur: 2.6 }, { t: 0.0, type: 'whoosh' }, { t: 0.86, type: 'crunch' }, { t: 1.25, type: 'mrrp' }, { t: 1.3, type: 'sparkle' }],
    },
  };
}
