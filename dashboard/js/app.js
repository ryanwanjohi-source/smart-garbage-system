// Dashboard logic (proposal §3.3.3.4). Talks to the Flask API.
// The API is served from the same origin, so relative URLs just work.
const API = "/api";

function fillClass(p) {
  if (p >= 90) return "crit";
  if (p >= 70) return "warn";
  return "";
}

async function loadBins() {
  const res = await fetch(`${API}/bins`);
  const bins = await res.json();
  document.getElementById("binRows").innerHTML = bins.map(b => `
    <tr>
      <td><code>${b.code}</code></td>
      <td>${b.location}</td>
      <td>${b.fill_pct == null ? "—" : `
        <div class="fillbar ${fillClass(b.fill_pct)}">
          <div style="width:${b.fill_pct}%"></div>
        </div><small>${b.fill_pct.toFixed(1)}%</small>`}
      </td>
      <td>${b.mass_kg == null ? "—" : b.mass_kg.toFixed(2)}</td>
      <td><small>${b.last_seen ? new Date(b.last_seen).toLocaleString() : "—"}</small></td>
    </tr>`).join("") || `<tr><td colspan="5" class="text-center">no bins</td></tr>`;
  // keep the command box's bin picker in sync
  document.getElementById("binList").innerHTML =
    bins.map(b => `<option value="${b.code}">`).join("");
}

async function loadAlerts() {
  const res = await fetch(`${API}/alerts?threshold=80`);
  const alerts = await res.json();
  const el = document.getElementById("alertRows");
  el.innerHTML = alerts.length ? alerts.map(a => `
    <div class="alert alert-danger py-2 mb-2">
      <strong>${a.code}</strong> — ${a.fill_pct.toFixed(0)}% full
      <br><small>${a.location} · ${new Date(a.at).toLocaleTimeString()}</small>
    </div>`).join("")
    : `<small class="text-muted">No bins above 80% — all clear.</small>`;
}

async function optimize() {
  const t = document.getElementById("threshold").value || 70;
  const out = document.getElementById("routeOut");
  out.innerHTML = "optimizing…";
  const res = await fetch(`${API}/routes/optimize?threshold=${t}`, { method: "POST" });
  if (!res.ok) { out.innerHTML = `<div class="alert alert-warning">No bins above ${t}%.</div>`; return; }
  const r = await res.json();
  const names = {};
  (await (await fetch(`${API}/bins`)).json()).forEach(b => names[b.id] = b.code);
  out.innerHTML = `
    <div class="alert alert-success">Route #${r.route_id} — ${r.distance_km} km</div>
    <ol>${r.stops.map(s => `<li>${names[s] || ("Bin #" + s)}</li>`).join("")}</ol>`;
}

async function sendCmd(category) {
  const code = document.getElementById("cmdBin").value.trim();
  const out = document.getElementById("cmdOut");
  if (!code) { out.innerHTML = `<div class="alert alert-warning py-2">Enter a bin code first.</div>`; return; }
  out.innerHTML = "sending…";
  const res = await fetch(`${API}/bins/${encodeURIComponent(code)}/command`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ category })
  });
  const body = await res.json();
  out.innerHTML = res.ok
    ? `<div class="alert alert-success py-2">Sent <code>${body.command}</code> → <code>${body.topic}</code></div>`
    : `<div class="alert alert-danger py-2">${body.error || "failed"}</div>`;
}

setInterval(() => {
  document.getElementById("clock").textContent = new Date().toLocaleString();
}, 1000);

loadBins();
loadAlerts();
setInterval(loadBins, 10000);
setInterval(loadAlerts, 15000);
