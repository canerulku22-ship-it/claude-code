const TAN3 = Math.tan(3 * D2R);
function arrPose(tau, rw) {
  const R = RW[rw]; const xtd = R.e - 400; const side = R.z < 0 ? 1 : -1;
  let x, y = 0, z = R.z, hd = Math.PI, pitch = 0, alpha = 1, land = 0;
  if (tau < 0) { const d = -tau * 3250; x = xtd + d; y = d > 250 ? d * TAN3 + 12 : 25.1 * Math.pow(d / 250, 1.6); pitch = 3 * D2R; alpha = smooth(-2.15, -1.85, tau); land = 1; }
  else if (tau < 0.93) { const a = 2849.5; const d = 3250 * tau - 0.5 * a * tau * tau; x = xtd - d; pitch = 3 * D2R * (1 - smooth(0, 0.15, tau)); land = 1 - smooth(0.3, 0.6, tau); }
  else { const u = tau - 0.93; const th = smooth(0, 0.3, u) * 38 * D2R; x = xtd - 1790 - 520 * u * Math.cos(th * 0.5); z = R.z + side * 520 * u * Math.sin(th * 0.6); hd = Math.PI + side * th; alpha = 1 - smooth(0.2, 0.5, u); }
  return { x, y, z, hd, pitch, alpha, land };
}
function depPose(tau, rw, seed) {
  const R = RW[rw]; const x0 = R.e - 60; const side = R.z < 0 ? 1 : -1;
  let x, y = 0, z = R.z, hd = Math.PI, pitch = 0, alpha = 1, land = 0;
  if (tau < 0) { const u = smooth(-0.36, 0, tau); const ang = u * Math.PI / 2; x = x0 + 110 * Math.sin(Math.PI / 2 - ang) * 0 + 110 * (1 - Math.sin(ang)); z = R.z + side * 120 * (1 - Math.sin(ang + 0.0)) * (1 - u * 0.0); hd = Math.PI / 2 * side * -1 * (1 - u) + Math.PI * u; if (side < 0) hd = -Math.PI / 2 * (1 - u) + Math.PI * u; else hd = Math.PI / 2 * (1 - u) + Math.PI * u; alpha = smooth(-0.46, -0.32, tau); land = 0.6; }
  else if (tau < 0.81) { const d = 0.5 * 5487 * tau * tau; x = x0 - d; land = 1; pitch = 0; if (tau > 0.72) pitch = smooth(0.72, 0.81, tau) * 7 * D2R; }
  else {
    const u = tau - 0.81; const d = 1800 + 4444 * u + 300 * u * u; x = x0 - d; y = 560 * Math.pow(u, 1.15); pitch = (7 + 3 * smooth(0, 0.2, u)) * D2R; land = 1 - smooth(0.5, 0.9, u);
    const turn = (seed < 0.5 ? -1 : 1) * smooth(0.9, 1.9, u) * 28 * D2R; hd = Math.PI + turn;
    z = R.z + (seed < 0.5 ? 1 : -1) * 2200 * Math.pow(smooth(0.9, 2.2, u), 1.6);
    alpha = 1 - smooth(1.9, 2.5, u);
  }
  return { x, y, z, hd, pitch, alpha, land };
}

