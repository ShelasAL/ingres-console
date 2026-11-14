
import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const EDGE = "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const PORT = 9350;
const OUT = process.argv[2];
const BASE = "http://127.0.0.1:8600";
const PROFILE = path.join(process.env.TEMP, "edge-ingres-console");
const W = 1600;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
fs.mkdirSync(OUT, { recursive: true });

const edge = spawn(EDGE, ["--headless=new", "--no-sandbox", "--disable-gpu", "--disable-crash-reporter",
  "--no-first-run", "--window-size=1640,1100", "--hide-scrollbars",
  "--remote-debugging-port=" + PORT, "--user-data-dir=" + PROFILE, "about:blank"], { stdio: "ignore" });

async function getJson(p) {
  for (let i = 0; i < 60; i++) {
    try { const r = await fetch("http://127.0.0.1:" + PORT + p); if (r.ok) return await r.json(); } catch (e) {}
    await sleep(500);
  }
  throw new Error("CDP unreachable");
}
const target = (await getJson("/json/list")).find((t) => t.type === "page");
const ws = new WebSocket(target.webSocketDebuggerUrl);
let id = 0; const pending = new Map();
const errors = [];
ws.onmessage = (e) => {
  const m = JSON.parse(e.data);
  if (m.method === "Runtime.exceptionThrown") {
    const d = m.params.exceptionDetails;
    errors.push(d.text + " " + (d.exception && d.exception.description ? d.exception.description : ""));
  }
  if (m.id && pending.has(m.id)) {
    const p = pending.get(m.id); pending.delete(m.id);
    m.error ? p.reject(new Error(JSON.stringify(m.error))) : p.resolve(m.result);
  }
};
await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
const send = (method, params = {}) => new Promise((resolve, reject) => {
  const mid = ++id; pending.set(mid, { resolve, reject });
  ws.send(JSON.stringify({ id: mid, method, params }));
});
const ev = async (expr) => {
  const r = await send("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true });
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.text + " " + (r.exceptionDetails.exception?.description || ""));
  return r.result ? r.result.value : undefined;
};
await send("Page.enable"); await send("Runtime.enable");
await send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: "dark" }] });
await send("Emulation.setDeviceMetricsOverride", { width: W, height: 1000, deviceScaleFactor: 1, mobile: false });
await send("Page.navigate", { url: BASE });
await sleep(5000);

async function waitText(marker, timeout = 20000) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeout) {
    const txt = await ev("document.body.innerText");
    if (txt.includes(marker)) return true;
    await sleep(400);
  }
  console.log("WARN missing text:", marker);
  return false;
}

async function shot(name) {
  const h = await ev("Math.min(Math.max(document.documentElement.scrollHeight, 1000), 4200)");
  await send("Emulation.setDeviceMetricsOverride", { width: W, height: h, deviceScaleFactor: 1, mobile: false });
  await sleep(1200);
  const s = await send("Page.captureScreenshot", { format: "png" });
  fs.writeFileSync(path.join(OUT, name), Buffer.from(s.data, "base64"));
  console.log("saved", name, h);
  await send("Emulation.setDeviceMetricsOverride", { width: W, height: 1000, deviceScaleFactor: 1, mobile: false });
  await sleep(400);
}

await waitText("National groundwater posture");
await sleep(1500);
if (errors.length) console.log("PAGE ERRORS:", JSON.stringify(errors.slice(0, 3)));
await shot("console_dashboard.png");

// Map
await ev("document.querySelector('[data-page=map]').click()");
await sleep(5000);
await shot("console_map.png");

// Copilot
await ev("document.querySelector('[data-page=copilot]').click()");
await sleep(800);
await ev("document.querySelector('.suggestion').click()");
console.log("asked copilot");
await sleep(6000);
await waitText("Fully supported", 25000);
await sleep(1500);
await shot("console_copilot.png");

// Stations
await ev("document.querySelector('[data-page=stations]').click()");
await sleep(5000);
await shot("console_stations.png");

// Explore
await ev("document.querySelector('[data-page=explore]').click()");
await sleep(3500);
await shot("console_explore.png");

// Performance
await ev("document.querySelector('[data-page=performance]').click()");
await sleep(2500);
await sleep(1200);
await shot("console_performance.png");

console.log("errors:", JSON.stringify(errors.slice(0, 5)));
ws.close(); edge.kill(); process.exit(0);