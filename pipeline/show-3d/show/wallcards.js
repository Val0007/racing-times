// Catalog graphics for the studio wall, drawn on a 1600x900 canvas in the Racing Times palette
// (ink, paper, one red; team colours only as data accents). One block per catalog kind.
import { RT, drawWordmark } from './characters.js';

export const TEAM = { MCL: '#ff8000', FER: '#e8002d', RBR: '#3671c6', MER: '#27f4d2', AMR: '#229971', ALP: '#0093cc',
  WIL: '#64c4ff', RB: '#6692ff', HAA: '#b6babd', AUD: '#c8ccd0', CAD: '#c9a24a' };
const INK = '#0e0d0c';
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const easeOut = t => 1 - Math.pow(1 - clamp(t), 3);
const lerp = (a, b, t) => a + (b - a) * t;

// maxW: shrink to fit (script text varies week to week)
export function txt(g, s, x, y, font, fill, align = 'left', spacing = 0, maxW = 0) {
  g.font = font;
  if (maxW) {
    const size = parseFloat(font.match(/([\d.]+)px/)[1]);
    const w = g.measureText(s).width + spacing * s.length;
    if (w > maxW) g.font = font.replace(/[\d.]+px/, `${Math.max(12, size * maxW / w).toFixed(1)}px`);
  }
  g.fillStyle = fill; g.textAlign = align; g.textBaseline = 'alphabetic'; g.letterSpacing = spacing + 'px'; g.fillText(s, x, y); g.letterSpacing = '0px';
}
function bg(g) { g.fillStyle = INK; g.fillRect(0, 0, 1600, 900); }
function label(g, s, x, y, align = 'left') { txt(g, s, x, y, '600 30px Inter', RT.paper2, align, 10, 1300); }
function redRule(g, x, y, w = 140) { g.fillStyle = RT.red; g.fillRect(x, y, w, 6); }

export function drawCard(g, gr, t) {
  g.save(); bg(g);
  const k = gr.kind;
  if (k === 'logo') {
    drawWordmark(g, 'Racing Times', 800, 430, 230, RT.paper);
    redRule(g, 730, 520);
    txt(g, gr.sub, 800, 600, '600 32px Inter', RT.paper2, 'center', 14, 1300);
  } else if (k === 'headlines') {
    txt(g, gr.title, 120, 170, '900 84px "Playfair Display"', RT.paper, 'left', 0, 1360); redRule(g, 122, 196);
    const step = Math.min(175, 600 / gr.items.length), rh = step * 0.8, s = rh / 140;
    gr.items.forEach((it, i) => {
      const p = easeOut((t - 0.5 - i * 1.5) / 0.6); if (p <= 0) return;
      const y = 260 + i * step, x = lerp(-900, 120, p);
      g.globalAlpha = p; g.fillStyle = 'rgba(244,239,228,0.05)'; g.fillRect(x, y, 1360, rh);
      g.fillStyle = RT.red; g.fillRect(x, y, 8, rh);
      txt(g, String(i + 1).padStart(2, '0'), x + 50, y + rh * 0.68, `600 ${44 * s}px Inter`, RT.paper2);
      txt(g, it, x + 160, y + rh * 0.7, `400 ${80 * s}px "Bebas Neue"`, RT.paper, 'left', 2, 1170); g.globalAlpha = 1;
    });
  } else if (k === 'p1') {
    const tc = TEAM[gr.team] || RT.red;
    g.fillStyle = tc; g.beginPath(); g.moveTo(1290, 0); g.lineTo(1600, 0); g.lineTo(1600, 900); g.lineTo(1110, 900); g.fill();
    g.fillStyle = INK; g.globalAlpha = 0.35; g.fillRect(1100, 0, 500, 900); g.globalAlpha = 1;
    const p = easeOut(t / 0.8);
    txt(g, gr.pos, lerp(-300, 120, p), 460, '900 320px "Playfair Display"', RT.paper, 'left', 0, 900);
    txt(g, gr.name, lerp(-600, 128, easeOut((t - .25) / .8)), 600, '400 120px "Bebas Neue"', RT.paper, 'left', 4, 880);
    redRule(g, 130, 630);
    txt(g, [gr.sub, gr.stat].filter(Boolean).join('  ·  '), 130, 700, '600 32px Inter', RT.paper2, 'left', 6, 900);
  } else if (k === 'results') {
    txt(g, gr.title, 110, 140, '900 72px "Playfair Display"', RT.paper, 'left', 0, 1380);
    label(g, gr.sub, 112, 192);
    gr.rows.forEach(([pos, name, team, gap], i) => {
      const p = easeOut((t - 0.3 - i * 0.32) / 0.5); if (p <= 0) return;
      const y = 225 + i * 104, x = lerp(1700, 110, p);
      g.fillStyle = i % 2 ? 'rgba(244,239,228,0.04)' : 'rgba(244,239,228,0.08)'; g.fillRect(x, y, 1380, 90);
      g.fillStyle = TEAM[team] || RT.paper2; g.fillRect(x, y, 10, 90);
      txt(g, pos, x + 60, y + 66, '900 54px "Playfair Display"', i === 0 ? RT.paper : RT.paper2);
      txt(g, name, x + 170, y + 66, '400 66px "Bebas Neue"', RT.paper, 'left', 3, 700);
      txt(g, team, x + 900, y + 60, '600 28px Inter', RT.paper2, 'left', 6);
      txt(g, gap, x + 1340, y + 66, '400 62px "Bebas Neue"', i === 0 ? '#e0575d' : RT.paper, 'right', 2);
    });
  } else if (k === 'champions') {
    const p = easeOut(t / 0.9);
    g.globalAlpha = p; label(g, gr.sub, 800, 300, 'center');
    txt(g, gr.big, 800, 540, '900 220px "Playfair Display"', RT.paper, 'center', 0, 1440);
    g.fillStyle = TEAM[gr.team] || RT.red; g.fillRect(800 - 300 * p, 600, 600 * p, 6); g.globalAlpha = 1;
  } else if (k === 'bigword') {
    g.strokeStyle = 'rgba(244,239,228,0.05)'; g.lineWidth = 2;
    for (let i = 0; i < 30; i++) { const y = (i * 37 + t * 60) % 1000 - 50; g.beginPath(); g.moveTo(0, y); g.lineTo(1600, y - 400); g.stroke(); }
    const p = easeOut(t / 0.7);
    g.globalAlpha = p; txt(g, gr.big, 800, 500, '900 290px "Playfair Display"', RT.paper, 'center', 0, 1440);
    redRule(g, 730, 545);
    g.globalAlpha = clamp((t - 0.8) / 0.4); txt(g, gr.lines[0], 800, 640, '600 38px Inter', RT.paper, 'center', 8, 1400);
    if (gr.lines[1]) { g.globalAlpha = clamp((t - 1.4) / 0.4); txt(g, gr.lines[1], 800, 705, '600 32px Inter', RT.paper2, 'center', 8, 1400); }
    g.globalAlpha = 1;
  } else if (k === 'nextup') {
    label(g, gr.title, 800, 230, 'center');
    txt(g, gr.big, 800, 450, '900 200px "Playfair Display"', RT.paper, 'center', 0, 1460);
    redRule(g, 730, 495);
    txt(g, gr.sub, 800, 580, '400 70px "Bebas Neue"', RT.paper, 'center', 6, 1400);
    if (gr.later?.length) txt(g, 'LATER: ' + gr.later.join('  ·  '), 800, 660, '600 26px Inter', RT.paper2, 'center', 4, 1400);
  }
  g.restore();
}
