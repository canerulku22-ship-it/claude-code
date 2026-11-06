
// ================================================================== LANDMARKS
const LANDMARK = (() => {
  const upd = [];
  if (AP.landmark === 'themeBuilding') {
    // LAX Theme Building: two crossing parabolic arches over a flying-saucer restaurant
    const x0 = 60, z0 = 0;
    const mat = new THREE.MeshLambertMaterial({ color: 0xf2f3f5, emissive: 0x8a5cff, emissiveIntensity: 0 });
    for (const th of [0.42, -0.42]) {
      const pts = []; for (let i = 0; i <= 40; i++) { const s = i / 20 - 1; pts.push(new THREE.Vector3(x0 + s * 38 * Math.cos(th), 43 * (1 - s * s), z0 + s * 38 * Math.sin(th))); }
      const tube = new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 60, 1.9, 10, false), mat); sceneA.add(tube);
    }
    const disc = new THREE.Mesh(new THREE.CylinderGeometry(15, 12, 5, 32), mat); disc.position.set(x0, 22, z0); sceneA.add(disc);
    const stem = new THREE.Mesh(new THREE.CylinderGeometry(3.5, 4.5, 22, 16), mat); stem.position.set(x0, 11, z0); sceneA.add(stem);
    const glow = pointsGeo(1); glow.attributes.position.setXYZ(0, x0, 26, z0); glow.attributes.acol.setXYZ(0, 0.65, 0.45, 1); glow.attributes.size.setX(0, 140); glow.attributes.alpha.setX(0, 0);
    const gm = glowMat(false); const gp = new THREE.Points(glow, gm); gp.frustumCulled = false; sceneA.add(gp);
    // gateway pylons at the Century Blvd entrance, cycling colours at night
    const pyl = [];
    for (let i = 0; i < 15; i++) { const a = i / 15 * Math.PI * 2; const m = new THREE.MeshLambertMaterial({ color: 0xdfe3ea, emissive: 0xffffff, emissiveIntensity: 0 }); const p = new THREE.Mesh(new THREE.CylinderGeometry(2.6, 2.6, 34, 12), m); p.position.set(1180 + Math.cos(a) * 95, 17, Math.sin(a) * 55); sceneA.add(p); pyl.push(m); }
    for (let i = 0; i < 11; i++) { const m = new THREE.MeshLambertMaterial({ color: 0xdfe3ea, emissive: 0xffffff, emissiveIntensity: 0 }); const p = new THREE.Mesh(new THREE.CylinderGeometry(1.6, 1.6, 22, 10), m); p.position.set(1350 + i * 140, 11, -38); sceneA.add(p); pyl.push(m); }
    const c = new THREE.Color();
    upd.push((t, night) => {
      mat.emissiveIntensity = 0.12 + night * 0.75; mat.emissive.setHSL(0.72 + 0.05 * Math.sin(t * 0.5), 0.8, 0.55);
      glow.attributes.alpha.setX(0, night * 0.5); glow.attributes.alpha.needsUpdate = true; gm.uniforms.uScale.value = camA.userData.us || 600;
      pyl.forEach((m, i) => { c.setHSL(((t * 0.08 + i * 0.045) % 1), 0.85, 0.55); m.emissive.copy(c); m.emissiveIntensity = 0.15 + night * 1.1; });
    });
  }
  if (AP.landmark === 'gatwickSatellite') {
    // South Terminal circular satellite
    const m = new THREE.MeshLambertMaterial({ color: 0xc3c9cf, emissive: 0xffd9a0, emissiveIntensity: 0 });
    const s = new THREE.Mesh(new THREE.CylinderGeometry(70, 70, 16, 40), m); s.position.set(AP.satellite.x, 8, AP.satellite.z); sceneA.add(s);
    upd.push((t, night) => { m.emissiveIntensity = 0.1 + night * 0.6; });
  }
  if (AP.landmark === 'tulipTower') {
    // Istanbul Airport's tulip-shaped control tower
    const T = AP.tulip; const prof = [[11, 0], [9, 14], [6.8, 38], [5.6, 58], [6.2, 68], [9.5, 75], [14.5, 81], [17.5, 87], [16.5, 92], [12, 96], [6, 98.5], [0.1, 99.5]];
    const mat = new THREE.MeshLambertMaterial({ color: 0xeef2f6, emissive: 0xbfe0ff, emissiveIntensity: 0 });
    const tul = new THREE.Mesh(new THREE.LatheGeometry(prof.map(p => new THREE.Vector2(p[0], p[1])), 32), mat); tul.position.set(T.x, 0, T.z); sceneA.add(tul);
    const ribs = new THREE.MeshLambertMaterial({ color: 0xc8102e, emissive: 0xc8102e, emissiveIntensity: 0 });
    for (let k = 0; k < 6; k++) { const a = k / 6 * Math.PI * 2; const pts = prof.slice(4, 10).map(p => new THREE.Vector3(T.x + Math.cos(a) * (p[0] + 0.4), p[1], T.z + Math.sin(a) * (p[0] + 0.4)));
      const rib = new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 20, 0.5, 6, false), ribs); sceneA.add(rib); }
    const glow = pointsGeo(1); glow.attributes.position.setXYZ(0, T.x, 88, T.z); glow.attributes.acol.setXYZ(0, 0.7, 0.85, 1); glow.attributes.size.setX(0, 90); glow.attributes.alpha.setX(0, 0);
    const gm = glowMat(false); const gp = new THREE.Points(glow, gm); gp.frustumCulled = false; sceneA.add(gp);
    upd.push((t, night) => { mat.emissiveIntensity = 0.1 + night * 0.85; ribs.emissiveIntensity = 0.2 + night * 0.9; glow.attributes.alpha.setX(0, night * 0.45); glow.attributes.alpha.needsUpdate = true; gm.uniforms.uScale.value = camA.userData.us || 600; });
  }
  if (AP.landmark === 'yellowSub') {
    // Liverpool's Yellow Submarine sculpture by the terminal (drawn a little over life size so it reads on camera)
    const S = AP.sub, k = S.scale || 1.6;
    const mat = new THREE.MeshLambertMaterial({ color: 0xffcc14, emissive: 0xffb000, emissiveIntensity: 0 });
    const g = new THREE.Group(); g.position.set(S.x, 0, S.z); g.rotation.y = S.rot || 0.4; g.scale.setScalar(k); sceneA.add(g);
    const hull = new THREE.Mesh(new THREE.CapsuleGeometry(2.6, 12, 8, 20), mat); hull.rotation.z = Math.PI / 2; hull.position.y = 4.2; g.add(hull);
    const tower = new THREE.Mesh(new THREE.BoxGeometry(4.2, 3.4, 2.4), mat); tower.position.set(-0.6, 7.6, 0); g.add(tower);
    const deck = new THREE.Mesh(new THREE.BoxGeometry(2.0, 1.2, 1.6), mat); deck.position.set(-0.4, 9.9, 0); g.add(deck);
    for (const dx of [-1.6, 0.9]) { const p = new THREE.Mesh(new THREE.CylinderGeometry(0.18, 0.18, 2.8, 8), mat); p.position.set(dx, 10.4, 0); g.add(p); }
    const fin = new THREE.Mesh(new THREE.BoxGeometry(1.6, 0.3, 6.2), mat); fin.position.set(-8.6, 4.2, 0); g.add(fin);
    const rud = new THREE.Mesh(new THREE.BoxGeometry(1.6, 4.6, 0.3), mat); rud.position.set(-8.6, 4.2, 0); g.add(rud);
    const prop = new THREE.Mesh(new THREE.CylinderGeometry(1.3, 1.3, 0.25, 12), new THREE.MeshLambertMaterial({ color: 0xd94a1e })); prop.rotation.z = Math.PI / 2; prop.position.set(-9.7, 4.2, 0); g.add(prop);
    const portMat = new THREE.MeshLambertMaterial({ color: 0x1d2a3a, emissive: 0xffe0a0, emissiveIntensity: 0 });
    for (let i = 0; i < 5; i++) for (const s of [1, -1]) { const p = new THREE.Mesh(new THREE.CylinderGeometry(0.55, 0.55, 0.3, 10), portMat); p.rotation.x = Math.PI / 2; p.position.set(-4 + i * 2, 4.6, s * 2.55); g.add(p); }
    const glow = pointsGeo(1); glow.attributes.position.setXYZ(0, S.x, 9 * k, S.z); glow.attributes.acol.setXYZ(0, 1, 0.8, 0.2); glow.attributes.size.setX(0, 70); glow.attributes.alpha.setX(0, 0);
    const gm = glowMat(false); const gp = new THREE.Points(glow, gm); gp.frustumCulled = false; sceneA.add(gp);
    upd.push((t, night) => { mat.emissiveIntensity = 0.08 + night * 0.55; portMat.emissiveIntensity = night * 1.2; glow.attributes.alpha.setX(0, night * 0.4); glow.attributes.alpha.needsUpdate = true; gm.uniforms.uScale.value = camA.userData.us || 600; });
  }
  return { update: (t, night) => upd.forEach(f => f(t, night)) };
})();
