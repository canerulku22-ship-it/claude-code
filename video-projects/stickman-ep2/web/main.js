// Entry: load fonts first (canvas panels and glyph textures need them), then build the shots.
await Promise.all(['900 100px "Inter Display"', '800 40px Inter', '600 40px Inter', '900 40px Inter'].map(f => document.fonts.load(f)));
const ENGINE = await import('./engine.js'); const { renderAt } = ENGINE; window.ENGINE = ENGINE;
const { drawCaptions, DUR, SFX, MUSIC } = await import('./lib.js');
await import('./shots.js');
const bar = document.getElementById('bar');
window.seek = t => { renderAt(t); drawCaptions(t); bar.style.width = (Math.min(1, t / DUR) * 100).toFixed(2) + '%'; };
window.getCues = () => ({ duration: DUR, sfx: SFX.slice().sort((a, b) => a.t - b.t), music: MUSIC.slice().sort((a, b) => a.t - b.t) });
window.READY = true;
