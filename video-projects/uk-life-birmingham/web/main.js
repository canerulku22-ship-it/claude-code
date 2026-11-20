// Entry: fonts + map data first, then build the timeline and expose seek() for the frame renderer.
await Promise.all(['400 100px "Lilita One"', '400 100px "Patrick Hand"', '800 40px "Nunito"', '900 40px "Nunito"'].map(f => document.fonts.load(f)));
const core = await import('./core.js');
const { loadUK } = await import('./ukmap.js');
await loadUK();
await import('./shots.js');
window.seek = t => core.renderAt(t);
window.getCues = () => ({ duration: core.DUR, sfx: core.SFX.slice().sort((a, b) => a.t - b.t), music: core.MUSIC.slice().sort((a, b) => a.t - b.t) });
window.READY = true;
