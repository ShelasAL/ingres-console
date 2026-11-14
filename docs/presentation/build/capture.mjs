
import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const EDGE = "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const PORT = 9340;
const OUT_DIR = process.argv[2];
const BASE = "http://localhost:8501";
const PROFILE = path.join(process.env.TEMP, "edge-ingres-capture");
const WIDTH = 1654;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
fs.mkdirSync(OUT_DIR, { recursive: true });

const edge = spawn(EDGE, [
  "--headless=new", "--no-sandbox", "--disable-gpu", "--disable-crash-reporter",
  "--no-first-run", "--window-size=1680,1200", "--hide-scrollbars",
  "--remote-debugging-port=" + PORT,
  "--user-data-dir=" + PROFILE,
  "about:blank",
], { stdio: "ignore" });

async function getJson(p) {
  for (let i = 0; i < 60; i++) {
    try { const r = await fetch("http://127.0.0.1:" + PORT + p); if (r.ok) return await r.json(); } catch (e) {}
    await sleep(500);
  }
  throw new Error("CDP unreachable");
}
const version = await getJson("/json/version");
console.log("Browser:", version.Browser);
const target = (await getJson("/json/list")).find((t) => t.type === "page");
const ws = new WebSocket(target.webSocketDebuggerUrl);
let id = 0;
const pending = new Map();
ws.onmessage = (evt) => {
  const m = JSON.parse(evt.data);
  if (m.id && pending.has(m.id)) {
    const p = pending.get(m.id);
    pending.delete(m.id);
    m.error ? p.reject(new Error(JSON.stringify(m.error))) : p.resolve(m.result);
  }
};
await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
const send = (method, params = {}) => new Promise((resolve, reject) => {
  const mid = ++id;
  pending.set(mid, { resolve, reject });
  ws.send(JSON.stringify({ id: mid, method, params }));
});
const ev = async (expression) => {
  const r = await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.text + " :: " + (r.exceptionDetails.exception ? r.exceptionDetails.exception.description : ""));
  return r.result ? r.result.value : undefined;
};
const bodyText = () => ev("(() => { const m = document.querySelector('[data-testid=\"stMainBlockContainer\"]') || document.querySelector('[data-testid=\"stMain\"]'); return m ? m.innerText : document.body.innerText; })()");

await send("Page.enable");
await send("Runtime.enable");
await send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: "light" }] });
await send("Emulation.setDeviceMetricsOverride", { width: WIDTH, height: 1100, deviceScaleFactor: 1, mobile: false });

async function waitReady(marker, timeout) {
  timeout = timeout || 45000;
  const t0 = Date.now();
  while (Date.now() - t0 < timeout) {
    try {
      const ok = await ev("(() => { const sk = document.querySelectorAll('[data-testid=\"stSkeleton\"]').length; const main = document.querySelector('[data-testid=\"stMainBlockContainer\"]') || document.querySelector('[data-testid=\"stMain\"]'); const mt = main ? main.innerText : document.body.innerText; const busy = mt.includes('Analyzing inquiry') || mt.includes('Running...'); return sk === 0 && !busy && mt.length > 80; })()");
      if (ok) {
        if (!marker) return true;
        if ((await bodyText()).includes(marker)) return true;
      }
    } catch (e) {}
    await sleep(600);
  }
  console.log("WARN waitReady timeout for", marker);
  return false;
}

async function goto(url, marker) {
  await send("Emulation.setDeviceMetricsOverride", { width: WIDTH, height: 1100, deviceScaleFactor: 1, mobile: false });
  await send("Page.navigate", { url });
  await sleep(4000);
  await waitReady(marker, 45000);
  await sleep(2500);
}

async function fullshot(name) {
  const h = await ev("(() => { const m = document.querySelector('[data-testid=\"stMainBlockContainer\"]') || document.querySelector('[data-testid=\"stMain\"]'); if (!m) return 1100; const r = m.getBoundingClientRect(); return Math.ceil(Math.max(m.scrollHeight, r.height)); })()");
  const height = Math.min(Math.max(h, 1100), 5200);
  await send("Emulation.setDeviceMetricsOverride", { width: WIDTH, height, deviceScaleFactor: 1, mobile: false });
  await sleep(1800);
  const shot = await send("Page.captureScreenshot", { format: "png" });
  const file = path.join(OUT_DIR, name);
  fs.writeFileSync(file, Buffer.from(shot.data, "base64"));
  console.log("saved", file, fs.statSync(file).size, "height", height);
  await send("Emulation.setDeviceMetricsOverride", { width: WIDTH, height: 1100, deviceScaleFactor: 1, mobile: false });
}

async function clickButtonContains(label) {
  const expr = "(() => { const b = Array.from(document.querySelectorAll('button')).find(x => (x.innerText || '').includes(" + JSON.stringify(label) + ")); if (b) { b.click(); return true; } return false; })()";
  return ev(expr);
}
async function clickTab(label) {
  const expr = "(() => { const t = Array.from(document.querySelectorAll('button[role=\"tab\"]')).find(x => (x.innerText || '').includes(" + JSON.stringify(label) + ")); if (t) { t.click(); return true; } return false; })()";
  return ev(expr);
}
async function openExpander(label) {
  const expr = "(() => { const s = Array.from(document.querySelectorAll('summary')).find(x => (x.innerText || '').includes(" + JSON.stringify(label) + ")); if (s) { s.click(); return true; } return false; })()";
  return ev(expr);
}

await goto(BASE, "National Groundwater Intelligence Platform");
await fullshot("01_dashboard.png");

await goto(BASE + "/Groundwater_Copilot", "Groundwater AI Copilot");
console.log("click conceptual sample:", await clickButtonContains("What is a monitoring well"));
await sleep(4000);
await waitReady("Answer", 60000);
await sleep(3500);
await fullshot("02_copilot_answer.png");
console.log("open evidence:", await openExpander("Scientific Evidence"));
await sleep(2000);
await fullshot("03_copilot_evidence.png");

// Fresh session: fluoride data query (chart + citations + executed SQL)
await goto(BASE + "/Groundwater_Copilot", "Groundwater AI Copilot");
console.log("click fluoride sample:", await clickButtonContains("Nalgonda fluoride status"));
await sleep(4000);
await waitReady("Answer", 60000);
await sleep(4000);
await fullshot("03b_copilot_fluoride.png");
console.log("open evidence 2:", await openExpander("Scientific Evidence"));
await sleep(2000);
await fullshot("03c_copilot_fluoride_evidence.png");

await goto(BASE + "/Station_Dossier", "Station & Well Dossier");
await fullshot("04_dossier_overview.png");
console.log("tab quality:", await clickTab("Water Quality"));
await sleep(2500);
await fullshot("05_dossier_quality.png");

await goto(BASE + "/Data_Explorer", "National Groundwater Data Catalog");
await fullshot("06_data_explorer.png");

await goto(BASE + "/Performance_Report", "Model Performance");
await fullshot("07_performance.png");

await goto(BASE + "/NWIC_Live_Sync", "NWIC");
await sleep(2000);
await fullshot("08_nwic_sync.png");

await goto(BASE, "National Groundwater Intelligence Platform");
console.log("open provider config:", await openExpander("Model & Provider Config"));
await sleep(1500);
const rect = await ev("(() => { const el = document.querySelector('[data-testid=\"stSidebar\"]'); const r = el.getBoundingClientRect(); return JSON.stringify({x:r.x,y:r.y,w:r.width,h:r.height}); })()");
const rc = JSON.parse(rect);
const h2 = await ev("document.querySelector('[data-testid=\"stSidebar\"]').scrollHeight");
const clipH = Math.min(Math.max(h2, rc.h), 3200);
const shot2 = await send("Page.captureScreenshot", { format: "png", clip: { x: rc.x, y: rc.y, width: rc.w, height: clipH, scale: 1 }, captureBeyondViewport: true });
fs.writeFileSync(path.join(OUT_DIR, "09_sidebar_settings.png"), Buffer.from(shot2.data, "base64"));
console.log("saved sidebar", clipH);

ws.close();
edge.kill();
process.exit(0);