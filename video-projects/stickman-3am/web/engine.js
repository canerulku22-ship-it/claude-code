// 3D engine: Three.js world (mirror floor, glowing figures, neon canvas panels, particles) + bloom + film pass.
// Everything is a pure function of time t via a paused GSAP timeline, so any frame renders deterministically.
import * as THREE from 'three';
import { Reflector } from 'three/addons/objects/Reflector.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

export { THREE };
export const W = 1080, H = 1920, FPS = 30;
export const gsap = window.gsap;
export const tl = gsap.timeline({ paused: true });
export const C = { mint: '#4DFFD2', red: '#FF4D5E', white: '#F4F7FF', grey: '#8C93A3', gold: '#FFD15C' };

// ---------------------------------------------------------------- renderer
export const renderer = new THREE.WebGLRenderer({ antialias: false, preserveDrawingBuffer: true, powerPreference: 'high-performance' });
renderer.setPixelRatio(1);
renderer.setSize(W, H);
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.0;
document.getElementById('gl').appendChild(renderer.domElement);

export const scene = new THREE.Scene();
scene.background = new THREE.Color(0x000000);
scene.fog = new THREE.FogExp2(0x000000, 0.055);
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
scene.environmentIntensity = 0.5;

export const camera = new THREE.PerspectiveCamera(30, W / H, 0.05, 300);
export const ambient = new THREE.AmbientLight(0xb8c4ff, 0.12); scene.add(ambient);
export const key = new THREE.SpotLight(0xffffff, 18, 40, 0.6, 0.7, 1.4);
key.position.set(0, 9, 3); key.target.position.set(0, 0, 0);
scene.add(key, key.target);
export const rim = new THREE.DirectionalLight(0xbcd6ff, 0.6); rim.position.set(-4, 3, -6); scene.add(rim);
export const moon = new THREE.DirectionalLight(0xffd9a0, 0.5); moon.position.set(-1.5, 3, -3); scene.add(moon);
export const phoneLight = new THREE.PointLight(0xdfe8ff, 0, 3.5, 1.6); scene.add(phoneLight);
export const hallLight = new THREE.PointLight(0xfff1dc, 0, 5, 1.4); scene.add(hallLight);
export const lights = { ambient, rim, moon, phoneLight, hallLight };

// ---------------------------------------------------------------- floor (blurred mirror that fades with distance)
const ReflShader = {
  name: 'GlossFloor',
  uniforms: { color: { value: null }, tDiffuse: { value: null }, textureMatrix: { value: null }, strength: { value: 0.55 }, blur: { value: 1.6 / 540 }, tint: { value: new THREE.Color(0x000000) } },
  vertexShader: /* glsl */`
    uniform mat4 textureMatrix; varying vec4 vUv; varying vec3 vWorld;
    void main(){ vUv = textureMatrix * vec4(position,1.0); vec4 wp = modelMatrix*vec4(position,1.0); vWorld = wp.xyz; gl_Position = projectionMatrix*viewMatrix*wp; }`,
  fragmentShader: /* glsl */`
    uniform vec3 color; uniform vec3 tint; uniform sampler2D tDiffuse; uniform float strength; uniform float blur; varying vec4 vUv; varying vec3 vWorld;
    void main(){
      vec2 uv = vUv.xy / vUv.w; vec3 c = vec3(0.0);
      for (int i=-2;i<=2;i++) for (int j=-2;j<=2;j++) c += texture2D(tDiffuse, uv + vec2(float(i), float(j)) * blur).rgb;
      c /= 25.0;
      float d = length(vWorld.xz - cameraPosition.xz);
      float fade = exp(-d * 0.055);
      vec3 base = color + tint * exp(-length(vWorld.xz) * 0.35);
      gl_FragColor = vec4(base + c * strength * fade, 1.0);
    }`,
};
export const floor = new Reflector(new THREE.PlaneGeometry(400, 400), { textureWidth: 540, textureHeight: 960, color: 0x020203, shader: ReflShader, clipBias: 0.003 });
floor.rotation.x = -Math.PI / 2;
scene.add(floor);
export const floorU = floor.material.uniforms;
floorU.color.value = new THREE.Color(0x030305); floorU.strength.value = 0.38;

// dashed seam line on the floor
function dashTexture() {
  const c = document.createElement('canvas'); c.width = 512; c.height = 8; const g = c.getContext('2d');
  g.fillStyle = '#fff'; for (let x = 0; x < 512; x += 64) g.fillRect(x, 0, 38, 8);
  const t = new THREE.CanvasTexture(c); t.wrapS = THREE.RepeatWrapping; t.repeat.set(60, 1); t.colorSpace = THREE.SRGBColorSpace; return t;
}
export function dashedLine(len = 120, z = 0, rotY = 0, opacity = 0.55) {
  const m = new THREE.Mesh(new THREE.PlaneGeometry(len, 0.025), new THREE.MeshBasicMaterial({ map: dashTexture(), transparent: true, opacity, depthWrite: false, toneMapped: false }));
  m.rotation.x = -Math.PI / 2; m.rotation.z = rotY; m.position.set(0, 0.002, z); m.material.map.repeat.set(len / 2, 1);
  return m;
}

// ---------------------------------------------------------------- textures
function radialTexture(stops) {
  const c = document.createElement('canvas'); c.width = c.height = 256; const g = c.getContext('2d');
  const gr = g.createRadialGradient(128, 128, 0, 128, 128, 128); stops.forEach(([o, col]) => gr.addColorStop(o, col));
  g.fillStyle = gr; g.fillRect(0, 0, 256, 256);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}
export const TEX = {
  glow: radialTexture([[0, 'rgba(255,255,255,1)'], [0.25, 'rgba(255,255,255,.55)'], [1, 'rgba(255,255,255,0)']]),
  soft: radialTexture([[0, 'rgba(255,255,255,.9)'], [0.5, 'rgba(255,255,255,.25)'], [1, 'rgba(255,255,255,0)']]),
};
export function glyphTexture(ch, font = '800 200px Inter', color = '#fff') {
  const c = document.createElement('canvas'); c.width = c.height = 256; const g = c.getContext('2d');
  g.font = font; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillStyle = color; g.fillText(ch, 128, 138);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}

// ---------------------------------------------------------------- figure (glowing mannequin)
const figMat = new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: 0xffffff, emissiveIntensity: 0.06, roughness: 0.3, metalness: 0.0 });
const bodyGeo = (() => {
  const p = [new THREE.Vector2(0, 0), new THREE.Vector2(0.25, 0), new THREE.Vector2(0.272, 0.025)];
  for (let i = 0; i <= 10; i++) p.push(new THREE.Vector2(0.272 + 0.012 * (i / 10), 0.025 + 0.46 * (i / 10)));
  for (let i = 1; i <= 16; i++) { const a = i / 16 * Math.PI / 2; p.push(new THREE.Vector2(0.284 * Math.cos(a), 0.485 + 0.31 * Math.sin(a))); }
  return new THREE.LatheGeometry(p, 48);
})();
const headGeo = new THREE.SphereGeometry(0.185, 40, 28);
export function figure({ scale = 1, glow = 'rgba(255,255,255,1)', glowSize = 1.6, glowOpacity = 0.35, emissive = 0.06 } = {}) {
  const g = new THREE.Group();
  const mat = emissive === 0.06 ? figMat : figMat.clone();
  if (emissive !== 0.06) mat.emissiveIntensity = emissive;
  const body = new THREE.Mesh(bodyGeo, mat), head = new THREE.Mesh(headGeo, mat);
  head.position.y = 0.795 + 0.045 + 0.185;
  g.add(body, head);
  const pool = new THREE.Mesh(new THREE.PlaneGeometry(glowSize, glowSize), new THREE.MeshBasicMaterial({ map: TEX.glow, transparent: true, opacity: glowOpacity, depthWrite: false, blending: THREE.AdditiveBlending, toneMapped: false, color: new THREE.Color(glow) }));
  pool.rotation.x = -Math.PI / 2; pool.position.y = 0.004; pool.scale.set(1, 0.6, 1);
  g.add(pool);
  g.scale.setScalar(scale);
  g.userData = { body, head, pool, mat };
  return g;
}

// ---------------------------------------------------------------- canvas panels (all UI is drawn in 2D, mapped onto 3D planes)
const ICON_CACHE = {};
export function iconPaths(name) {
  if (ICON_CACHE[name]) return ICON_CACHE[name];
  const doc = new DOMParser().parseFromString(`<svg xmlns="http://www.w3.org/2000/svg">${window.ICONS[name]}</svg>`, 'image/svg+xml');
  const out = [];
  for (const e of doc.documentElement.children) {
    const a = k => parseFloat(e.getAttribute(k) || 0);
    let d = '';
    if (e.tagName === 'path') d = e.getAttribute('d');
    else if (e.tagName === 'circle') { const cx = a('cx'), cy = a('cy'), r = a('r'); d = `M${cx - r} ${cy}a${r} ${r} 0 1 0 ${2 * r} 0a${r} ${r} 0 1 0 ${-2 * r} 0`; }
    else if (e.tagName === 'line') d = `M${a('x1')} ${a('y1')}L${a('x2')} ${a('y2')}`;
    else if (e.tagName === 'polyline' || e.tagName === 'polygon') { const p = e.getAttribute('points').trim().split(/[\s,]+/).map(Number); d = 'M' + p.slice(0, 2).join(' ') + 'L' + p.slice(2).join(' ') + (e.tagName === 'polygon' ? 'Z' : ''); }
    else if (e.tagName === 'rect') { const x = a('x'), y = a('y'), w = a('width'), h = a('height'), r = Math.min(a('rx'), w / 2, h / 2); d = `M${x + r} ${y}H${x + w - r}A${r} ${r} 0 0 1 ${x + w} ${y + r}V${y + h - r}A${r} ${r} 0 0 1 ${x + w - r} ${y + h}H${x + r}A${r} ${r} 0 0 1 ${x} ${y + h - r}V${y + r}A${r} ${r} 0 0 1 ${x + r} ${y}Z`; }
    else if (e.tagName === 'ellipse') { const cx = a('cx'), cy = a('cy'), rx = a('rx'), ry = a('ry'); d = `M${cx - rx} ${cy}a${rx} ${ry} 0 1 0 ${2 * rx} 0a${rx} ${ry} 0 1 0 ${-2 * rx} 0`; }
    if (d) out.push(new Path2D(d));
  }
  return (ICON_CACHE[name] = out);
}
export function drawIcon(g, name, cx, cy, size, color, lw = 1.6, glow = 0) {
  g.save(); g.translate(cx - size / 2, cy - size / 2); g.scale(size / 24, size / 24);
  g.strokeStyle = color; g.lineWidth = lw; g.lineCap = 'round'; g.lineJoin = 'round';
  if (glow) { g.shadowColor = color; g.shadowBlur = glow; }
  for (const p of iconPaths(name)) g.stroke(p);
  g.restore();
}
export function text(g, s, x, y, { size = 40, weight = 800, color = C.white, align = 'center', spacing = 0, font = 'Inter', glow = 0, baseline = 'middle' } = {}) {
  g.save(); g.font = `${weight} ${size}px "${font}"`; g.textAlign = align; g.textBaseline = baseline; g.fillStyle = color;
  g.letterSpacing = spacing ? `${spacing}px` : '0px';
  if (glow) { g.shadowColor = color; g.shadowBlur = glow; }
  g.fillText(s, x, y); g.restore();
}
export function rrect(g, x, y, w, h, r) { g.beginPath(); g.roundRect(x, y, w, h, r); }

export const PANELS = [];
export class Panel {
  // w,h in world units; draw(g, t, P) paints in canvas pixels (P.cw x P.ch). key(t) -> redraw only when it changes.
  constructor({ w, h, ppu = 360, draw, key = null, boost = 1.0, opacity = 1, additive = false, fog = true }) {
    this.cw = Math.round(Math.min(2048, w * ppu)); this.ch = Math.round(Math.min(2048, h * ppu));
    this.canvas = document.createElement('canvas'); this.canvas.width = this.cw; this.canvas.height = this.ch;
    this.g = this.canvas.getContext('2d');
    this.tex = new THREE.CanvasTexture(this.canvas); this.tex.colorSpace = THREE.SRGBColorSpace; this.tex.anisotropy = 8;
    this.mat = new THREE.MeshBasicMaterial({ map: this.tex, transparent: true, opacity, depthWrite: false, toneMapped: false, side: THREE.DoubleSide, fog, blending: additive ? THREE.AdditiveBlending : THREE.NormalBlending });
    this.mat.color.setScalar(boost);
    this.mat.onBeforeCompile = sh => { sh.fragmentShader = sh.fragmentShader.replace('#include <map_fragment>', '#ifdef USE_MAP\n vec4 sampledDiffuseColor = texture2D( map, vMapUv, -0.85 );\n diffuseColor *= sampledDiffuseColor;\n#endif'); };
    this.mesh = new THREE.Mesh(new THREE.PlaneGeometry(w, h), this.mat);
    this.mesh.userData.panel = this;
    this.draw = draw; this.key = key; this.lastKey = undefined; this.w = w; this.h = h;
    PANELS.push(this);
  }
  update(t) {
    if (!this.mesh.visible || !this.inScene()) return;
    const k = this.key ? this.key(t) : 'static';
    if (k === this.lastKey) return;
    this.lastKey = k;
    this.g.clearRect(0, 0, this.cw, this.ch);
    this.draw(this.g, t, this);
    this.tex.needsUpdate = true;
  }
  inScene() { let o = this.mesh; while (o) { if (!o.visible) return false; o = o.parent; } return true; }
}

// ---------------------------------------------------------------- particles (deterministic: positions are functions of t)
export function particles({ count, texture, size = 0.12, color = '#ffffff', boost = 2, fn, additive = true }) {
  const geo = new THREE.BufferGeometry();
  const pos = new Float32Array(count * 3), alpha = new Float32Array(count);
  geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  geo.setAttribute('alpha', new THREE.BufferAttribute(alpha, 1));
  const mat = new THREE.ShaderMaterial({
    uniforms: { map: { value: texture }, size: { value: size * H / 2 }, color: { value: new THREE.Color(color).multiplyScalar(boost) } },
    vertexShader: `attribute float alpha; varying float vA; uniform float size;
      void main(){ vec4 mv = modelViewMatrix * vec4(position,1.0); vA = alpha * smoothstep(0.35, 1.4, -mv.z); gl_PointSize = min(size / -mv.z * projectionMatrix[1][1], 90.0); gl_Position = projectionMatrix * mv; }`,
    fragmentShader: `uniform sampler2D map; uniform vec3 color; varying float vA;
      void main(){ vec4 c = texture2D(map, vec2(gl_PointCoord.x, 1.0 - gl_PointCoord.y)); gl_FragColor = vec4(color * c.rgb, c.a * vA); }`,
    transparent: true, depthWrite: false, blending: additive ? THREE.AdditiveBlending : THREE.NormalBlending,
  });
  const pts = new THREE.Points(geo, mat); pts.frustumCulled = false;
  pts.userData.update = t => { fn(t, pos, alpha); geo.attributes.position.needsUpdate = true; geo.attributes.alpha.needsUpdate = true; };
  return pts;
}
export function mulberry32(a) { return function () { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }

// ambient dust specks (world space, always present)
const DR = mulberry32(5), DUST = Array.from({ length: 260 }, () => [(DR() - 0.5) * 30, DR() * 9, -DR() * 30 + 6, DR() * 6.28, 0.3 + DR()]);
export const dust = particles({
  count: DUST.length, texture: TEX.soft, size: 0.035, color: '#cfd8ff', boost: 1.6,
  fn: (t, p, a) => DUST.forEach((d, i) => { p[i * 3] = d[0] + Math.sin(t * 0.2 * d[4] + d[3]) * 0.4 + camState.x * 0.6; p[i * 3 + 1] = (d[1] + t * 0.08 * d[4]) % 9; p[i * 3 + 2] = d[2] + camState.z * 0.6; a[i] = (0.25 + 0.5 * Math.abs(Math.sin(t * 0.7 * d[4] + d[3]))); }),
});
scene.add(dust);

// ---------------------------------------------------------------- camera rig
export const camState = { x: 0, y: 1.2, z: 8, tx: 0, ty: 1.1, tz: 0, roll: 0, fov: 30, shake: 0 };
export function camTo(t, vars, dur = 1.2, ease = 'power2.inOut') { tl.to(camState, Object.assign({ duration: dur, ease }, vars), t); }
export function camSet(t, vars) { tl.set(camState, vars, t); }
export function shake(t, amp = 1, dur = 0.5) { tl.fromTo(camState, { shake: amp }, { shake: 0, duration: dur, ease: 'power2.out', immediateRender: false }, t); }
function applyCamera(t) {
  const k = camState.shake, n = (a, b) => Math.sin(t * a) * 0.6 + Math.sin(t * b + 1.7) * 0.4;
  const breathe = 0.02;
  camera.position.set(camState.x + k * 0.05 * n(57, 91) + Math.sin(t * 0.31) * breathe, camState.y + k * 0.05 * n(63, 41) + Math.sin(t * 0.27) * breathe, camState.z);
  camera.lookAt(camState.tx, camState.ty, camState.tz);
  camera.rotateZ(THREE.MathUtils.degToRad(camState.roll + k * 0.6 * n(47, 77)));
  if (camera.fov !== camState.fov) { camera.fov = camState.fov; camera.updateProjectionMatrix(); }
}

// ---------------------------------------------------------------- post: bloom + film (vignette, grain, chromatic aberration, flash, zoom blur)
export const composer = new EffectComposer(renderer, new THREE.WebGLRenderTarget(W, H, { type: THREE.HalfFloatType }));
composer.setPixelRatio(1); composer.setSize(W, H);
composer.addPass(new RenderPass(scene, camera));
export const bloom = new UnrealBloomPass(new THREE.Vector2(W / 2, H / 2), 0.8, 0.22, 1.6);
bloom.compositeMaterial.uniforms.bloomFactors.value = [1.0, 0.55, 0.22, 0.07, 0.02]; // glow hugs its source, no frame-wide haze
composer.addPass(bloom);
composer.addPass(new OutputPass());
export const film = new ShaderPass({
  uniforms: { tDiffuse: { value: null }, time: { value: 0 }, ca: { value: 0.006 }, vig: { value: 0.6 }, grain: { value: 0.065 }, flash: { value: 0 }, flashColor: { value: new THREE.Color(1, 1, 1) }, zoom: { value: 0 }, fade: { value: 0 }, flicker: { value: 0 } },
  vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }`,
  fragmentShader: /* glsl */`
    uniform sampler2D tDiffuse; uniform float time, ca, vig, grain, flash, zoom, fade, flicker; uniform vec3 flashColor; varying vec2 vUv;
    float hash(vec2 p){ return fract(sin(dot(p, vec2(12.9898,78.233))) * 43758.5453); }
    vec3 samp(vec2 uv, float r){ vec2 d = uv - 0.5; return vec3(texture2D(tDiffuse, uv + d*ca*r).r, texture2D(tDiffuse, uv).g, texture2D(tDiffuse, uv - d*ca*r).b); }
    void main(){
      vec2 d = vUv - 0.5; float r = dot(d, d) * 4.0;
      vec3 col = samp(vUv, r);
      if (zoom > 0.001) { for (int i = 1; i < 10; i++) { float s = 1.0 - zoom * float(i) / 9.0 * 0.12; col += samp(0.5 + d * s, r); } col /= 10.0; }
      col *= mix(1.0, smoothstep(1.25, 0.15, r), vig);
      col += (hash(vUv * vec2(1080.0, 1920.0) + fract(time * 7.13) * 100.0) - 0.5) * grain;
      col = mix(col, flashColor, flash);
      col *= (1.0 - fade) * (1.0 - flicker);
      float l = dot(col, vec3(0.299, 0.587, 0.114)); col = mix(vec3(l), col, 0.92); // slight desaturation
      gl_FragColor = vec4(col, 1.0);
    }`,
});
composer.addPass(film);
export const post = { flash: 0, zoom: 0, fade: 0, bloom: 0.7, flicker: 0 };
export function flash(t, a = 0.5, dur = 0.35, color = '#ffffff') { tl.set(film.uniforms.flashColor, { r: new THREE.Color(color).r, g: new THREE.Color(color).g, b: new THREE.Color(color).b }, t); tl.fromTo(post, { flash: a }, { flash: 0, duration: dur, ease: 'power2.out', immediateRender: false }, t); }
export function zoomBlur(t, a = 1, dur = 0.35) { tl.fromTo(post, { zoom: a }, { zoom: 0, duration: dur, ease: 'power2.out', immediateRender: false }, t); }

// ---------------------------------------------------------------- shots & frame loop
export const SHOTS = [];
export function shot(t0, t1, build) {
  const g = new THREE.Group(), h = new THREE.Group(); g.visible = h.visible = false;
  scene.add(g); camera.add(h); SHOTS.push({ g, h, t0, t1 }); build(g, h); return g;
}
scene.add(camera); camera.layers.enable(1);
export const UPDATERS = [];
export function every(fn) { UPDATERS.push(fn); }

export function renderAt(t) {
  tl.seek(t, false);
  for (const s of SHOTS) s.g.visible = s.h.visible = t >= s.t0 && t < s.t1;
  for (const f of UPDATERS) f(t);
  scene.traverseVisible(o => { if (o.userData.update) o.userData.update(t); });
  for (const p of PANELS) p.update(t);
  applyCamera(t);
  film.uniforms.time.value = t; film.uniforms.flash.value = post.flash; film.uniforms.zoom.value = post.zoom; film.uniforms.fade.value = post.fade; film.uniforms.flicker.value = post.flicker;
  bloom.strength = post.bloom;
  composer.render();
}
