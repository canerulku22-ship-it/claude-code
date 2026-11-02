
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
  return { update: (t, night) => upd.forEach(f => f(t, night)) };
})();
