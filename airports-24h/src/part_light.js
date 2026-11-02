function lightAirport(t, vm, cam, rcw, rch) {
  const m = clamp(vm, 0, 1440);
  const wx = wxAt(m);
  const sl = sunLocal(mod1440(vm)); const el = Math.asin(clamp(sl.y, -1, 1)) / D2R;
  const day = smooth(-5, 7, el), night = 1 - smooth(-7, 3, el);
  camA.position.copy(cam.p); camA.lookAt(cam.q); camA.fov = cam.fov; camA.aspect = rcw / rch; camA.updateProjectionMatrix();
  sky.position.copy(camA.position);
  const cl = wx.cloud, rn = wx.rain, mist = wx.mist;
  const zNight = new THREE.Color('#070d24'), hNight = new THREE.Color('#2a2a52').lerp(new THREE.Color('#4a3048'), 0.35);
  const zDay = new THREE.Color('#3f7fd0').lerp(new THREE.Color('#5f6a77'), cl), hDay = new THREE.Color('#a9cbe8').lerp(new THREE.Color('#9aa3ab'), cl);
  const zen = zNight.clone().lerp(zDay, day), hor = hNight.clone().lerp(hDay, day);
  const twi = Math.exp(-Math.pow((el - 0.5) / 6.0, 2)) * (1 - cl * 0.5);
  const warm = mod1440(vm) < 720 ? new THREE.Color('#f39a5e') : new THREE.Color('#f06a42');
  hor.lerp(warm, twi * 0.8); zen.lerp(new THREE.Color('#33407e'), twi * 0.45);
  hor.lerp(new THREE.Color('#b8bfc8'), mist * 0.6 * day + mist * 0.2);
  skyMat.uniforms.zen.value.copy(zen); skyMat.uniforms.hor.value.copy(hor);
  skyMat.uniforms.sunDir.value.copy(sl); skyMat.uniforms.sunCol.value.set(el < 8 ? '#ffa860' : '#fff2d8'); skyMat.uniforms.sunAmt.value = smooth(-4, 2, el) * (1 - cl * 0.8);
  skyMat.uniforms.stars.value = night * (1 - cl);
  sceneA.fog.color.copy(hor);
  sceneA.fog.near = lerp(2500, 600, mist) * (1 - rn * 0.3); sceneA.fog.far = lerp(26000, 9000, mist) * (1 - rn * 0.35);
  sunL.position.copy(sl).multiplyScalar(5000); sunL.target.position.set(0, 0, 0);
  sunL.intensity = day * (1 - cl * 0.65) * 2.4; sunL.color.set(el < 10 ? '#ffc58a' : '#fff4e2');
  hemi.intensity = 0.32 + 1.15 * day * (1 - cl * 0.2); hemi.color.copy(zen.clone().lerp(new THREE.Color('#ffffff'), 0.5)); hemi.groundColor.set(day > 0.5 ? '#5a5a48' : '#1c2030');
  groundMat.emissiveIntensity = Math.pow(night, 1.2) * 0.6;
  const us = rch / (2 * Math.tan(camA.fov * D2R / 2)); camA.userData.us = us;
  if (oceanMat) { oceanMat.color.set(day > 0.3 ? '#0e3352' : '#061524').lerp(new THREE.Color('#2a3440'), mist * 0.5); oceanMat.specular.set(el < 8 ? '#ffb070' : '#e8eef5').multiplyScalar(0.25 + 0.75 * day * (1 - cl * 0.7)); }
  LANDMARK.update(t, night);
  streetMat.uniforms.uInt.value = Math.pow(night, 1.3) * (rch > 1000 ? 1.5 : 1.1); streetMat.uniforms.uScale.value = us; streetMat.uniforms.uFog.value = sceneA.fog.far * 0.45; streetMat.uniforms.uMin.value = 1.3;
  sceneA.userData.far.material.emissiveIntensity = night * 0.6;
  for (const k2 in bMats) bMats[k2].emissiveIntensity = 0.12 + night * 0.95;
  sceneA.userData.cab.material.emissiveIntensity = 0.2 + night * 0.9;
  for (const hz of HAZE) hz.material.opacity = night * 0.55;
  bodyMatShared.emissiveIntensity = 0.30 * night; sceneA.userData.parkedTail.material.emissiveIntensity = 0.25 * night;
  ltMat.uniforms.uScale.value = us * (rch > 1000 ? 1.25 : 1); ltMat.uniforms.uFog.value = sceneA.fog.far * 0.55; ltMat.uniforms.uMin.value = rch > 1000 ? 2.2 : 1.6;
  acLt.material.uniforms.uScale.value = us; acLt.material.uniforms.uFog.value = sceneA.fog.far * 0.6; acLt.material.uniforms.uMin.value = 1.8;
  const wdir = (wx.dir + 180) * D2R; const wvx = Math.sin(wdir), wvz = -Math.cos(wdir);
  const cc = new THREE.Color('#ffffff').lerp(new THREE.Color('#6d7682'), rn).lerp(new THREE.Color('#1a2138'), night);
  CLOUDS.forEach(s => { const u = s.userData; const span = 26000; let x = u.x + wvx * vm * 9, z = u.z + wvz * vm * 9; x = ((x + span / 2) % span + span) % span - span / 2; z = ((z + span / 2) % span + span) % span - span / 2; s.position.set(x, u.y, z); s.material.opacity = clamp(cl * 1.3 - u.ph * 0.6, 0, 1) * 0.9; s.material.color.copy(cc).lerp(warm, twi * 0.5); });
  const rp = rainGeo.attributes.position; const fwd = new THREE.Vector3().subVectors(cam.q, cam.p).setY(0).normalize(); const rc0 = cam.p.clone().addScaledVector(fwd, 1200);
  for (let i = 0; i < RAIN_N; i++) {
    const s = rainSeed[i]; const x = rc0.x + (s[0] - 0.5) * 2400, z = rc0.z + (s[1] - 0.5) * 2400; const y = cam.p.y - 300 + ((s[2] * 900 - t * 2600) % 900 + 900) % 900;
    rp.setXYZ(i * 2, x + wvx * 14, y + 40, z + wvz * 14); rp.setXYZ(i * 2 + 1, x, y, z);
  }
  rp.needsUpdate = true; rainMat.opacity = rn * 0.34;
  if (windObj) { sceneA.remove(windObj); windObj.geometry.dispose(); windObj = null; }
  { const pos = [], col = []; const sp = 260 + wx.kt * 60; const wa = clamp((wx.kt - 3) / 14, 0.25, 1) * (0.45 + 0.55 * day) * 0.26 * smooth(8.8, 9.8, t) * smooth(150, 500, cam.p.y);
    if (wa > 0.002) {
      for (let i = 0; i < WS_N; i++) {
        const s = windSeed[i]; const span = 9000; const L = 260 + s[2] * 380;
        const a = (s[0] * span + t * sp) % span - span / 2; const b = (s[1] - 0.5) * span;
        const cx = -300 + wvx * a - wvz * b, cz = 200 + wvz * a + wvx * b; const y = 50 + s[3] * 260;
        const life = Math.sin(Math.PI * ((s[0] * span + t * sp) % span) / span);
        for (let j = 0; j < WS_SEG; j++) {
          const u0 = j / WS_SEG, u1 = (j + 1) / WS_SEG; const w0 = Math.sin(Math.PI * u0) * wa * life, w1 = Math.sin(Math.PI * u1) * wa * life;
          const wob = Math.sin((t * 2 + s[1] * 9 + u0 * 4)) * 10;
          pos.push(cx + wvx * L * (u0 - 0.5) - wvz * wob, y, cz + wvz * L * (u0 - 0.5) + wvx * wob, cx + wvx * L * (u1 - 0.5) - wvz * wob, y, cz + wvz * L * (u1 - 0.5) + wvx * wob);
          col.push(w0 * 0.85, w0 * 0.95, w0 * 1.1, w1 * 0.85, w1 * 0.95, w1 * 1.1);
        }
      }
      const g = new LineSegmentsGeometry(); g.setPositions(pos); g.setColors(col); windMat.resolution.set(rcw, rch); windObj = new LineSegments2(g, windMat); windObj.frustumCulled = false; sceneA.add(windObj);
    } }
  return { wx, el, night, day };
}

