// The two Racing Times sets, shared by the show (show.js):
//   studio: curved full-width LED wall, long black desk with a centre display, Pixie in her three-piece suit
//   grid:   Byte on the starting grid, pit wall, grandstand crowd (blurred by depth of field)
// Palette: ink, paper, one red (RT in characters.js). No gold, no glow.
import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { BokehPass } from 'three/addons/postprocessing/BokehPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { RectAreaLightUniformsLib } from 'three/addons/lights/RectAreaLightUniformsLib.js';
import { Reflector } from 'three/addons/objects/Reflector.js';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import { buildPixie, buildByte, RT, WORDMARK, drawWordmark } from './characters.js';

export const W = 1280, H = 720;
await Promise.all(['900 80px "Playfair Display"', 'italic 700 40px "Playfair Display"', '400 40px Inter', '600 40px Inter',
  '800 40px Inter', '40px "Bebas Neue"', '40px "UnifrakturMaguntia"'].map(f => document.fonts.load(f)));

const v3 = (x, y, z) => new THREE.Vector3(x, y, z);
const shadowed = (m, cast = true, recv = true) => { m.castShadow = cast; m.receiveShadow = recv; return m; };
function rng(seed) { return () => (seed = (seed * 16807) % 2147483647) / 2147483647; }
function canvasTex(w, h, draw) {
  const c = document.createElement('canvas'); c.width = w; c.height = h; draw(c.getContext('2d'), w, h);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; return t;
}

export const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setSize(W, H); renderer.setPixelRatio(1);
renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.0;
RectAreaLightUniformsLib.init();
const pmrem = new THREE.PMREMGenerator(renderer);
const ENV = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;

function makePost(scene, camera, { bloom = 0.45, threshold = 0.9, maxblur = 0.015 } = {}) {
  const composer = new EffectComposer(renderer);
  composer.addPass(new RenderPass(scene, camera));
  const bokeh = new BokehPass(scene, camera, { focus: 5, aperture: 0.002, maxblur }); composer.addPass(bokeh);
  composer.addPass(new UnrealBloomPass(new THREE.Vector2(W, H), bloom, 0.6, threshold));
  composer.addPass(new OutputPass());
  const grade = new ShaderPass({
    uniforms: { tDiffuse: { value: null }, time: { value: 3.3 } },
    vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.); }`,
    fragmentShader: `uniform sampler2D tDiffuse; uniform float time; varying vec2 vUv;
      float h(vec2 p){ return fract(sin(dot(p, vec2(12.9898,78.233)) + time*7.13) * 43758.5453); }
      void main(){ vec2 d = vUv - 0.5; float r = dot(d,d);
        vec3 c; float ca = 0.0012 * r * 4.0;
        c.r = texture2D(tDiffuse, vUv + d*ca).r; c.g = texture2D(tDiffuse, vUv).g; c.b = texture2D(tDiffuse, vUv - d*ca).b;
        c = (c - 0.5) * 1.06 + 0.5; c *= mix(1.0, smoothstep(0.9, 0.15, r*1.6), 0.45);
        c += (h(vUv*vec2(1280.,720.)) - 0.5) * 0.03; gl_FragColor = vec4(c, 1.0); }`,
  });
  composer.addPass(grade);
  return { composer, bokeh };
}

// ═════════════════════════ STUDIO ═════════════════════════
const studio = new THREE.Scene();
studio.background = new THREE.Color(0x020205);
studio.environment = ENV; studio.environmentIntensity = 0.16;
const studioCam = new THREE.PerspectiveCamera(32, W / H, 0.05, 120);
const PX = -1.4;                       // presenter x (left third, the wall's headline sits right)

// ── full-width curved LED wall behind the presenter ─────────
const WALL = { R: 16, W: 14.5, H: 4.7, y0: 0.15, z: -4.3 };
const wallCanvas = document.createElement('canvas'); wallCanvas.width = 3584; wallCanvas.height = Math.round(3584 * WALL.H / WALL.W);
const wallTex = new THREE.CanvasTexture(wallCanvas); wallTex.colorSpace = THREE.SRGBColorSpace; wallTex.anisotropy = 8;
wallTex.wrapS = THREE.RepeatWrapping; wallTex.repeat.x = -1; wallTex.offset.x = 1;   // seen from inside the cylinder
const L = WALL.W / WALL.R;
const wallMesh = new THREE.Mesh(new THREE.CylinderGeometry(WALL.R, WALL.R, WALL.H, 128, 1, true, Math.PI - L / 2, L),
  new THREE.MeshBasicMaterial({ map: wallTex, side: THREE.BackSide, toneMapped: false, color: new THREE.Color(0.92, 0.92, 0.92) }));
wallMesh.position.set(0, WALL.y0 + WALL.H / 2, WALL.z + WALL.R); studio.add(wallMesh);
const wallLight = new THREE.RectAreaLight(0xffffff, 0.9, WALL.W, WALL.H);
wallLight.position.set(0, WALL.y0 + WALL.H / 2, WALL.z + 0.2); wallLight.lookAt(0, WALL.y0 + WALL.H / 2, 10); studio.add(wallLight);

function wrapLines(g, text, maxW) {
  const words = text.split(' '), lines = []; let line = '';
  for (const w of words) { const t = line ? line + ' ' + w : w; if (g.measureText(t).width > maxW && line) { lines.push(line); line = w; } else line = t; }
  if (line) lines.push(line); return lines;
}
// Wall layout: brand field on the left (behind Pixie), photo across the rest,
// kicker + headline lower right, photo credit always visible.
export function paintWallPhoto(photo, { focusX = 0.5, focusY = 0.55, zoom = 1, panX = 0 } = {}) {
  const g = wallCanvas.getContext('2d'), Wc = wallCanvas.width, Hc = wallCanvas.height;
  const p = photo, img = photo.img;
  g.fillStyle = '#0e0d0c'; g.fillRect(0, 0, Wc, Hc);
  const x0 = Wc * 0.27, pw = Wc - x0;
  const s = Math.max(pw / img.width, Hc / img.height) * zoom, dw = img.width * s, dh = img.height * s;
  g.save(); g.beginPath(); g.rect(x0, 0, pw, Hc); g.clip();
  g.drawImage(img, x0 + (pw - dw) * focusX + panX * pw, (Hc - dh) * focusY, dw, dh);
  g.restore();
  // blend the photo into the brand field; darken top-right for the headline block
  let gr = g.createLinearGradient(x0 - 2, 0, x0 + Wc * 0.16, 0); gr.addColorStop(0, '#0e0d0c'); gr.addColorStop(1, 'rgba(14,13,12,0)'); g.fillStyle = gr; g.fillRect(x0 - 2, 0, Wc * 0.16 + 2, Hc);
  gr = g.createLinearGradient(0, 0, 0, Hc * 0.62); gr.addColorStop(0, 'rgba(3,3,6,.86)'); gr.addColorStop(0.7, 'rgba(3,3,6,.45)'); gr.addColorStop(1, 'rgba(3,3,6,0)'); g.fillStyle = gr; g.fillRect(Wc * 0.4, 0, Wc * 0.6, Hc * 0.62);
  gr = g.createLinearGradient(0, Hc * 0.75, 0, Hc); gr.addColorStop(0, 'rgba(3,3,6,0)'); gr.addColorStop(1, 'rgba(3,3,6,.6)'); g.fillStyle = gr; g.fillRect(x0, Hc * 0.75, pw, Hc * 0.25);
  // headline block (u 0.47..0.84: inside the wide shot, clear of Pixie)
  const hx = Wc * 0.47, maxW = Wc * 0.37, ky = Hc * 0.1;
  g.font = '600 40px Inter'; g.letterSpacing = '10px';
  const tag = p.series || ''; const tw = tag ? g.measureText(tag).width + 46 : 0;
  g.fillStyle = RT.red; if (tag) g.fillRect(hx, ky, tw, 66); else g.fillRect(hx, ky + 14, 10, 40);
  g.fillStyle = RT.paper; g.textBaseline = 'middle'; if (tag) g.fillText(tag, hx + 20, ky + 35);
  g.fillStyle = RT.paper2; g.fillText((p.kicker || '').toUpperCase(), hx + tw + 28, ky + 35);
  g.letterSpacing = '0px';
  g.font = '900 104px "Playfair Display"'; g.fillStyle = RT.paper; g.textBaseline = 'alphabetic';
  g.shadowColor = 'rgba(0,0,0,.6)'; g.shadowBlur = 24;
  let lines = wrapLines(g, p.headline, maxW); if (lines.length > 3) { lines = lines.slice(0, 3); lines[2] = lines[2].replace(/\s*\S*$/, '') + '…'; }
  lines.forEach((l, i) => g.fillText(l, hx, ky + 200 + i * 118));
  g.shadowBlur = 0;
  g.fillStyle = RT.red; g.fillRect(hx, ky + 200 + lines.length * 118 - 50, 180, 6);
  g.font = '600 30px Inter'; g.letterSpacing = '6px'; g.fillStyle = 'rgba(244,239,228,.75)'; g.textAlign = 'right';
  g.fillText(`PHOTO: ${p.credit.toUpperCase()}`, Wc * 0.84, Hc - 70); g.textAlign = 'left'; g.letterSpacing = '0px';
  // LED pixel pitch, barely visible
  g.fillStyle = 'rgba(0,0,0,.10)'; for (let y = 0; y < Hc; y += 6) g.fillRect(0, y, Wc, 1);
  wallTex.needsUpdate = true;
  // tint the wall's light with the photo's average colour
  const sm = document.createElement('canvas'); sm.width = 8; sm.height = 4; const sg = sm.getContext('2d'); sg.drawImage(wallCanvas, 0, 0, 8, 4);
  const d = sg.getImageData(0, 0, 8, 4).data; let r = 0, gg = 0, b = 0; for (let i = 0; i < d.length; i += 4) { r += d[i]; gg += d[i + 1]; b += d[i + 2]; }
  const n = d.length / 4, m = Math.max(r, gg, b) / n || 1; wallLight.color.setRGB(r / n / m, gg / n / m, b / n / m);
}

// ── floor: mirror under a glossy black coat (reflects the wall) ─
const mirror = new Reflector(new THREE.CircleGeometry(30, 64), { textureWidth: W, textureHeight: H, color: 0x6a6a6a });
mirror.rotation.x = -Math.PI / 2; studio.add(mirror);
const floorCoat = shadowed(new THREE.Mesh(new THREE.CircleGeometry(30, 64), new THREE.MeshPhysicalMaterial({ color: 0x050507, roughness: 0.35, clearcoat: 1, clearcoatRoughness: 0.2, transparent: true, opacity: 0.72 })), false, true);
floorCoat.rotation.x = -Math.PI / 2; floorCoat.position.y = 0.003; studio.add(floorCoat);
// ── news desk: long, low, ink black; paper edge line, one red pinstripe, wordmark ──
const DESK = { x: PX + 0.35, w: 5.0, h: 1.0, z0: 0.24, d: 0.56 };
const inkBody = new THREE.MeshPhysicalMaterial({ color: 0x141311, roughness: 0.55, clearcoat: 0.35, clearcoatRoughness: 0.4 });
const inkTop = new THREE.MeshStandardMaterial({ color: 0x1d1c19, roughness: 0.8, envMapIntensity: 0.1 });
const paperMat = new THREE.MeshStandardMaterial({ color: RT.paper, roughness: 0.6 });
const redMat = new THREE.MeshStandardMaterial({ color: RT.red, roughness: 0.5 });
const desk = new THREE.Group(); desk.position.set(DESK.x, 0, DESK.z0 + DESK.d / 2); studio.add(desk);
{
  const body = shadowed(new THREE.Mesh(new RoundedBoxGeometry(DESK.w, DESK.h - 0.05, DESK.d, 4, 0.03), inkBody)); body.position.y = (DESK.h - 0.05) / 2; desk.add(body);
  const top = shadowed(new THREE.Mesh(new RoundedBoxGeometry(DESK.w + 0.16, 0.05, DESK.d + 0.16, 3, 0.02), inkTop)); top.position.set(0, DESK.h - 0.025, 0.04); desk.add(top);
  const edge = new THREE.Mesh(new THREE.BoxGeometry(DESK.w + 0.14, 0.008, 0.004), paperMat); edge.position.set(0, DESK.h - 0.025, DESK.d / 2 + 0.122); desk.add(edge);
  const pin = new THREE.Mesh(new THREE.BoxGeometry(DESK.w - 0.06, 0.012, 0.004), redMat); pin.position.set(0, 0.14, DESK.d / 2 + 0.002); desk.add(pin);
  const plinth = new THREE.Mesh(new THREE.BoxGeometry(DESK.w - 0.1, 0.06, DESK.d - 0.1), new THREE.MeshStandardMaterial({ color: 0x050505 })); plinth.position.y = 0.03; desk.add(plinth);
}
// Desk display: an LED panel in the middle of the desk front that cycles through
// the show title, the location strap and what's coming next. Items come from the script.
const DISPLAY = { w: 1.9, h: 0.44 };
const dispCanvas = document.createElement('canvas'); dispCanvas.width = 1900; dispCanvas.height = 440;
const dispTex = new THREE.CanvasTexture(dispCanvas); dispTex.colorSpace = THREE.SRGBColorSpace; dispTex.anisotropy = 8;
{
  const bezel = new THREE.Mesh(new RoundedBoxGeometry(DISPLAY.w + 0.06, DISPLAY.h + 0.06, 0.03, 3, 0.012), new THREE.MeshPhysicalMaterial({ color: 0x070707, roughness: 0.2, clearcoat: 1 }));
  bezel.position.set(0, 0.56, DESK.d / 2 + 0.012); desk.add(bezel);
  const screen = new THREE.Mesh(new THREE.PlaneGeometry(DISPLAY.w, DISPLAY.h), new THREE.MeshBasicMaterial({ map: dispTex, toneMapped: false, color: new THREE.Color(0.82, 0.82, 0.82) }));
  screen.position.set(0, 0.56, DESK.d / 2 + 0.0285); desk.add(screen);
  var deskScreen = screen;
}
function fitFont(g, text, font, size, maxW) {
  g.font = font.replace('SIZE', size); const w = g.measureText(text).width;
  if (w > maxW) g.font = font.replace('SIZE', Math.floor(size * maxW / w));
}
// item: {kind: 'title'} | {kind: 'live', text} | {kind: 'next', items: [headline, ...]}
// p (0..1) = how far the item has slid in; the previous item slides out above it.
function drawDisplayItem(g, W, H, item, ep) {
  g.textAlign = 'center'; g.textBaseline = 'middle';
  if (item.kind === 'title') {
    drawWordmark(g, 'Racing Times', W / 2, H * 0.43, 190, RT.paper, 'masthead');
    g.font = '600 30px Inter'; g.letterSpacing = '12px'; g.fillStyle = RT.paper2; g.fillText(ep, W / 2 + 6, H * 0.82); g.letterSpacing = '0px';
  } else if (item.kind === 'live') {
    g.font = '600 64px Inter'; g.letterSpacing = '18px';
    const label = item.text.toUpperCase(), w = g.measureText(label).width;
    const x0 = W / 2 - w / 2 - 60;
    g.fillStyle = RT.red; g.beginPath(); g.arc(x0, H / 2, 18, 0, 7); g.fill();
    g.fillStyle = RT.paper; g.textAlign = 'left'; g.fillText(label, x0 + 50, H / 2 + 2); g.letterSpacing = '0px';
  } else if (item.kind === 'next') {
    g.font = '600 30px Inter'; g.letterSpacing = '12px'; g.fillStyle = RT.red; g.fillText('NEXT IN THE SHOW', W / 2 + 6, H * 0.2); g.letterSpacing = '0px';
    const lines = item.items.slice(0, 2);
    lines.forEach((l, i) => {
      fitFont(g, l, '900 SIZEpx "Playfair Display"', lines.length > 1 ? 76 : 104, W - 160);
      g.fillStyle = i ? RT.paper2 : RT.paper; g.fillText(l, W / 2, lines.length > 1 ? H * (0.48 + i * 0.29) : H * 0.6);
    });
  }
}
export function paintDisplay(items, t = 0, ep = '', hold = 6) {
  const g = dispCanvas.getContext('2d'), Wd = dispCanvas.width, Hd = dispCanvas.height;
  g.fillStyle = '#0b0b0a'; g.fillRect(0, 0, Wd, Hd);
  const n = items.length, k = Math.floor(t / hold) % n, u = (t % hold) / 0.6;          // 0.6 s slide between items
  if (u < 1 && t >= hold) {
    const e = 1 - Math.pow(1 - u, 3);
    g.save(); g.translate(0, -Hd * e); drawDisplayItem(g, Wd, Hd, items[(k - 1 + n) % n], ep); g.restore();
    g.save(); g.translate(0, Hd * (1 - e)); drawDisplayItem(g, Wd, Hd, items[k], ep); g.restore();
  } else drawDisplayItem(g, Wd, Hd, items[k], ep);
  g.fillStyle = RT.red; g.fillRect(0, Hd - 8, Wd, 8);                                       // red baseline
  g.fillStyle = 'rgba(0,0,0,.22)'; for (let y = 0; y < Hd; y += 4) g.fillRect(0, y, Wd, 1);  // LED rows
  dispTex.needsUpdate = true;
}
const pixie = buildPixie(); pixie.root.position.set(PX, 0, 0); studio.add(pixie.root);
pixie.head.rotation.set(0.04, 0.12, 0.02);

// ── studio lights ───────────────────────────────────────────
studio.add(new THREE.HemisphereLight(0x3a3834, 0x020202, 0.18));
function spot(col, int, pos, tgt, angle = 0.26, pen = 0.7, shadow = false) {
  const s = new THREE.SpotLight(col, int, 0, angle, pen, 1.6); s.position.copy(pos); s.target.position.copy(tgt);
  if (shadow) { s.castShadow = true; s.shadow.mapSize.set(2048, 2048); s.shadow.bias = -0.00015; s.shadow.normalBias = 0.02; s.shadow.radius = 4; }
  studio.add(s, s.target); return s;
}
spot(0xfff3e8, 36, v3(-4.5, 5.4, 5.6), v3(PX + 0.2, 1.4, 0), 0.24, 0.7, true);   // key
spot(0xf4efe4, 8, v3(3.5, 3, 6.5), v3(PX, 1.4, 0), 0.32, 0.9);                    // fill
spot(0xeef0f4, 22, v3(PX - 2.4, 4.4, -3.0), v3(PX, 1.5, 0), 0.22, 0.6);           // rim L
spot(0xfff4e6, 20, v3(PX + 2.6, 4.2, -2.6), v3(PX, 1.5, 0), 0.22, 0.6);           // rim R
const studioPost = makePost(studio, studioCam, { bloom: 0.15, threshold: 0.98 });

// ═════════════════════════ GRID ═════════════════════════
const grid = new THREE.Scene();
grid.background = canvasTex(16, 512, (g, w, h) => {
  const gr = g.createLinearGradient(0, 0, 0, h); gr.addColorStop(0, '#5f86b8'); gr.addColorStop(0.55, '#a9c0d6'); gr.addColorStop(1, '#f2d8b0');
  g.fillStyle = gr; g.fillRect(0, 0, w, h);
});
grid.environment = ENV; grid.environmentIntensity = 0.35;
grid.fog = new THREE.Fog(0xd3dbe2, 18, 140);
const gridCam = new THREE.PerspectiveCamera(35, W / H, 0.05, 400);

// asphalt with grid-slot markings
const asphalt = canvasTex(1024, 1024, (g, w, h) => {
  g.fillStyle = '#4a4c50'; g.fillRect(0, 0, w, h); const r = rng(11);
  for (let i = 0; i < 90000; i++) { const c = 50 + r() * 60 | 0; g.fillStyle = `rgba(${c},${c},${c + 4},.5)`; g.fillRect(r() * w, r() * h, 1.5, 1.5); }
  for (let i = 0; i < 40; i++) { g.fillStyle = 'rgba(20,20,22,.10)'; g.beginPath(); g.ellipse(r() * w, r() * h, 40 + r() * 120, 10 + r() * 30, r() * 3, 0, 7); g.fill(); }
});
asphalt.wrapS = asphalt.wrapT = THREE.RepeatWrapping; asphalt.repeat.set(40, 40);
const ground = shadowed(new THREE.Mesh(new THREE.PlaneGeometry(400, 400), new THREE.MeshStandardMaterial({ map: asphalt, roughness: 0.9 })), false, true);
ground.rotation.x = -Math.PI / 2; grid.add(ground);
const paint = new THREE.MeshStandardMaterial({ color: 0xf2f2ee, roughness: 0.7 });
const flat = (w, d, x, z) => { const m = shadowed(new THREE.Mesh(new THREE.PlaneGeometry(w, d), paint), false, true); m.rotation.x = -Math.PI / 2; m.position.set(x, 0.004, z); grid.add(m); };
// track runs along x; Byte stands between the two columns of grid slots
for (let k = -6; k <= 6; k++) {
  for (const [zc, off] of [[-2.6, 0], [2.6, 4]]) {
    const x = k * 8 + off;
    flat(0.12, 2.1, x, zc);                       // slot line across the track
    flat(0.7, 0.12, x - 0.35, zc - 1.0); flat(0.7, 0.12, x - 0.35, zc + 1.0);  // legs pointing back
  }
}
flat(200, 0.25, 0, -7.2); flat(200, 0.25, 0, 7.2);  // track edges
for (let i = -60; i < 60; i++) { const m = new THREE.Mesh(new THREE.PlaneGeometry(2, 0.6), new THREE.MeshStandardMaterial({ color: i % 2 ? 0xa3141b : 0xf2f2ee, roughness: 0.6 })); m.rotation.x = -Math.PI / 2; m.position.set(i * 2, 0.005, -7.65); grid.add(m); }
// slot numbers on the asphalt
for (let k = -2; k <= 2; k++) for (const [zc, off, base] of [[-2.6, 0, 1], [2.6, 4, 2]]) {
  const n = (2 - k) * 2 + base, x = k * 8 + off;
  const t = canvasTex(256, 256, (g) => { g.fillStyle = '#f2f2ee'; g.font = '800 200px Inter'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(String(n), 128, 140); });
  const m = new THREE.Mesh(new THREE.PlaneGeometry(1.0, 1.0), new THREE.MeshStandardMaterial({ map: t, transparent: true, roughness: 0.7 }));
  m.rotation.x = -Math.PI / 2; m.rotation.z = Math.PI / 2; m.position.set(x + 0.9, 0.005, zc); grid.add(m);
}
// pit wall + catch fence
const concrete = new THREE.MeshStandardMaterial({ color: 0xd9d6cf, roughness: 0.85 });
const wallBox = shadowed(new THREE.Mesh(new THREE.BoxGeometry(200, 1.1, 0.5), concrete)); wallBox.position.set(0, 0.55, -8.6); grid.add(wallBox);
const boards = canvasTex(2048, 128, (g, w, h) => {
  for (let i = 0; i < 8; i++) { g.fillStyle = i % 2 ? RT.red : RT.ink; g.fillRect(i * w / 8, 0, w / 8, h); drawWordmark(g, 'Racing Times', i * w / 8 + w / 16, h / 2 + 4, 62, RT.paper); }
});
boards.wrapS = THREE.RepeatWrapping; boards.repeat.x = 6;
const boardMesh = new THREE.Mesh(new THREE.PlaneGeometry(200, 0.75), new THREE.MeshStandardMaterial({ map: boards, roughness: 0.5 })); boardMesh.position.set(0, 0.55, -8.34); grid.add(boardMesh);
const fenceTex = canvasTex(64, 64, (g, w, h) => { g.strokeStyle = 'rgba(60,60,64,.9)'; g.lineWidth = 2; g.beginPath(); g.moveTo(0, 0); g.lineTo(w, h); g.moveTo(w, 0); g.lineTo(0, h); g.stroke(); });
fenceTex.wrapS = fenceTex.wrapT = THREE.RepeatWrapping; fenceTex.repeat.set(1600, 32);
const fence = new THREE.Mesh(new THREE.PlaneGeometry(200, 4), new THREE.MeshStandardMaterial({ map: fenceTex, transparent: true, alphaTest: 0.2, side: THREE.DoubleSide })); fence.position.set(0, 3.1, -8.7); grid.add(fence);
for (let x = -100; x <= 100; x += 5) { const p = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.05, 5.2, 8), concrete); p.position.set(x, 2.6, -8.75); grid.add(p); }

// grandstand with a crowd (instanced), roof
const stand = new THREE.MeshStandardMaterial({ color: 0x8b9099, roughness: 0.8 });
const ROWS = 22;
for (let r = 0; r < ROWS; r++) { const s = shadowed(new THREE.Mesh(new THREE.BoxGeometry(160, 0.5, 0.95), stand)); s.position.set(0, 1.6 + r * 0.55, -15 - r * 0.95); grid.add(s); }
const back = new THREE.Mesh(new THREE.BoxGeometry(160, 14, 0.5), stand); back.position.set(0, 7.5, -15 - ROWS * 0.95 - 0.3); grid.add(back);
const roof = shadowed(new THREE.Mesh(new THREE.BoxGeometry(160, 0.4, 26), new THREE.MeshStandardMaterial({ color: 0xe9ecef, roughness: 0.6 }))); roof.position.set(0, 17.5, -25); roof.rotation.x = -0.08; grid.add(roof);
for (let x = -75; x <= 75; x += 15) { const c = new THREE.Mesh(new THREE.CylinderGeometry(0.25, 0.25, 16, 10), concrete); c.position.set(x, 8, -14.5); grid.add(c); }
{
  const PAL = [0xc8742e, 0xa83a3a, 0x3f5f8f, 0x4f9a8f, 0x3f7a62, 0xe8e3d8, 0x1b1a17, 0xc9b25a, 0x6f95b5, 0xa3141b, 0x2a2926, 0xd9d4c8, 0x8a8478];
  const SKINS = [0xf1c9a5, 0xe0ac86, 0xc68a62, 0x9c6845, 0x6e4a32];
  const r = rng(77), per = Math.floor(150 / 0.62), count = ROWS * per;
  const bodies = new THREE.InstancedMesh(new THREE.CapsuleGeometry(0.2, 0.35, 4, 8), new THREE.MeshStandardMaterial({ roughness: 0.8 }), count);
  const heads = new THREE.InstancedMesh(new THREE.SphereGeometry(0.12, 10, 8), new THREE.MeshStandardMaterial({ roughness: 0.7 }), count);
  const m = new THREE.Matrix4(), q = new THREE.Quaternion(), s = new THREE.Vector3(1, 1, 1), c = new THREE.Color();
  let i = 0;
  for (let row = 0; row < ROWS; row++) for (let k = 0; k < per; k++) {
    const x = -75 + k * 0.62 + (r() - 0.5) * 0.2, y = 1.85 + row * 0.55 + 0.3 + r() * 0.12, z = -15 - row * 0.95 + 0.1;
    const standUp = r() < 0.35 ? 0.25 : 0;
    m.compose(v3(x, y + standUp, z), q, s); bodies.setMatrixAt(i, m); bodies.setColorAt(i, c.setHex(PAL[r() * PAL.length | 0]));
    m.compose(v3(x, y + standUp + 0.42, z), q, s); heads.setMatrixAt(i, m); heads.setColorAt(i, c.setHex(r() < 0.25 ? PAL[r() * PAL.length | 0] : SKINS[r() * SKINS.length | 0]));
    i++;
  }
  grid.add(bodies, heads);
  // waving flags
  const flags = new THREE.InstancedMesh(new THREE.PlaneGeometry(0.9, 0.55), new THREE.MeshStandardMaterial({ side: THREE.DoubleSide, roughness: 0.7 }), 160);
  for (let f = 0; f < 160; f++) {
    const row = r() * ROWS | 0; m.compose(v3(-75 + r() * 150, 3.0 + row * 0.55, -15 - row * 0.95), q.setFromEuler(new THREE.Euler(0, (r() - 0.5) * 0.8, (r() - 0.5) * 0.5)), s);
    flags.setMatrixAt(f, m); flags.setColorAt(f, c.setHex(PAL[r() * PAL.length | 0]));
  }
  grid.add(flags);
}
// start gantry down the straight
{
  const steel = new THREE.MeshStandardMaterial({ color: 0x2a2c33, metalness: 0.6, roughness: 0.4 });
  for (const z of [-7.8, 7.8]) { const p = shadowed(new THREE.Mesh(new THREE.BoxGeometry(0.5, 7, 0.5), steel)); p.position.set(-34, 3.5, z); grid.add(p); }
  const beam = shadowed(new THREE.Mesh(new THREE.BoxGeometry(0.8, 1.2, 16), steel)); beam.position.set(-34, 7, 0); grid.add(beam);
  const lamp = new THREE.MeshBasicMaterial({ color: new THREE.Color(1, 0.1, 0.1).multiplyScalar(3), toneMapped: false });
  for (let k = 0; k < 5; k++) { const l = new THREE.Mesh(new THREE.CircleGeometry(0.18, 20), lamp); l.position.set(-33.55, 7, -2 + k); l.rotation.y = Math.PI / 2; grid.add(l); }
}
// late-afternoon sun from behind-left (rim light), sky fill, warm bounce from the front
const sun = new THREE.DirectionalLight(0xffe0b0, 3.2); sun.position.set(-14, 16, -18); sun.target.position.set(0, 1, 0);
sun.castShadow = true; sun.shadow.mapSize.set(2048, 2048); Object.assign(sun.shadow.camera, { left: -8, right: 8, top: 8, bottom: -8, near: 1, far: 60 }); sun.shadow.bias = -0.0002; sun.shadow.normalBias = 0.03;
grid.add(sun, sun.target);
grid.add(new THREE.HemisphereLight(0xbcd2ec, 0x5a5550, 1.1));
const bounce = new THREE.SpotLight(0xfff0e0, 9, 0, 0.35, 0.9, 1.4); bounce.position.set(2.5, 2.5, 6); bounce.target.position.set(0, 1.4, 0); grid.add(bounce, bounce.target);

const byte = buildByte(); grid.add(byte.root);
byte.root.rotation.y = 0.08; byte.head.rotation.set(0.03, -0.05, -0.03); byte.setMouth('X');
const gridPost = makePost(grid, gridCam, { bloom: 0.25, threshold: 0.95, maxblur: 0.03 });

// ═════════════════════════ WALL: cards and brand ═════════════════════════
import { drawCard } from './wallcards.js';
const cardCanvas = document.createElement('canvas'); cardCanvas.width = 1600; cardCanvas.height = 900;
// Card region on the wall: right of Pixie, 80% of the wall height. The 'full' shot frames it.
export const CARD = { x0: 0.505, w: 0.461, top: 0.1, h: 0.8 };
function wallBase(g, Wc, Hc) {
  g.fillStyle = '#0e0d0c'; g.fillRect(0, 0, Wc, Hc);
  const gr = g.createRadialGradient(Wc * 0.25, Hc * 0.5, 50, Wc * 0.25, Hc * 0.5, Wc * 0.3);
  gr.addColorStop(0, 'rgba(244,239,228,0.05)'); gr.addColorStop(1, 'rgba(0,0,0,0)'); g.fillStyle = gr; g.fillRect(0, 0, Wc, Hc);
}
function ledRows(g, Wc, Hc) { g.fillStyle = 'rgba(0,0,0,.10)'; for (let y = 0; y < Hc; y += 6) g.fillRect(0, y, Wc, 1); }
export function paintWallCard(graphic, t) {
  const g = wallCanvas.getContext('2d'), Wc = wallCanvas.width, Hc = wallCanvas.height;
  wallBase(g, Wc, Hc);
  drawCard(cardCanvas.getContext('2d'), graphic, t);
  g.drawImage(cardCanvas, Wc * CARD.x0, Hc * CARD.top, Wc * CARD.w, Hc * CARD.h);
  ledRows(g, Wc, Hc); wallTex.needsUpdate = true; wallLight.color.setRGB(0.9, 0.9, 0.9);
}
export function paintWallBrand(t) {
  const g = wallCanvas.getContext('2d'), Wc = wallCanvas.width, Hc = wallCanvas.height;
  wallBase(g, Wc, Hc);
  // intro / credits: the page overlay carries the wordmark, so the wall stays quiet (one red line)
  g.fillStyle = RT.red; g.fillRect(Wc * 0.5 - 160, Hc * 0.86, 320 * Math.min(1, t / 1.5), 6);
  ledRows(g, Wc, Hc); wallTex.needsUpdate = true; wallLight.color.setRGB(0.9, 0.9, 0.9);
}

export const studioSet = { scene: studio, camera: studioCam, post: studioPost, pixie, desk, deskScreen: () => deskScreen, PX, WALL };
export const gridSet = { scene: grid, camera: gridCam, post: gridPost, byte };
export { v3 };
