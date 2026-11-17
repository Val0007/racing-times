// Racing Times 3D show. Deterministic: window.renderAt(t) draws the frame at time t.
//   /show-3d/show/index.html?episode=/episodes/2026-11-16&timeline=build/preview_timeline.json
//   (no params: the pilot in show/data/)
// Timing (sentences, mouth cues) comes from the timeline; content (graphics, shots, speakers)
// from the script, matched by segment id. Each line is played on its speaker's set:
// Pixie in the studio, Byte on the grid. A 'full' shot always frames the studio wall.
import * as THREE from 'three';
import { renderer, W, H, studioSet, gridSet, paintWallPhoto, paintWallCard, paintWallBrand, paintDisplay, CARD, v3 } from './sets.js';
import { VIS } from './characters.js';

document.body.prepend(renderer.domElement);
const q = new URLSearchParams(location.search);
const EPI = q.get('episode');                                   // e.g. /episodes/2026-11-16
const base = EPI ? EPI.replace(/\/$/, '') + '/' : 'data/';
const getJSON = (u) => fetch(u).then(r => { if (!r.ok) throw new Error(`${u}: ${r.status}`); return r.json(); });
const [TL, SCRIPT, CATALOG] = await Promise.all([
  getJSON(base + (q.get('timeline') || 'timeline.json')),
  getJSON(base + (q.get('script') || (EPI ? 'script.json' : 'pilot.json'))),
  getJSON('/show-catalog/catalog.json').catch(() => ({ show: { city: 'Stockholm' } })),
]);
// approved photos only
const PHOTOS = {};
if (EPI) {
  const list = await getJSON(base + 'photos/photos.json').catch(() => []);
  const load = (src, tries = 3) => new Promise(ok => {          // retry: a dropped request must not silently lose a photo
    const img = new Image();
    img.onload = () => ok(img);
    img.onerror = () => tries > 1 ? setTimeout(() => load(src, tries - 1).then(ok), 300) : ok(null);
    img.src = src + (tries < 3 ? `?retry=${tries}` : '');
  });
  await Promise.all(list.filter(p => p.status === 'approved').map(async p => {
    const img = await load(base + 'photos/' + p.file);
    if (img) PHOTOS[`${p.story}#${p.n || 1}`] = { img, credit: p.credit };
    else console.error(`photo failed to load: ${p.file}`);
  }));
}

// ── helpers ─────────────────────────────────────────────────
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const ease = t => { t = clamp(t); return t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; };
const easeOut = t => 1 - Math.pow(1 - clamp(t), 3);
const lerp = (a, b, t) => a + (b - a) * t;
const lerpV = (a, b, t) => a.clone().lerp(b, t);
function rng(seed) { return () => (seed = (seed * 16807) % 2147483647) / 2147483647; }
function bsearch(arr, x) { let lo = 0, hi = arr.length - 1, ans = -1; while (lo <= hi) { const m = (lo + hi) >> 1; if (arr[m] <= x) { ans = m; lo = m + 1; } else hi = m - 1; } return ans; }

// ── script + timeline ───────────────────────────────────────
const CONTENT_KEYS = ['graphic', 'graphic_b', 'graphic_b_at', 'shots', 'point', 'lower_third', 'lower_third_at', 'speaker'];
const scriptSegs = Object.fromEntries(SCRIPT.segments.map(s => [s.id, s]));
const segs = TL.segments.map(seg => {
  const sc = scriptSegs[seg.id]; if (!sc) return seg;
  const m = { ...seg }; CONTENT_KEYS.forEach(k => delete m[k]); CONTENT_KEYS.forEach(k => { if (k in sc) m[k] = sc[k]; });
  m.sentences = seg.sentences.map((s, i) => ({ ...s, speaker: s.speaker || sc.sentences?.[i]?.speaker || sc.speaker || 'pixie',
    delivery: s.delivery || sc.sentences?.[i]?.delivery || 'neutral' }));
  return m;
});
const bounds = [TL.intro[1], ...segs.slice(1).map(s => s.start), TL.outro[0]];
const mouthStarts = TL.mouth.map(m => m[0]);
const EP = String(SCRIPT.episode).padStart(2, '0');
const EP_LINE = `EPISODE ${EP}  ·  ${SCRIPT.date_display}`;
const CITY = CATALOG.show?.city || 'Stockholm';
function normalize(g) {
  g = { ...g, kind: g.kind === 'gen4' ? 'bigword' : g.kind };
  if (g.kind === 'logo') g.sub ??= `EPISODE ${EP}`;
  if (g.kind === 'headlines') g.title ??= 'THIS WEEK';
  if (g.kind === 'p1') g.pos ??= 'P1';
  if (g.kind === 'results') g.sub ??= `TOP ${g.rows.length} - CLASSIFICATION`;
  if (g.kind === 'nextup') { g.title ??= 'NEXT RACE'; g.later ??= []; }
  return g;
}
const at = (s, f) => s.start + (s.end - s.start) * f;
const segAt = t => segs.find(s => s.start <= t && t < s.end + 0.55);
function shotOf(seg, t) {
  let idx = 0; seg.shots.forEach(([f], i) => { if (t >= at(seg, f)) idx = i; });
  const start = at(seg, seg.shots[idx][0]);
  const end = idx + 1 < seg.shots.length ? at(seg, seg.shots[idx + 1][0]) : seg.end + 0.55;
  return { name: seg.shots[idx][1], idx, u: (t - start) / (end - start) };
}
function graphicOf(seg, t) {
  if (seg.graphic_b && t >= at(seg, seg.graphic_b_at)) return [normalize(seg.graphic_b), t - at(seg, seg.graphic_b_at)];
  return [normalize(seg.graphic), t - seg.start];
}
function sentenceAt(seg, t) {
  let cur = null;
  for (const s of seg.sentences) if (s.start - 0.05 <= t && t <= s.end + 0.15) cur = s;
  if (cur) return cur;
  for (const s of seg.sentences) if (s.start <= t) cur = s;   // between sentences: the last one started
  return cur || seg.sentences[0];
}
function mouthAt(t) {
  const i = bsearch(mouthStarts, t); if (i < 0) return 'X';
  const [, e, v] = TL.mouth[i]; return t < e ? v : 'X';
}
const mouthShape = t => { const a = VIS[mouthAt(t)], b = VIS[mouthAt(t - 0.045)]; return a.map((x, k) => x * 0.65 + b[k] * 0.35); };

// desk display: script's own items, or title / live / the first two photo or headline titles
const NEXT = SCRIPT.segments.flatMap(s => [s.graphic, s.graphic_b]).filter(g => g && g.kind === 'photo').map(g => g.title)
  .concat(SCRIPT.segments.filter(s => s.graphic?.kind === 'headlines').flatMap(s => s.graphic.items));
const DESK_ITEMS = SCRIPT.desk_display || [{ kind: 'title' }, { kind: 'live', text: `Live from ${CITY}` }, { kind: 'next', items: NEXT.slice(1, 3) }]
  .filter(it => it.kind !== 'next' || it.items.length);

// ── wall content ────────────────────────────────────────────
let wallKey = '';
function paintWall(g, gt, t) {
  const pk = `${g.story}#${g.n || 1}`;
  if (g.kind === 'photo' && PHOTOS[pk]) {
    // slow push-in and drift so the wall never sits still (Ken Burns)
    const u = Math.min(1, gt / 14), p = PHOTOS[pk], dir = (g.n || 1) % 2 ? 1 : -1;
    paintWallPhoto({ img: p.img, credit: p.credit, headline: g.title, kicker: g.kicker || '', series: '' },
                   { zoom: 1 + 0.08 * u, panX: dir * 0.03 * (u - 0.5) });
    wallKey = '';
    return 'photo';
  }
  const card = g.kind === 'photo' ? { kind: 'bigword', big: (g.kicker || 'NEWS').split(' ')[0], lines: [g.title] } : g;   // photo missing: plain card
  paintWallCard(card, gt); wallKey = '';
  return 'card';
}

// ── cameras ─────────────────────────────────────────────────
const { PX, WALL } = studioSet;
const handheld = (t, a) => v3(Math.sin(t * 1.3) * a + Math.sin(t * 2.9) * a * .4, Math.sin(t * 1.7 + 1) * a * .7, 0);
const headOf = c => c.head.getWorldPosition(new THREE.Vector3());
function setCam(set, pos, look, focusOn, aperture, fov) {
  const cam = set.camera; cam.position.copy(pos); cam.fov = fov; cam.updateProjectionMatrix(); cam.lookAt(look);
  set.post.bokeh.uniforms.focus.value = cam.position.distanceTo(focusOn); set.post.bokeh.uniforms.aperture.value = aperture;
}
const STUDIO_WIDES = [
  // both wides keep Pixie (x -1.4) and the whole wall card (x 0..6.8) in frame
  u => [lerpV(v3(1.0, 2.35, 6.9), v3(0.8, 2.25, 6.5), ease(u)), v3(0.75, 1.65, -1)],
  u => [lerpV(v3(-0.2, 2.35, 6.9), v3(0.0, 2.2, 6.5), ease(u)), v3(0.95, 1.65, -1)],
];
function cardTarget() {   // centre of the card region on the curved wall
  const x = (CARD.x0 + CARD.w / 2 - 0.5) * WALL.W, y = WALL.y0 + WALL.H * (1 - CARD.top - CARD.h / 2);
  return v3(x, y, WALL.z + WALL.R - Math.sqrt(WALL.R ** 2 - x * x));
}
function direct(t, seg, si, sh, speaker, wallKind) {
  if (sh.name === 'full') {
    if (wallKind === 'photo') {
      const pos = lerpV(v3(2.3, 3.0, 0.9), v3(2.3, 3.0, 0.5), ease(sh.u)); const look = v3(2.3, 3.0, -4.3);
      setCam(studioSet, pos, look, look, 0, 36);
    } else {
      const c = cardTarget(), pos = c.clone().add(v3(-0.05, 0, lerp(6.1, 5.8, ease(sh.u))));
      setCam(studioSet, pos, c, c, 0, 36);
    }
    return studioSet;
  }
  if (speaker === 'byte') {
    const hb = headOf(gridSet.byte);
    if (sh.name === 'wide') { const pos = lerpV(v3(0.9, 1.45, 4.3), v3(0.7, 1.45, 4.0), ease(sh.u)).add(handheld(t, 0.015)); setCam(gridSet, pos, v3(-0.15, 1.15, 0), hb, 0.02, 35); }
    else { const pos = lerpV(v3(0.45, 1.55, 2.3), v3(0.35, 1.58, 2.0), ease(sh.u)).add(handheld(t, 0.01)); setCam(gridSet, pos, v3(0, 1.45, 0), hb, 0.02, 30); }
    return gridSet;
  }
  const hp = headOf(studioSet.pixie);
  if (sh.name === 'wide') {
    const [pos, look] = STUDIO_WIDES[(si + sh.idx) % 2](sh.u); pos.add(handheld(t, 0.01)); setCam(studioSet, pos, look, hp, 0, 36);
  } else {
    const side = (si + sh.idx) % 2 ? -1 : 1;
    const pos = lerpV(v3(PX + 0.55 * side, 1.62, 2.6), v3(PX + 0.42 * side, 1.64, 2.15), easeOut(sh.u)).add(handheld(t, 0.006));
    setCam(studioSet, pos, hp.clone().add(v3(0, -0.12, 0)), hp, 0, 30);
  }
  return studioSet;
}

// ── character animation ─────────────────────────────────────
const blinks = []; { const r = rng(7); let t = 1; while (t < TL.duration + 5) { blinks.push(t); t += 2.2 + r() * 2.8; } }
// Delivery shapes the face as well as the voice: energy (nods, head motion), brows, head tilt.
const LOOK = {
  neutral: { e: 1.0, brow: 0, tilt: 0 },     warm: { e: 0.8, brow: 0.002, tilt: 0.04 },
  excited: { e: 2.0, brow: 0.008, tilt: 0 }, serious: { e: 0.45, brow: -0.004, tilt: 0 },
  deadpan: { e: 0.35, brow: -0.002, tilt: 0 }, question: { e: 1.1, brow: 0.006, tilt: 0.09 },
  aside: { e: 0.9, brow: 0.003, tilt: -0.06 },
};
function animate(c, t, talking, cam, energy, gesture, delivery = 'neutral') {
  const L = LOOK[delivery] || LOOK.neutral, k = energy * (talking ? L.e : 0.7);
  const shape = talking ? mouthShape(t) : VIS.X;
  c.setMouth(shape);
  const mh = shape[1], moving = mh > 0.3 ? 1 : 0;
  const to = cam.position.clone().sub(c.head.getWorldPosition(new THREE.Vector3()));
  c.head.rotation.y = clamp(Math.atan2(to.x, to.z), -0.5, 0.5) * 0.55 + Math.sin(t * 0.6) * 0.04 * k;
  c.head.rotation.x = clamp(-Math.atan2(to.y, Math.hypot(to.x, to.z)) * 0.4, -0.15, 0.2) + Math.sin(t * 6.3) * 0.028 * moving * k + Math.sin(t * 0.7) * 0.015;
  c.head.rotation.z = Math.sin(t * 0.9) * 0.025 * k + (talking ? L.tilt : 0);
  c.torso.scale.y = 1 + Math.sin(t * 1.6) * 0.008;
  const bi = bsearch(blinks, t), blink = bi >= 0 && t - blinks[bi] < 0.12;
  c.eyes.forEach(e => { e.scale.y = blink ? 0.08 : 1; });           // both eyes blink together
  const raise = (talking ? L.brow : 0) + (talking && mh > 0.85 ? 0.003 : 0);
  c.brows.forEach(b => { b.position.y = b.userData.y + raise; b.rotation.z = b.userData.rz - b.userData.side * (talking && L.brow < 0 ? 0.15 : 0); });
  if (gesture !== undefined) {   // Pixie: an open-hand gesture when she introduces a graphic
    c.armR.sh.rotation.set(lerp(-0.55, -0.9, gesture), lerp(0, -0.25, gesture), lerp(0.18, 0.55, gesture));
    c.armR.el.rotation.set(lerp(-1.15, -1.0, gesture), 0, -0.1);
  }
}
function animateByte(t, talking, cam, delivery) {
  animate(gridSet.byte, t, talking, cam, 1.8, undefined, delivery);
  const b = gridSet.byte;
  b.root.rotation.z = Math.sin(t * 2.1) * 0.012 * (talking ? 1.5 : 0.6);
  b.root.position.y = Math.abs(Math.sin(t * 4.2)) * 0.006 * (talking ? 1 : 0);
  b.armR.sh.rotation.set(0.05 + Math.sin(t * 2.6) * 0.08 * (talking ? 1 : 0.3), 0, 0.1 + Math.sin(t * 1.9) * 0.05);
}

// ── overlays ────────────────────────────────────────────────
const $ = id => document.getElementById(id);
$('bugR').textContent = EP_LINE;
$('title').querySelector('.sub').textContent = EP_LINE;
$('credits').innerHTML = `<div class="logo">Racing Times</div><div class="rule"></div><div class="h">STORIES SUMMARISED FROM REPORTING BY</div><div class="n">${SCRIPT.credits.join('  ·  ')}</div><div class="f">Read the originals: links in the description</div>`;
function overlays(t, mode, seg, shot, sentence) {
  const inSeg = mode === 'seg';
  $('bugL').style.opacity = $('bugR').style.opacity = inSeg && shot !== 'full' ? 1 : 0;
  $('bugL').querySelector('i').style.opacity = Math.floor(t * 1.4) % 2 ? 0.25 : 1;
  const ti = $('title');
  ti.style.opacity = mode === 'intro' ? clamp((t - 1.2) / 0.6) * clamp((TL.intro[1] - t) / 0.35) : 0;
  ti.style.transform = `translateY(${lerp(24, 0, easeOut((t - 1.2) / 1.2))}px)`;
  const cu = t - TL.outro[0], cr = $('credits');
  cr.style.opacity = mode === 'outro' ? clamp((cu - 0.6) / 0.6) : 0;
  cr.style.transform = `translateY(${lerp(16, -8, clamp(cu / 6))}px)`;
  const lo = $('lower'); let show = 0, a = '', b = '';
  if (inSeg && seg.lower_third && shot !== 'full') {
    const t0 = at(seg, seg.lower_third_at || 0);
    if (t >= t0 && t < t0 + 5.2) { show = Math.min(easeOut((t - t0) / 0.5), clamp((t0 + 5.2 - t) / 0.4)); a = seg.lower_third.title; b = seg.lower_third.sub; }
  }
  lo.style.opacity = show; lo.style.clipPath = `inset(0 ${100 - show * 100}% 0 0)`;
  lo.querySelector('.t').textContent = a; lo.querySelector('.s').textContent = b;
  const sb = $('subs').firstElementChild;
  const line = inSeg && sentence && sentence.start - 0.05 <= t && t <= sentence.end + 0.15 ? sentence.text : '';
  sb.textContent = line; sb.style.opacity = line ? 1 : 0;
  sb.classList.toggle('byte', !!line && sentence.speaker === 'byte');
  const dt = Math.min(...bounds.map(x => Math.abs(t - x)));
  $('dip').style.opacity = clamp(1 - dt / 0.18) * 0.9;     // quick dip to ink at every segment change
}

// ── main entry ──────────────────────────────────────────────
window.renderAt = (t) => {
  let mode = 'seg';
  if (t < TL.intro[1]) mode = 'intro'; else if (t >= TL.outro[0]) mode = 'outro';
  let set = studioSet, seg = null, sh = { name: mode }, sentence = null;
  if (mode === 'seg') {
    seg = segAt(t) || segs[segs.length - 1];
    const si = segs.indexOf(seg); sh = shotOf(seg, t); sentence = sentenceAt(seg, t);
    const [g, gt] = graphicOf(seg, t);
    const wallKind = paintWall(g, gt, t);
    set = direct(t, seg, si, sh, sentence.speaker, wallKind);
  } else {
    paintWallBrand(mode === 'intro' ? t : t - TL.outro[0]); wallKey = '';
    const u = mode === 'intro' ? t / TL.intro[1] : (t - TL.outro[0]) / (TL.outro[1] - TL.outro[0]);
    const [wpos, wlook] = STUDIO_WIDES[0](0);
    const pos = mode === 'intro' ? lerpV(v3(0.2, 5.5, 13.5), wpos, ease(u)) : lerpV(wpos, v3(0.2, 5.0, 13), ease(u));
    const look = mode === 'intro' ? lerpV(v3(0.5, 2.6, -4), wlook, ease(u)) : lerpV(wlook, v3(0.5, 2.6, -4), ease(u));
    setCam(studioSet, pos, look, headOf(studioSet.pixie), 0, mode === 'intro' ? lerp(42, 36, ease(u)) : 36);
  }
  const speaking = sentence && sentence.start - 0.05 <= t && t <= sentence.end + 0.1 ? sentence.speaker : null;
  if (set === studioSet) {
    let gesture = 0;
    if (seg && seg.point) { const lt = t - seg.start; gesture = lt < 1.9 ? easeOut(lt / 0.45) : clamp(1 - (lt - 1.9) / 0.45); }
    animate(studioSet.pixie, t, speaking === 'pixie', studioSet.camera, 1, gesture, sentence?.delivery);
    paintDisplay(DESK_ITEMS, t, EP_LINE);
  } else animateByte(t, speaking === 'byte', gridSet.camera, sentence?.delivery);
  set.post.composer.render();
  overlays(t, mode, seg, sh.name, sentence);
  return mode === 'seg' ? `${set === gridSet ? 'grid' : 'studio'}:${sh.name}` : mode;
};
window.DURATION = TL.duration;
window.ready = true;
