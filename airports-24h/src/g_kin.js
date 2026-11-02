
// ================================================================== KINETIC TYPE (every word animates in and out)
const GSTOPS = ['#5AA9FF', '#A06BFF', '#FF6FB5'];
function gradAt(f) { const k = clamp(f, 0, 1) * 2, i = Math.min(1, Math.floor(k)); return new THREE.Color(GSTOPS[i]).lerp(new THREE.Color(GSTOPS[i + 1]), k - i).getStyle(); }
const backOut = k => { const c1 = 1.9, c3 = c1 + 1; return 1 + c3 * Math.pow(k - 1, 3) + c1 * Math.pow(k - 1, 2); };
const WORD_TICKS = [];   // times of prominent word pops (for the soundtrack)
function kinPrep(el, text, mode) {
  if (el.__kt === text && el.__km === mode) return el.__sp;
  el.__kt = text; el.__km = mode; el.textContent = '';
  if (el.classList.contains('grad')) { el.classList.remove('grad'); el.dataset.grad = '1'; }
  const parts = mode === 'char' ? [...text] : text.split(/(\s+)/);
  const sp = [];
  for (const p of parts) {
    if (p === '') continue;
    if (/^\s+$/.test(p)) { el.appendChild(document.createTextNode(' ')); continue; }
    const s = document.createElement('span'); s.textContent = p; s.style.display = 'inline-block'; s.style.whiteSpace = 'pre'; s.style.transformOrigin = '50% 70%';
    el.appendChild(s); sp.push(s);
  }
  if (el.dataset.grad) sp.forEach((s, i) => s.style.color = gradAt((i + 0.5) / sp.length));
  el.__sp = sp; return sp;
}
// o: mode ('word'|'char'), stagger, dIn, dOut, outStagger, s0 (start scale), y0, blur, r0, color0 (first word colour)
function kin(el, text, tIn, tOut, t, o = {}) {
  const sp = kinPrep(el, text, o.mode || 'word');
  const st = o.stagger ?? 0.06, dIn = o.dIn ?? 0.34, dOut = o.dOut ?? 0.22, so = o.outStagger ?? st * 0.5;
  if (o.color0 && sp[0]) sp[0].style.color = o.color0;
  let vis = 0;
  sp.forEach((s, i) => {
    const a = clamp((t - (tIn + i * st)) / dIn, 0, 1);
    const b = tOut == null ? 0 : clamp((t - (tOut + i * so)) / dOut, 0, 1);
    const ein = backOut(a), eo = b * b;
    const op = clamp(a * 2.2, 0, 1) * (1 - b); vis = Math.max(vis, op);
    const sc = lerp(o.s0 ?? 0.35, 1, ein) * lerp(1, 0.6, eo);
    const ty = lerp(o.y0 ?? 26, 0, ein) - 18 * eo;
    const bl = (1 - a) * (o.blur ?? 7) + b * 6;
    const rot = lerp(o.r0 ?? -8, 0, clamp(ein, 0, 1));
    s.style.opacity = op.toFixed(3);
    s.style.transform = `translateY(${ty.toFixed(1)}px) scale(${sc.toFixed(3)}) rotate(${rot.toFixed(2)}deg)`;
    s.style.filter = bl > 0.15 ? `blur(${bl.toFixed(1)}px)` : 'none';
  });
  return vis;
}
// whole-element pop (boxes, pills, chips)
function pop(el, tIn, tOut, t, o = {}) {
  const a = clamp((t - tIn) / (o.dIn ?? 0.32), 0, 1), b = tOut == null ? 0 : clamp((t - tOut) / (o.dOut ?? 0.22), 0, 1);
  const sc = lerp(o.s0 ?? 0.6, 1, backOut(a)) * lerp(1, 0.75, b * b);
  el.style.opacity = (clamp(a * 2, 0, 1) * (1 - b)).toFixed(3);
  el.style.transform = (o.pre || '') + ` translateY(${((1 - backOut(a)) * (o.y0 ?? 18) - 10 * b * b).toFixed(1)}px) scale(${sc.toFixed(3)})`;
  return a * (1 - b);
}
