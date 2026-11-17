// Racing Times: renders content/episodes.md as a list of episode cards.
// Each "## Title" block is one episode; "Key: value" lines are its fields.

const FIELDS = ["video", "poster", "notes", "runtime"];

function parseEpisodes(md) {
  const blocks = md.split(/^## /m).slice(1);
  return blocks.map((block) => {
    const lines = block.split("\n");
    const ep = { title: lines.shift().trim(), teaser: [] };
    for (const line of lines) {
      const m = line.match(/^(\w+):\s*(.+)$/);
      if (m && FIELDS.includes(m[1].toLowerCase())) ep[m[1].toLowerCase()] = m[2].trim();
      else if (line.trim()) ep.teaser.push(line.trim());
    }
    ep.teaser = ep.teaser.join(" ");
    return ep;
  });
}

function esc(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function slug(s) {
  return s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
}

async function loadNotes(path) {
  if (!path) return "";
  try {
    const r = await fetch(path);
    if (!r.ok) throw new Error(r.status);
    let md = await r.text();
    md = md.replace(/^# .*\n+/, "");          // the card already shows the title
    const html = marked.parse(md);
    const box = document.createElement("div");
    box.innerHTML = html;
    box.querySelectorAll("a").forEach((a) => { a.target = "_blank"; a.rel = "noopener"; });
    return box.innerHTML;
  } catch (e) {
    return `<p class="muted">Notes could not be loaded.</p>`;
  }
}

function card(ep, i, notesHtml) {
  const id = slug(ep.title);
  const [num, date] = ep.title.split("·").map((s) => s.trim());
  return `
  <article class="episode" id="${id}">
    <div class="ep-head">
      <span class="ep-num">${esc(num || ep.title)}</span>
      ${date ? `<span class="ep-date">${esc(date)}</span>` : ""}
      ${ep.runtime ? `<span class="ep-run">${esc(ep.runtime)}</span>` : ""}
      ${i === 0 ? `<span class="ep-new">Latest</span>` : ""}
    </div>
    <div class="screen">
      <video controls preload="metadata" playsinline ${ep.poster ? `poster="${esc(ep.poster)}"` : ""}>
        <source src="${esc(ep.video)}" type="video/mp4">
        Your browser can't play this video. <a href="${esc(ep.video)}">Download it</a>.
      </video>
    </div>
    ${ep.teaser ? `<p class="teaser">${esc(ep.teaser)}</p>` : ""}
    <details class="notes" ${i === 0 ? "open" : ""}>
      <summary>Show notes, sources &amp; credits</summary>
      <div class="notes-scroll">${notesHtml}</div>
    </details>
  </article>`;
}

async function main() {
  const root = document.getElementById("episodes");
  try {
    const r = await fetch("content/episodes.md");
    const eps = parseEpisodes(await r.text());
    const notes = await Promise.all(eps.map((e) => loadNotes(e.notes)));
    root.innerHTML = eps.map((e, i) => card(e, i, notes[i])).join("");
    document.getElementById("ep-count").textContent = `${eps.length} episode${eps.length === 1 ? "" : "s"}`;
    if (location.hash) document.querySelector(location.hash)?.scrollIntoView();
  } catch (e) {
    root.innerHTML = `<p class="muted">Episodes could not be loaded.</p>`;
  }
}

function setupTheme() {
  const btn = document.getElementById("theme-toggle");
  const dark = () => {
    const t = document.documentElement.dataset.theme;
    return t ? t === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
  };
  btn.addEventListener("click", () => {
    const next = dark() ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem("rt-theme", next); } catch (e) {}
  });
}

setupTheme();
main();
