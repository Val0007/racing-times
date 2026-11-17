// Racing Times characters, both original designs:
//   Pixie: studio presenter, three-piece suit.
//   Byte:  paddock reporter, team-neutral bomber jacket, press pass, handheld mic.
// Clothing is painted onto the torso with canvas textures mapped in body coordinates,
// so buttons, lapels and stripes stay where a tailor would put them.
import * as THREE from 'three';

// Racing Times palette, taken from the newspaper: ink, paper, one red. Nothing else.
export const RT = { ink: '#1b1a17', ink2: '#2a2926', ink3: '#3a3834', paper: '#f4efe4', paper2: '#cfc6b3', red: '#a3141b', redD: '#7d0f15' };
// Wordmark: 'masthead' = the newspaper's blackletter; 'caps' = spaced capitals.
export const WORDMARK = { style: 'masthead' };
export function drawWordmark(g, text, cx, cy, size, color, style = WORDMARK.style) {
  g.fillStyle = color; g.textAlign = 'center'; g.textBaseline = 'middle';
  if (style === 'masthead') { g.font = `400 ${size}px "UnifrakturMaguntia"`; g.letterSpacing = '0px'; g.fillText(text, cx, cy); }
  else { g.font = `600 ${size * 0.42}px Inter`; g.letterSpacing = `${size * 0.16}px`; g.fillText(text.toUpperCase(), cx + size * 0.08, cy); g.letterSpacing = '0px'; }
}
const v3 = (x, y, z) => new THREE.Vector3(x, y, z);
const shadowed = (m, cast = true, recv = true) => { m.castShadow = cast; m.receiveShadow = recv; return m; };
function canvasTex(w, h, draw) {
  const c = document.createElement('canvas'); c.width = w; c.height = h; draw(c.getContext('2d'), w, h);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; return t;
}

// ── torso shape + body-coordinate texture mapping ───────────
// Profile [radius, y] relative to the torso origin (chest ~0.2, shoulders ~0.3, neck 0.445).
const PROF = [[0, -0.22], [0.205, -0.22], [0.212, -0.12], [0.218, -0.02], [0.228, 0.08], [0.242, 0.18], [0.25, 0.26],
  [0.24, 0.32], [0.21, 0.37], [0.15, 0.41], [0.085, 0.435], [0.06, 0.445], [0, 0.445]];
const SX = 1.1, SZ = 0.72;            // torso is an ellipse: wider than deep
function seg(y) {                     // profile index (fractional) for height y on the side surface
  for (let i = 1; i < PROF.length - 2; i++) {
    const [, y0] = PROF[i], [, y1] = PROF[i + 1];
    if (y <= y1 || i === PROF.length - 3) return i + Math.min(1, Math.max(0, (y - y0) / (y1 - y0 || 1)));
  }
}
function rAt(y) { const s = seg(y), i = Math.floor(s), f = s - i; const a = PROF[i][0], b = PROF[Math.min(i + 1, PROF.length - 1)][0]; return a + (b - a) * f; }
const vAt = y => seg(y) / (PROF.length - 1);
const phiAt = (x, y) => Math.asin(Math.max(-1, Math.min(1, x / (rAt(y) * SX))));
const uAt = (x, y) => 0.5 + phiAt(x, y) / (2 * Math.PI);   // front centre at u = 0.5 (lathe phiStart = PI)
function surf(x, y, off = 0.004) { const p = phiAt(x, y), r = rAt(y); return v3(Math.sin(p) * r * SX, y, Math.cos(p) * r * SZ + off); }

function painter(g, W, H) {
  const C = (x, y) => [uAt(x, y) * W, (1 - vAt(y)) * H];
  const sub = pts => { const o = []; pts.forEach((p, i) => { const q = pts[(i + 1) % pts.length]; for (let k = 0; k < 10; k++) o.push([p[0] + (q[0] - p[0]) * k / 10, p[1] + (q[1] - p[1]) * k / 10]); }); return o; };
  const path = pts => { g.beginPath(); sub(pts).forEach(([x, y], i) => { const [cx, cy] = C(x, y); i ? g.lineTo(cx, cy) : g.moveTo(cx, cy); }); g.closePath(); };
  return {
    C,
    poly(pts, fill) { path(pts); g.fillStyle = fill; g.fill(); },
    stroke(pts, col, w, close = false) {
      g.beginPath(); const s = close ? sub(pts) : pts.flatMap((p, i) => i ? Array.from({ length: 10 }, (_, k) => [pts[i - 1][0] + (p[0] - pts[i - 1][0]) * (k + 1) / 10, pts[i - 1][1] + (p[1] - pts[i - 1][1]) * (k + 1) / 10]) : [p]);
      s.forEach(([x, y], i) => { const [cx, cy] = C(x, y); i ? g.lineTo(cx, cy) : g.moveTo(cx, cy); });
      if (close) g.closePath(); g.strokeStyle = col; g.lineWidth = w; g.stroke();
    },
    dot(x, y, r, fill) { const [cx, cy] = C(x, y); g.beginPath(); g.arc(cx, cy, r, 0, Math.PI * 2); g.fillStyle = fill; g.fill(); },
    clip(pts) { path(pts); g.save(); g.clip(); },
    unclip() { g.restore(); },
  };
}

function cloth(g, W, H, base, stripe, every = 9, alpha = 0.22) {
  g.fillStyle = base; g.fillRect(0, 0, W, H);
  const r = (s => () => (s = (s * 16807) % 2147483647) / 2147483647)(9);
  for (let i = 0; i < W * H / 60; i++) { g.fillStyle = `rgba(${r() > .5 ? '255,255,255' : '0,0,0'},${0.03 * r()})`; g.fillRect(r() * W, r() * H, 2, 2); } // weave
  if (stripe) { g.globalAlpha = alpha; g.fillStyle = stripe; for (let x = 0; x < W; x += every) g.fillRect(x, 0, 1.2, H); g.globalAlpha = 1; }
}

// Three-piece suit: jacket with peak lapels, waistcoat with buttons, shirt, tie, pocket square.
function suitTexture(o) {
  return canvasTex(2048, 1024, (g, W, H) => {
    const P = painter(g, W, H);
    cloth(g, W, H, o.suit, o.pin, 10);
    // jacket opening (V down to the button) -> waistcoat
    const open = [[-0.12, 0.445], [0.12, 0.445], [0.0, -0.05]];
    P.clip(open); cloth(g, W, H, o.vest, o.pin, 10); P.unclip();
    // cutaway below the button shows the waistcoat points
    P.poly([[0, -0.05], [0.05, -0.2], [-0.05, -0.2]], o.vest);
    P.poly([[-0.05, -0.2], [0.05, -0.2], [0.0, -0.13]], o.suit);
    // waistcoat V -> shirt + tie
    P.poly([[-0.042, 0.445], [0.042, 0.445], [0.0, 0.25]], o.shirt);
    P.poly([[-0.013, 0.43], [0.013, 0.43], [0.009, 0.405], [-0.009, 0.405]], o.tieKnot);
    P.poly([[-0.009, 0.405], [0.009, 0.405], [0.017, 0.25], [-0.017, 0.25]], o.tie);
    P.clip([[-0.009, 0.405], [0.009, 0.405], [0.017, 0.25], [-0.017, 0.25]]);
    g.strokeStyle = o.tieStripe; g.lineWidth = 3; for (let k = -40; k < 40; k++) { const [x, y] = P.C(0, 0.3); g.beginPath(); g.moveTo(x - 200, y + k * 14 - 200); g.lineTo(x + 200, y + k * 14 + 200); g.stroke(); }
    P.unclip();
    // waistcoat edge shadow + buttons
    P.stroke([[-0.042, 0.445], [0, 0.25], [0.042, 0.445]], 'rgba(0,0,0,.5)', 3);
    for (const y of [0.21, 0.16, 0.11, 0.06, 0.01]) P.dot(0, y, 5, '#151412');
    // peak lapels (lighter, with a dark roll line and a notch)
    for (const s of [-1, 1]) {
      const lap = [[s * 0.12, 0.445], [s * 0.004, -0.045], [s * 0.045, 0.05], [s * 0.13, 0.27], [s * 0.175, 0.33], [s * 0.145, 0.345], [s * 0.16, 0.39]];
      P.poly(lap, o.lapel);
      P.stroke([[s * 0.12, 0.445], [s * 0.004, -0.045]], 'rgba(0,0,0,.6)', 5);
      P.stroke([[s * 0.004, -0.045], [s * 0.045, 0.05], [s * 0.13, 0.27], [s * 0.175, 0.33]], 'rgba(0,0,0,.35)', 2.5);
      P.stroke([[s * 0.175, 0.33], [s * 0.145, 0.345], [s * 0.16, 0.39]], 'rgba(0,0,0,.5)', 2.5);
    }
    // jacket button, breast pocket welt (character's left = +x), hip pockets
    P.dot(0, -0.05, 6, '#111');
    P.stroke([[0.12, 0.215], [0.19, 0.225]], 'rgba(0,0,0,.6)', 3);
    for (const s of [-1, 1]) P.stroke([[s * 0.09, -0.08], [s * 0.19, -0.075]], 'rgba(0,0,0,.5)', 3);
    // side shading for depth
    const sg = g.createLinearGradient(0, 0, W, 0);
    sg.addColorStop(0, 'rgba(0,0,0,.35)'); sg.addColorStop(0.3, 'rgba(0,0,0,0)'); sg.addColorStop(0.7, 'rgba(0,0,0,0)'); sg.addColorStop(1, 'rgba(0,0,0,.35)');
    g.fillStyle = sg; g.fillRect(0, 0, W, H);
  });
}

// Racing Times merch bomber: ink with a paper wordmark across the chest, one red stripe, red-tipped ribs.
function bomberTexture(o) {
  return canvasTex(2048, 1024, (g, W, H) => {
    const P = painter(g, W, H);
    cloth(g, W, H, o.jacket, null);
    const yy = y => P.C(0, y)[1];
    g.fillStyle = o.rib; g.fillRect(0, yy(-0.15), W, H - yy(-0.15));                 // hem rib
    for (let x = 0; x < W; x += 6) { g.fillStyle = 'rgba(255,255,255,.04)'; g.fillRect(x, yy(-0.15), 2, H); }
    g.fillStyle = o.accent; g.fillRect(0, yy(-0.13), W, yy(-0.14) - yy(-0.13));        // red tipping
    g.fillStyle = o.rib; g.fillRect(0, 0, W, yy(0.405));                               // collar rib
    g.fillStyle = o.accent; g.fillRect(0, yy(0.405), W, yy(0.398) - yy(0.405));
    g.fillStyle = o.accent; g.fillRect(0, yy(0.185), W, yy(0.172) - yy(0.185));        // chest stripe
    // wordmark across the chest, split by the zip
    const [cx, cy] = P.C(0, 0.255);
    drawWordmark(g, 'Racing Times', cx, cy, 64, o.print);
    P.stroke([[0, 0.43], [0, -0.22]], '#0d0c0b', 6); P.stroke([[0, 0.43], [0, -0.22]], o.print2, 1.5);   // zip
    for (const s of [-1, 1]) P.stroke([[s * 0.06, 0.43], [s * 0.012, 0.13]], o.lanyard, 9);          // lanyard
    const sg = g.createLinearGradient(0, 0, W, 0);
    sg.addColorStop(0, 'rgba(0,0,0,.35)'); sg.addColorStop(0.3, 'rgba(0,0,0,0)'); sg.addColorStop(0.7, 'rgba(0,0,0,0)'); sg.addColorStop(1, 'rgba(0,0,0,.35)');
    g.fillStyle = sg; g.fillRect(0, 0, W, H);
  });
}

// ── shared character builder ────────────────────────────────
export const VIS = { X: [1, .12, 0], A: [.92, .06, 0], B: [1, .42, .7], C: [1.02, .72, .8], D: [1.12, 1, 1], E: [.72, .7, .2], F: [.55, .5, 0], G: [1, .32, 1], H: [1, .68, .5] };

function buildCharacter(o) {
  const M = {
    skin: new THREE.MeshPhysicalMaterial({ color: o.skin, roughness: 0.55, sheen: 0.4, sheenColor: o.skinSheen }),
    hair: new THREE.MeshPhysicalMaterial({ color: o.hair, roughness: 0.5, clearcoat: 0.25, clearcoatRoughness: 0.4, sheen: 0.8, sheenColor: o.hairSheen }),
    hairIn: new THREE.MeshStandardMaterial({ color: new THREE.Color(o.hair).multiplyScalar(0.35), roughness: 0.9, side: THREE.BackSide }),
    torso: new THREE.MeshPhysicalMaterial({ map: o.torsoTex, roughness: 0.62, sheen: 0.7, sheenColor: o.sheen }),
    sleeve: new THREE.MeshPhysicalMaterial({ map: o.sleeveTex, roughness: 0.62, sheen: 0.7, sheenColor: o.sheen }),
    legs: new THREE.MeshPhysicalMaterial({ map: o.legTex, roughness: 0.65, sheen: 0.6, sheenColor: o.sheen }),
    shoes: new THREE.MeshPhysicalMaterial({ color: o.shoes, roughness: 0.25, clearcoat: 1, clearcoatRoughness: 0.1 }),
    white: new THREE.MeshPhysicalMaterial({ color: 0xf4f1ea, roughness: 0.5 }),
    eyeW: new THREE.MeshPhysicalMaterial({ color: 0xffffff, roughness: 0.1, clearcoat: 1 }),
    pupil: new THREE.MeshPhysicalMaterial({ color: o.iris, roughness: 0.05, clearcoat: 1 }),
    mouth: new THREE.MeshStandardMaterial({ color: 0x4a0f18, roughness: 0.6 }),
    lips: new THREE.MeshPhysicalMaterial({ color: o.lips, roughness: 0.35, clearcoat: 0.6 }),
    teeth: new THREE.MeshStandardMaterial({ color: 0xfbf8f2, roughness: 0.3 }),
    dark: new THREE.MeshPhysicalMaterial({ color: 0x1a1a20, metalness: 0.6, roughness: 0.3 }),
    brow: new THREE.MeshStandardMaterial({ color: o.brow, roughness: 0.7 }),
  };
  const root = new THREE.Group();

  // legs + hips (trousers), shoes
  const hips = shadowed(new THREE.Mesh(new THREE.CylinderGeometry(0.2, 0.19, 0.2, 32), M.legs)); hips.scale.z = 0.75; hips.position.y = 0.8; root.add(hips);
  for (const s of [-1, 1]) {
    const leg = shadowed(new THREE.Mesh(new THREE.CapsuleGeometry(0.075, 0.68, 6, 20), M.legs)); leg.position.set(s * 0.1, 0.45, 0); leg.scale.z = 0.9; root.add(leg);
    const shoe = shadowed(new THREE.Mesh(new THREE.CapsuleGeometry(0.05, 0.14, 6, 16), M.shoes)); shoe.rotation.x = Math.PI / 2; shoe.scale.set(1.15, 1, 0.75); shoe.position.set(s * 0.1, 0.045, 0.05); root.add(shoe);
  }

  // torso
  const torso = new THREE.Group(); torso.position.y = 1.0; root.add(torso);
  const body = shadowed(new THREE.Mesh(new THREE.LatheGeometry(PROF.map(([r, y]) => new THREE.Vector2(r, y)), 96, Math.PI, Math.PI * 2), M.torso));
  body.scale.set(SX, 1, SZ); torso.add(body);
  o.torsoExtras?.(torso, M, surf);

  // neck, collar
  const neck = shadowed(new THREE.Mesh(new THREE.CylinderGeometry(0.052, 0.06, 0.14, 20), M.skin)); neck.position.y = 1.47; root.add(neck);
  o.collar?.(root, M);

  // head
  const head = new THREE.Group(); head.position.y = 1.66; root.add(head);
  const HR = 0.165;
  const skull = shadowed(new THREE.Mesh(new THREE.SphereGeometry(HR, 64, 48), M.skin)); skull.scale.set(0.94, 1.06, 0.98); head.add(skull);
  const jaw = shadowed(new THREE.Mesh(new THREE.SphereGeometry(HR * 0.82, 48, 32), M.skin)); jaw.position.set(0, -0.055, 0.012); jaw.scale.set(o.jawW ?? 0.95, 0.85, 0.95); head.add(jaw);
  o.hairStyle(head, M, HR);
  const eyes = [], brows = [];
  for (const s of [-1, 1]) {
    const e = new THREE.Group(); e.position.set(s * 0.056, 0.014, 0.151); head.add(e);
    const w = new THREE.Mesh(new THREE.SphereGeometry(0.027, 24, 16), M.eyeW); w.scale.set(1, o.eyeH ?? 1.2, 0.55); e.add(w);
    const p = new THREE.Mesh(new THREE.SphereGeometry(0.0175, 20, 12), M.pupil); p.position.z = 0.009; p.scale.set(1, 1.15, 0.55); e.add(p);
    const hl = new THREE.Mesh(new THREE.SphereGeometry(0.0045, 8, 6), new THREE.MeshBasicMaterial({ color: 0xffffff })); hl.position.set(-0.006, 0.009, 0.0185); e.add(hl);
    eyes.push(e);
    const br = new THREE.Mesh(new THREE.CapsuleGeometry(o.browT ?? 0.006, 0.034, 4, 8), M.brow); br.rotation.z = Math.PI / 2 + s * (o.browTilt ?? 0.12); br.position.set(s * 0.058, 0.062, 0.157); br.userData = { y: 0.062, rz: br.rotation.z, side: s }; head.add(br); brows.push(br);
    if (o.blush) { const b = new THREE.Mesh(new THREE.CircleGeometry(0.022, 20), new THREE.MeshBasicMaterial({ color: 0xff8a8a, transparent: true, opacity: 0.22 })); b.position.set(s * 0.085, -0.04, 0.128); b.rotation.y = s * 0.55; head.add(b); }
    if (o.ears) { const ear = shadowed(new THREE.Mesh(new THREE.SphereGeometry(0.03, 16, 12), M.skin)); ear.scale.set(0.45, 1, 0.75); ear.position.set(s * HR * 0.93, -0.005, 0.0); head.add(ear); }
  }
  const nose = new THREE.Mesh(new THREE.SphereGeometry(0.014, 16, 12), M.skin); nose.position.set(0, -0.022, 0.158); nose.scale.set(1, 1.1, 0.9); head.add(nose);
  const mouthG = new THREE.Group(); mouthG.position.set(0, -0.077, 0.146); head.add(mouthG);
  const mouth = new THREE.Mesh(new THREE.SphereGeometry(0.03, 32, 16), M.mouth); mouth.scale.set(1, 0.2, 0.35); mouthG.add(mouth);
  const teeth = new THREE.Mesh(new THREE.BoxGeometry(0.036, 0.009, 0.01), M.teeth); teeth.position.set(0, 0.004, 0.006); mouthG.add(teeth);
  const lipU = new THREE.Mesh(new THREE.CapsuleGeometry(0.0045, 0.045, 4, 8), M.lips); lipU.rotation.z = Math.PI / 2; mouthG.add(lipU);
  const lipL = lipU.clone(); mouthG.add(lipL);
  o.headExtras?.(head, M, HR);

  // arms: sleeve, shirt cuff (optional), hand, finger
  function makeArm(side) {
    const sh = new THREE.Group(); sh.position.set(side * 0.255, 1.36, 0); root.add(sh);
    const up = shadowed(new THREE.Mesh(new THREE.CapsuleGeometry(0.06, 0.2, 6, 16), M.sleeve)); up.position.y = -0.13; sh.add(up);
    const el = new THREE.Group(); el.position.y = -0.27; sh.add(el);
    const fo = shadowed(new THREE.Mesh(new THREE.CapsuleGeometry(0.052, 0.18, 6, 16), M.sleeve)); fo.position.y = -0.11; el.add(fo);
    if (o.cuff) { const c = new THREE.Mesh(new THREE.CylinderGeometry(0.047, 0.047, 0.03, 20), o.cuff === 'shirt' ? M.white : new THREE.MeshPhysicalMaterial({ color: o.cuff, roughness: 0.7 })); c.position.y = -0.215; el.add(c); }
    const hand = shadowed(new THREE.Mesh(new THREE.SphereGeometry(0.047, 20, 14), M.skin)); hand.position.y = -0.26; hand.scale.set(0.85, 1.1, 0.6); el.add(hand);
    const finger = new THREE.Mesh(new THREE.CapsuleGeometry(0.012, 0.05, 4, 8), M.skin); finger.position.y = -0.32; finger.visible = false; el.add(finger);
    return { sh, el, hand, finger };
  }
  const armL = makeArm(-1), armR = makeArm(1);   // -1 = character's right side (faces +z)

  function setMouth(shape) {
    const [mw, mh, tv] = typeof shape === 'string' ? VIS[shape] : shape;
    mouth.scale.set(mw * 0.95, 0.06 + mh * 0.62, 0.35);
    teeth.visible = tv > 0.3 && mh > 0.25; teeth.scale.x = mw;
    lipU.position.y = 0.004 + mh * 0.011; lipL.position.y = -0.004 - mh * 0.013;
    lipU.scale.set(1, mw, 1); lipL.scale.set(1, mw * 0.92, 1);
  }
  setMouth('X');
  return { root, torso, head, eyes, brows, armL, armR, setMouth, M };
}

// ── Pixie: presenter in a three-piece suit ──────────────────
export function buildPixie() {
  const suit = { suit: '#1d1e21', vest: '#3a3b3f', pin: '#7d7f86', lapel: '#26272b', shirt: RT.paper, tie: RT.red, tieKnot: RT.redD, tieStripe: 'rgba(0,0,0,.18)' };
  const sleeveTex = canvasTex(512, 512, (g, W, H) => cloth(g, W, H, suit.suit, suit.pin, 10));
  sleeveTex.wrapS = sleeveTex.wrapT = THREE.RepeatWrapping; sleeveTex.repeat.set(2, 1);
  const c = buildCharacter({
    skin: 0xf0bf9c, skinSheen: 0xffc4a8, hair: 0x5a1426, hairSheen: 0xb04a66, iris: 0x1a1210, lips: 0xc8606a, brow: 0x3e0d1a,
    shoes: 0x0c0c0e, sheen: 0x8a857a, blush: true, cuff: 'shirt',
    torsoTex: suitTexture(suit), sleeveTex, legTex: sleeveTex,
    torsoExtras(torso, M) {
      // 3D details: waistcoat + jacket buttons, tie knot, pocket square, lapel pin
      const btn = new THREE.MeshPhysicalMaterial({ color: 0x141418, roughness: 0.3, clearcoat: 1 });
      for (const y of [0.21, 0.16, 0.11, 0.06, 0.01, -0.05]) { const b = new THREE.Mesh(new THREE.SphereGeometry(y < 0 ? 0.009 : 0.006, 12, 8), btn); b.scale.z = 0.5; b.position.copy(surf(0, y, 0.002)); torso.add(b); }
      const knot = new THREE.Mesh(new THREE.BoxGeometry(0.026, 0.028, 0.016), new THREE.MeshPhysicalMaterial({ color: RT.redD, roughness: 0.4, sheen: 1, sheenColor: 0xc04050 }));
      knot.position.copy(surf(0, 0.418, 0.006)); torso.add(knot);
      const sq = new THREE.Mesh(new THREE.ConeGeometry(0.018, 0.03, 3), new THREE.MeshPhysicalMaterial({ color: RT.paper, roughness: 0.6 }));
      sq.position.copy(surf(0.155, 0.232, 0.004)); sq.rotation.z = -0.15; torso.add(sq);
      const pin = new THREE.Mesh(new THREE.SphereGeometry(0.008, 12, 8), new THREE.MeshPhysicalMaterial({ color: RT.red, roughness: 0.3, clearcoat: 1 })); pin.position.copy(surf(-0.135, 0.3, 0.004)); torso.add(pin);
    },
    collar(root, M) {
      const col = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.066, 0.04, 24, 1, true), M.white); col.position.y = 1.44; root.add(col);
      for (const s of [-1, 1]) { const tip = new THREE.Mesh(new THREE.ConeGeometry(0.014, 0.038, 3), M.white); tip.position.set(s * 0.024, 1.43, 0.058); tip.rotation.set(0.5, 0, s * 2.6); tip.scale.z = 0.4; root.add(tip); }
    },
    hairStyle(head, M, HR) {
      const crown = shadowed(new THREE.Mesh(new THREE.SphereGeometry(HR * 1.07, 64, 32, 0, Math.PI * 2, 0, Math.PI * 0.42), M.hair)); crown.position.y = 0.01; head.add(crown);
      const bob = shadowed(new THREE.Mesh(new THREE.SphereGeometry(HR * 1.09, 64, 40, Math.PI / 2 + 1.05, Math.PI * 2 - 2.1, Math.PI * 0.18, Math.PI * 0.55), M.hair));
      bob.scale.set(1.04, 1.12, 1.02); bob.position.y = -0.01; head.add(bob);
      const inner = new THREE.Mesh(bob.geometry, M.hairIn); inner.scale.copy(bob.scale); inner.position.copy(bob.position); head.add(inner);
      const fringe = shadowed(new THREE.Mesh(new THREE.SphereGeometry(HR * 1.05, 48, 24, Math.PI / 2 - 1.15, 2.3, Math.PI * 0.18, Math.PI * 0.2), M.hair)); head.add(fringe);
    },
    headExtras(head, M, HR) {  // broadcast headset with boom mic
      const band = new THREE.Mesh(new THREE.TorusGeometry(HR * 1.13, 0.007, 8, 48, Math.PI), M.dark); band.position.y = 0.005; head.add(band);
      const cup = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.03, 0.025, 20), M.dark); cup.rotation.z = Math.PI / 2; cup.position.set(-HR * 1.13, -0.005, 0); head.add(cup);
      const boom = new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3([v3(-HR * 1.12, -0.02, 0.01), v3(-0.13, -0.09, 0.09), v3(-0.07, -0.105, 0.155)]), 20, 0.0045, 8), M.dark); head.add(boom);
      const mic = new THREE.Mesh(new THREE.SphereGeometry(0.011, 12, 8), M.dark); mic.position.set(-0.066, -0.105, 0.157); head.add(mic);
    },
  });
  // default pose: forearms resting on the desk
  c.armL.sh.rotation.set(-0.55, 0, -0.18); c.armL.el.rotation.set(-1.15, 0, 0.1);
  c.armR.sh.rotation.set(-0.55, 0, 0.18); c.armR.el.rotation.set(-1.15, 0, -0.1);
  return c;
}


// ── Byte's cap: Racing Times merch, with a little open-wheel race car on top ──
// Generic single-seater built from primitives: no team livery, no series logos.
function buildRaceCar() {
  const car = new THREE.Group();
  const red = new THREE.MeshPhysicalMaterial({ color: RT.red, roughness: 0.3, clearcoat: 1, clearcoatRoughness: 0.1 });
  const ink = new THREE.MeshPhysicalMaterial({ color: RT.ink, roughness: 0.4, clearcoat: 0.6 });
  const paper = new THREE.MeshStandardMaterial({ color: RT.paper, roughness: 0.5 });
  const tyre = new THREE.MeshStandardMaterial({ color: 0x0d0d0d, roughness: 0.85 });
  const add = (geo, mat, x, y, z, rx = 0, ry = 0, rz = 0, sx = 1, sy = 1, sz = 1) => {
    const m = new THREE.Mesh(geo, mat); m.position.set(x, y, z); m.rotation.set(rx, ry, rz); m.scale.set(sx, sy, sz); m.castShadow = true; car.add(m); return m;
  };
  // units: metres of a ~5 m car, scaled down at the end; nose points +z
  add(new THREE.CapsuleGeometry(0.32, 2.4, 8, 16), red, 0, 0.42, -0.1, Math.PI / 2, 0, 0, 1, 1, 0.75);      // monocoque
  add(new THREE.ConeGeometry(0.2, 1.3, 16), red, 0, 0.33, 1.85, Math.PI / 2, 0, 0, 1, 1, 0.6);               // nose
  add(new THREE.BoxGeometry(0.08, 0.02, 1.6), paper, 0, 0.62, 0.7);                                           // paper stripe
  for (const s of [-1, 1]) add(new THREE.BoxGeometry(0.42, 0.34, 1.5), red, s * 0.48, 0.38, -0.4, 0, s * 0.08, 0); // sidepods
  add(new THREE.BoxGeometry(1.9, 0.05, 0.42), ink, 0, 0.12, 2.35);                                            // front wing
  for (const s of [-1, 1]) add(new THREE.BoxGeometry(0.04, 0.22, 0.5), ink, s * 0.95, 0.2, 2.35);
  add(new THREE.BoxGeometry(1.05, 0.06, 0.38), ink, 0, 1.0, -2.1, -0.15);                                     // rear wing
  add(new THREE.BoxGeometry(1.05, 0.04, 0.24), red, 0, 0.88, -2.08, -0.25);
  for (const s of [-1, 1]) add(new THREE.BoxGeometry(0.04, 0.55, 0.5), ink, s * 0.53, 0.8, -2.1);
  add(new THREE.TorusGeometry(0.3, 0.04, 8, 24, Math.PI), ink, 0, 0.7, 0.35, -Math.PI / 2 + 0.25, 0, 0, 1, 1.3, 1); // halo
  add(new THREE.SphereGeometry(0.17, 16, 12), paper, 0, 0.72, 0.05);                                          // helmet
  add(new THREE.BoxGeometry(0.22, 0.06, 0.1), ink, 0, 0.74, 0.18);                                            // visor
  for (const [x, z, r, w] of [[0.8, 1.6, 0.33, 0.32], [-0.8, 1.6, 0.33, 0.32], [0.82, -1.55, 0.36, 0.42], [-0.82, -1.55, 0.36, 0.42]]) {
    add(new THREE.CylinderGeometry(r, r, w, 24), tyre, x, r, z, 0, 0, Math.PI / 2);
    add(new THREE.CylinderGeometry(r * 0.55, r * 0.55, w + 0.01, 16), ink, x, r, z, 0, 0, Math.PI / 2);
  }
  return car;
}

function buildCap(HR) {
  const cap = new THREE.Group();
  const cloth = new THREE.MeshPhysicalMaterial({ color: RT.ink, roughness: 0.75, sheen: 0.5, sheenColor: 0x55524c });
  const crown = shadowed(new THREE.Mesh(new THREE.SphereGeometry(HR * 1.1, 64, 24, 0, Math.PI * 2, 0, Math.PI * 0.43), cloth));
  crown.scale.y = 0.95; crown.position.y = 0.012; cap.add(crown);
  const band = new THREE.Mesh(new THREE.CylinderGeometry(HR * 1.1 * Math.sin(Math.PI * 0.43) + 0.001, HR * 1.1 * Math.sin(Math.PI * 0.43) + 0.001, 0.008, 64, 1, true),
    new THREE.MeshStandardMaterial({ color: RT.red, roughness: 0.6 }));
  band.position.y = 0.012 + HR * 1.1 * Math.cos(Math.PI * 0.43) * 0.95 + 0.004; cap.add(band);
  const brim = shadowed(new THREE.Mesh(new THREE.CylinderGeometry(0.115, 0.115, 0.008, 40), cloth));
  brim.scale.z = 0.72; brim.position.set(0, 0.056, 0.165); brim.rotation.x = 0.12; cap.add(brim);
  const under = new THREE.Mesh(new THREE.CylinderGeometry(0.113, 0.113, 0.002, 40), new THREE.MeshStandardMaterial({ color: RT.red, roughness: 0.7 }));
  under.scale.z = 0.72; under.position.set(0, 0.051, 0.165); under.rotation.x = 0.12; cap.add(under);
  const btn = new THREE.Mesh(new THREE.SphereGeometry(0.011, 12, 8), new THREE.MeshStandardMaterial({ color: RT.red, roughness: 0.6 }));
  btn.position.y = 0.012 + HR * 1.1 * 0.95; btn.scale.y = 0.5; cap.add(btn);
  // front panel: masthead "RT"
  const logo = new THREE.Mesh(new THREE.PlaneGeometry(0.08, 0.05), new THREE.MeshStandardMaterial({ transparent: true, roughness: 0.7,
    map: canvasTex(256, 160, (g, W, H) => drawWordmark(g, 'RT', W / 2, H / 2 + 6, 130, RT.paper)) }));
  logo.position.set(0, 0.112, 0.152); logo.rotation.x = -0.62; cap.add(logo);
  // the car, riding on the crown
  const car = buildRaceCar(); car.scale.setScalar(0.042); car.position.set(0, 0.012 + HR * 1.1 * 0.95 - 0.008, 0.015); car.rotation.x = -0.08; cap.add(car);
  return cap;
}

// ── Byte: paddock reporter ──────────────────────────────────
export function buildByte() {
  const j = { jacket: RT.ink, rib: '#121110', accent: RT.red, print: RT.paper, print2: '#8a857a', lanyard: RT.red };
  const sleeveTex = canvasTex(512, 512, (g, W, H) => cloth(g, W, H, j.jacket, null));
  const legTex = canvasTex(512, 512, (g, W, H) => cloth(g, W, H, RT.ink2, null));
  const c = buildCharacter({
    skin: 0xb97a56, skinSheen: 0xd89a76, hair: 0x18141f, hairSheen: 0x3a6a78, iris: 0x24160e, lips: 0xa65a50, brow: 0x18141f,
    shoes: RT.paper, sheen: 0x55524c, ears: true, eyeH: 1.1, browT: 0.0075, browTilt: -0.05, jawW: 1.0, cuff: RT.red,
    torsoTex: bomberTexture(j), sleeveTex, legTex,
    torsoExtras(torso) {
      // press pass on the lanyard
      const card = new THREE.Mesh(new THREE.BoxGeometry(0.07, 0.095, 0.004), new THREE.MeshPhysicalMaterial({
        map: canvasTex(256, 352, (g, W, H) => {
          g.fillStyle = RT.paper; g.fillRect(0, 0, W, H); g.fillStyle = RT.red; g.fillRect(0, 0, W, 80);
          g.fillStyle = RT.paper; g.font = '600 34px Inter'; g.letterSpacing = '10px'; g.textAlign = 'center'; g.fillText('MEDIA', W / 2 + 5, 54); g.letterSpacing = '0px';
          drawWordmark(g, 'Racing Times', W / 2, 135, 40, RT.ink);
          g.fillStyle = RT.ink; g.font = '800 54px Inter'; g.textBaseline = 'alphabetic'; g.fillText('BYTE', W / 2, 235);
          g.font = '600 22px Inter'; g.fillText('PADDOCK REPORTER', W / 2, 280);
        }), roughness: 0.3, clearcoat: 1 }));
      card.position.copy(surf(0, 0.085, 0.012)); card.rotation.x = -0.12; torso.add(card);
    },
    collar(root) { const col = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.078, 0.06, 24, 1, true), new THREE.MeshPhysicalMaterial({ color: 0x121110, roughness: 0.8 })); col.position.y = 1.43; root.add(col); },
    hairStyle(head, M, HR) {
      // short hair showing under the cap at the back and sides
      const back = shadowed(new THREE.Mesh(new THREE.SphereGeometry(HR * 1.04, 48, 24, Math.PI / 2 + 1.3, Math.PI * 2 - 2.6, Math.PI * 0.22, Math.PI * 0.3), M.hair)); head.add(back);
      head.add(buildCap(HR));
    },
    headExtras(head, M, HR) {  // earpiece with coil
      const bud = new THREE.Mesh(new THREE.SphereGeometry(0.011, 12, 8), M.dark); bud.position.set(HR * 0.97, -0.005, 0.015); head.add(bud);
      const coil = new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3([v3(HR * 0.97, -0.01, 0.01), v3(HR * 0.93, -0.08, -0.03), v3(HR * 0.7, -0.2, -0.06)]), 20, 0.0025, 6),
        new THREE.MeshPhysicalMaterial({ color: 0xdfe6ea, transparent: true, opacity: 0.7, roughness: 0.1 })); head.add(coil);
    },
  });
  // handheld mic with an RT flag (in the character's right hand = -x side)
  const flagTex = canvasTex(256, 256, (g, W, H) => {
    g.fillStyle = RT.ink; g.fillRect(0, 0, W, H); g.fillStyle = RT.red; g.fillRect(0, H - 40, W, 40);
    drawWordmark(g, 'RT', W / 2, H / 2 - 12, 150, RT.paper);
  });
  const mic = new THREE.Group();
  const handle = new THREE.Mesh(new THREE.CylinderGeometry(0.016, 0.012, 0.2, 20), c.M.dark); handle.position.y = 0.05; mic.add(handle);
  const grille = new THREE.Mesh(new THREE.SphereGeometry(0.03, 20, 14), new THREE.MeshPhysicalMaterial({ color: 0x9aa0a8, metalness: 1, roughness: 0.45 })); grille.position.y = 0.19; mic.add(grille);
  const flag = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.06, 0.06), new THREE.MeshPhysicalMaterial({ map: flagTex, roughness: 0.3, clearcoat: 1 })); flag.position.y = 0.125; mic.add(flag);
  mic.position.set(0, -0.27, 0.01); mic.rotation.x = 1.25; c.armL.el.add(mic);
  // pose: mic hand up at chest, other arm relaxed
  c.armL.sh.rotation.set(-0.35, 0, -0.12); c.armL.el.rotation.set(-1.75, 0, 0.35);
  c.armR.sh.rotation.set(0.05, 0, 0.1); c.armR.el.rotation.set(-0.2, 0, 0);
  c.mic = mic;
  return c;
}
