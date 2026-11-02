
// ================================================================== HUD SETUP
const GRAD_PAX = 'linear-gradient(90deg, #FFD27A 0%, #FF9E5E 45%, #FF6FB5 100%)';
const GRAD_ALL = 'linear-gradient(90deg, #5AA9FF 0%, #A06BFF 50%, #FF6FB5 100%)';
const oPax = new Odo($('oPax'), 6, 56, 35, true, GRAD_PAX);
const oDep = new Odo($('oDep'), 3, 52, 32, false, null);
const oArr = new Odo($('oArr'), 3, 52, 32, false, null);
const oT1 = new Odo($('oT1'), 3, 64, 40, false, null); $('oT1').style.color = 'var(--arr)';
const oT2 = new Odo($('oT2'), 3, 64, 40, false, null); $('oT2').style.color = 'var(--dep)';
const oT3 = new Odo($('oT3'), 6, 64, 40, true, GRAD_PAX);
const oT4 = new Odo($('oT4'), 4, 64, 40, true, GRAD_ALL);
$('hTitle').textContent = AP.header; $('tBig').textContent = AP.titleBig;
// sunrise / sunset (local minutes) for the day bar
const elAt = mm => Math.asin(clamp(sunLocal(mm).y, -1, 1)) / D2R;
let SUNRISE = 0, SUNSET = 0; for (let mm = 1; mm < 1440; mm++) { if (elAt(mm - 1) < -0.83 && elAt(mm) >= -0.83) SUNRISE = mm; if (elAt(mm - 1) >= -0.83 && elAt(mm) < -0.83) SUNSET = mm; }
{ const p = mm => (mm / 1440 * 100).toFixed(1) + '%';
  const gstr = `linear-gradient(90deg, #0d1838 0%, #18265a ${p(SUNRISE - 40)}, #f2955c ${p(SUNRISE)}, #64aef7 ${p(SUNRISE + 60)}, #6fb6ff 50%, #64aef7 ${p(SUNSET - 60)}, #f0784a ${p(SUNSET)}, #2b2f6c ${p(SUNSET + 50)}, #0d1838 100%)`;
  $('track').style.background = gstr; $('fill').style.background = gstr; $('fill').style.backgroundSize = '860px 8px'; }

const TOASTS = AP.toasts(FL, ROUTES, S, hhmm, pad2).map(x => {
  let m = x.m; if (typeof m === 'string' && m.startsWith('pax')) { const thr = parseInt(m.slice(3)) * 1000; let s = 0; m = 1200; for (const f of FL) { s += f.pax; if (s >= thr) { m = f.t; break; } } }
  return { ...x, m, tm: x.tm || hhmm(m) };
});
for (const g of GA_EV) TOASTS.push({ m: g.m, tm: hhmm(g.m), a: 'GO-AROUND', b: `${g.cs} climbs away from runway ${g.rw}` });
TOASTS.sort((a, b) => a.m - b.m); TOASTS.forEach(x => x.t = vidT(x.m));
let lastToast = -1;

$('glG').style.zIndex = 0; $('glA').style.zIndex = 1; $('vignette').style.zIndex = 2; $('hud').style.zIndex = 3; $('introLayer').style.zIndex = 4; $('finale').style.zIndex = 5;
const fade = (id, a, dy = 0) => { const e = $(id); e.style.opacity = a; if (dy) e.style.transform = `translateY(${(1 - a) * dy}px)`; };

// ================================================================== FRAME
function renderFrame(t) {
  const m = dayMin(t), vm = visMin(t);
  const fin = smooth(52.0, 54.0, t);
  // ---- globe
  const [glat, glon, gd, gy] = globeCam(t);
  setGlobeCenter(500, gy);
  camG.position.copy(llv(glat, glon + Math.sin(t * 0.13) * 1.2, gd)); camG.up.set(0, 1, 0); camG.lookAt(0, 0, 0);
  camG.near = Math.max(0.01, gd - 1.25); camG.far = 120; camG.updateProjectionMatrix();
  const sunG = sunECEF(mod1440(vm));
  globeMat.uniforms.sunDir.value.copy(sunG); globeMat.uniforms.camPos.value.copy(camG.position); atmoMat.uniforms.sunDir.value.copy(sunG);
  const gs = updateGlobe(t, vm, fin);
  rG.render(sceneG, camG);

  // ---- airport
  const fullMode = t < 8.6;
  const aOp = fullMode ? 1 - smooth(7.2, 8.4, t) : smooth(9.0, 9.6, t) * (1 - smooth(52.0, 52.7, t));
  setAMode(fullMode ? 'full' : 'inset');
  $('glA').style.opacity = aOp;
  const cam = airportCam(t);
  const lit = lightAirport(t, fullMode ? 0 : vm, cam, fullMode ? W : CAMR.w, fullMode ? H : CAMR.h);
  if (aOp > 0.001) { updateAirport(t, lit.night, cam); rA.render(sceneA, camA); }

  // ---- intro titles
  const io = 1 - smooth(5.8, 6.5, t);
  $('introLayer').style.opacity = io; $('introLayer').style.display = io > 0.001 ? 'block' : 'none';
  if (io > 0.001) {
    const h = $('tBig'); const k1 = easeOut((t - 0.6) / 1.5);
    h.style.opacity = smooth(0.6, 1.4, t); h.style.letterSpacing = lerp(40, 4, k1) + 'px'; h.style.transform = `scale(${lerp(1.08, 1, k1)})`;
    h.style.filter = `blur(${lerp(14, 0, smooth(0.6, 1.6, t))}px) drop-shadow(0 0 26px rgba(140,120,255,${0.55 * smooth(1.2, 2.0, t)}))`;
    fade('tSky', smooth(1.6, 2.3, t), 22); $('tSky').style.letterSpacing = lerp(18, 8, easeOut((t - 1.6) / 1.2)) + 'px';
    const rw = 320 * easeOut((t - 2.0) / 0.9); $('tRule').style.width = rw + 'px'; $('tRule').style.left = (500 - rw / 2) + 'px';
    for (const [id, t0] of [['s1', 3.0], ['s2', 3.5], ['s3', 4.0]]) { const a = smooth(t0, t0 + 0.4, t); const e = $(id); e.style.opacity = a; e.style.transform = `translateY(${(1 - a) * 14}px)`; }
    $('intro').style.transform = `translateY(${-smooth(5.8, 6.5, t) * 30}px)`;
  }

  // ---- HUD visibility
  const hudOut = 1 - smooth(52.0, 52.8, t);
  fade('hdr', smooth(8.6, 9.4, t) * hudOut, -20); $('hdrShade').style.opacity = smooth(8.6, 9.4, t) * hudOut;
  for (const id of ['inair', 'view', 'legend']) fade(id, smooth(8.9, 9.7, t) * hudOut);
  $('labels').style.opacity = smooth(8.9, 9.7, t) * (1 - fin);
  fade('stats', smooth(9.0, 9.9, t) * hudOut, 30);
  const rowA = smooth(9.0, 9.6, t) * hudOut * (fullMode ? 0 : 1);
  for (const id of ['camEdge', 'camLabel', 'wchip', 'radar', 'radarEdge']) $(id).style.opacity = rowA;
  let dip = 0; for (const c of CUTS) dip = Math.max(dip, 1 - smooth(0, 0.24, Math.abs(t - c)));
  $('camDip').style.opacity = fullMode ? 0 : dip * hudOut;
  if (rowA > 0.001) drawRadar(t, m);

  // header
  $('clock').textContent = hhmm(t >= TE ? 1439.99 : m);
  $('clocksub').textContent = (t >= TE ? 'END OF DAY · ' : 'LOCAL TIME · ') + AP.tz;
  const frac = clamp(m / 1440, 0, 1);
  $('fill').style.width = (frac * 860) + 'px'; $('marker').style.left = (frac * 860) + 'px';
  const isDay = lit.el > -0.8;
  $('marker').style.background = isDay ? 'radial-gradient(circle, #fff6c8 0%, #FFD166 55%, rgba(255,209,102,0) 72%)' : 'radial-gradient(circle, #ffffff 0%, #c9d6ff 50%, rgba(201,214,255,0) 72%)';
  $('marker').style.boxShadow = isDay ? '0 0 14px 5px rgba(255,200,90,0.55)' : '0 0 12px 4px rgba(170,190,255,0.5)';
  for (let h = 0; h < 24; h++) {
    const n = ub(allT, Math.min(m, (h + 1) * 60)) - ub(allT, h * 60);
    hourBars[h].style.height = (Math.max(0, n) / HMAX * 24) + 'px'; hourBars[h].style.width = '29px';
    hourBars[h].style.opacity = (m >= h * 60 && m < (h + 1) * 60) ? 1 : 0.5;
  }
  $('inairN').textContent = fmt(gs.inAir);
  let vn = ''; for (const [vt, name] of VIEWS) if (t >= vt - 1.2) vn = name; $('view').textContent = vn ? 'VIEW · ' + vn : '';

  // counters
  oPax.set(paxAt(m)); oDep.set(contCount(depT, m)); oArr.set(contCount(arrT, m));
  const lastH = arr => ub(arr, m) - ub(arr, m - 60);
  $('sPax').textContent = m > 30 ? `+${fmt(paxAt(m) - paxAt(m - 60))} last hour` : '';
  $('sDep').textContent = m > 30 ? `+${lastH(depT)} last hour` : '';
  $('sArr').textContent = m > 30 ? `+${lastH(arrT)} last hour` : '';

  // globe labels
  const camDir = camG.position.clone().normalize();
  const wA = smooth(7.0, 8.5, gd), eA = 1 - smooth(6.6, 8.0, gd);
  const proj = v => { const p = v.clone().project(camG); return [(p.x + 1) / 2 * W, (1 - p.y) / 2 * H]; };
  const inBox = (x, y) => x > 80 && x < 920 && y > 345 && y < 895 ? 1 : 0;
  const hubS = proj(LV.clone().multiplyScalar(1.01));
  for (const L of labelEls) {
    const rt = RT[L.i]; const vis = smooth(0.12, 0.35, rt.v.dot(camDir));
    const [x, y] = proj(rt.v.clone().multiplyScalar(1.01));
    const served = ub(routeTimes[L.i], vm) > 0 || gs.act[L.i] > 0;
    L.el.style.left = x + 'px'; L.el.style.top = y + 'px';
    L.el.style.opacity = vis * (L.kind === 'w' ? wA : eA) * (served ? 0.55 + 0.45 * Math.min(1, gs.act[L.i] / 2) : 0.3) * inBox(x, y) * smooth(50, 80, Math.hypot(x - hubS[0], y - hubS[1]));
  }
  for (const B of busyEls) {
    const rt = RT[B.i]; const vis = smooth(0.12, 0.35, rt.v.dot(camDir));
    const [x, y] = proj(rt.v.clone().multiplyScalar(1.01));
    B.el.style.left = x + 'px'; B.el.style.top = y + 'px';
    B.el.style.opacity = vis * smooth(55, 90, Math.hypot(x - hubS[0], y - hubS[1])) * inBox(x, y) * (ub(routeTimes[B.i], vm) > 0 ? 1 : 0) * (1 - fin);
    B.el.querySelector('.n').textContent = '× ' + ub(routeTimes[B.i], Math.min(vm, 1440));
  }
  lhrLabel.style.left = (hubS[0] - 14) + 'px'; lhrLabel.style.top = (hubS[1] + 10) + 'px'; lhrLabel.style.transform = 'translate(-100%, 0)';
  lhrLabel.style.opacity = smooth(0.12, 0.3, LV.dot(camDir)) * (1 - fin) * inBox(hubS[0], hubS[1]);

  // time cards
  let tA = 0, tI = -1;
  TOASTS.forEach((x, i) => { const a = smooth(x.t - 0.05, x.t + 0.25, t) * (1 - smooth(x.t + 1.75, x.t + 2.05, t)); if (a > tA) { tA = a; tI = i; } });
  const toast = $('toast'); toast.style.opacity = tA * hudOut; toast.style.transform = `translateX(-50%) translateY(${(1 - tA) * -10}px)`;
  if (tI >= 0 && tI !== lastToast) { const x = TOASTS[tI]; toast.querySelector('.tm').textContent = x.tm; toast.querySelector('.tx').textContent = x.a; toast.querySelector('.t2').textContent = x.b; lastToast = tI; }

  // live cam overlays
  $('camName').textContent = cam.name || '';
  const wx = lit.wx;
  $('needle').setAttribute('transform', `rotate(${wx.dir + 180})`);
  $('wA').textContent = `${compassPt(wx.dir)} ${Math.round(wx.kt)} kt`;
  $('wB').textContent = wx.gust > wx.kt + 6 ? `GUSTS ${Math.round(wx.gust)} KT` : `${Math.round(wx.dir)}° WIND`;
  $('wT').textContent = Math.round(wx.temp) + '°C';
  const cond = condOf(wx, lit.el); $('wC').textContent = cond;
  const icon = cond === 'SHOWERS' || cond === 'LIGHT RAIN' ? 'RAIN' : cond === (AP.mistName || 'MIST') ? 'MIST' : cond === 'CLOUDY' ? 'CLOUD' : cond === 'PARTLY CLOUDY' ? (lit.el > 0 ? 'PART_D' : 'PART_N') : (lit.el > 0 ? 'SUNNY' : 'CLEAR');
  if (icon !== lastIcon) { $('wicon').innerHTML = ICONS[icon]; lastIcon = icon; }

  // ---- finale
  const fo = smooth(52.2, 53.0, t); $('finale').style.opacity = fo; $('finale').style.display = fo > 0.001 ? 'block' : 'none';
  if (fo > 0.001) {
    $('fShade').style.opacity = fo;
    for (const [id, t0] of [['f1', 52.5], ['f2', 53.5], ['f3', 54.5]]) { const a = smooth(t0, t0 + 0.45, t); const e = $(id); e.style.opacity = a; e.style.transform = `translateY(${(1 - a) * 22}px)`; e.style.letterSpacing = lerp(14, 2, easeOut((t - t0) / 0.7)) + 'px'; }
    const tots = [[oT1, S.stats.arr, 'r1', 55.3], [oT2, S.stats.dep, 'r2', 55.8], [oT3, S.stats.pax, 'r3', 56.3], [oT4, S.stats.dep + S.stats.arr, 'r4', 56.8]];
    for (const [o, val, id, t0] of tots) { const a = smooth(t0, t0 + 0.4, t); const e = $(id); e.style.opacity = a; e.style.transform = `translateX(${(1 - a) * 50}px)`; o.set(val * easeOut((t - t0 - 0.1) / 1.5)); }
    $('fFoot').style.opacity = smooth(58.0, 58.6, t);
  }
  return true;
}
window.renderFrame = renderFrame;

window.getAudioEvents = () => {
  const samples = [];
  for (let t = 0; t <= 60.001; t += 0.05) {
    const m = dayMin(t); const w = wxAt(m); const el = Math.asin(clamp(sunLocal(mod1440(visMin(t))).y, -1, 1)) / D2R;
    samples.push({ t: +t.toFixed(3), kt: w.kt, gust: w.gust, rain: w.rain, rate: (t >= T0 && t < TE) ? hourRate(m) : 0, night: 1 - smooth(-7, 3, el) });
  }
  const milestones = [50000, 100000, 150000, 200000].filter(p => p < S.stats.pax).map(p => { let s = 0; for (const f of FL) { s += f.pax; if (s >= p) return vidT(f.t); } return null; });
  const shotOf = t => { let s = SHOTS[SHOTS.length - 1]; for (const x of SHOTS) if (t < x.t1) { s = x; break; } return s; };
  return {
    inset: ALL_EV.map(e => ({ t: e.t, type: e.type === 'G' ? 'D' : e.type, ga: e.type === 'G', wide: e.wide, rw: e.rw, intro: !!e.intro, near: e.intro || e.t < 8.6 ? 0.8 : shotOf(e.t).near, sf: e.intro ? 0.5 : shotOf(e.t).sf })),
    toasts: TOASTS.map(x => x.t), hours: [...Array(25)].map((_, h) => vidT(h * 60)), samples, milestones, cuts: CUTS, ga: GA_EV.map(g => g.t),
    T_RISE, T0, TN, TE, switchT: -1, sunrise: vidT(SUNRISE), sunset: vidT(SUNSET),
    title: 0.7, sky: 1.6, subs: [3.0, 3.5, 4.0], tag: [52.5, 53.5, 54.5], totals: [55.3, 55.8, 56.3, 56.8],
  };
};
window.READY = true;
