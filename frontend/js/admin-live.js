/**
 * Super Admin live KPI + real-time event panel.
 *
 * Hooks into the new enterprise API:
 *   GET /api/admin/dashboard/stats   (every 30s)
 *   GET /api/tickets/sla-dashboard   (every 60s)
 *   GET /api/network/health-map      (every 60s)
 *   WS  /api/agent/ws/<id>           (real-time call/ticket/network events)
 */

(function () {
  const TOKEN_KEY = "dh_admin_token";

  function authHeaders() {
    const t = localStorage.getItem(TOKEN_KEY);
    return t ? { Authorization: `Bearer ${t}` } : {};
  }

  async function fetchJson(path) {
    const r = await fetch(path, { headers: { ...authHeaders() } });
    if (!r.ok) throw new Error(`${path}: ${r.status}`);
    return r.json();
  }

  async function refreshDashboard() {
    try {
      const [stats, sla, health] = await Promise.all([
        fetchJson("/api/admin/dashboard/stats"),
        fetchJson("/api/tickets/sla-dashboard").catch(() => ({})),
        fetchJson("/api/network/health-map").catch(() => ({ items: [] })),
      ]);

      setText("kpi-total-customers", stats.total_customers);
      setText("kpi-active-tickets", stats.active_tickets);
      setText("kpi-online-devices", `${stats.online_devices} / ${stats.total_devices}`);
      setText("kpi-network-health", `${stats.network_health_percent}%`);
      setText("kpi-unpaid-invoices", stats.unpaid_invoices);
      setText("kpi-active-calls", stats.active_calls);
      setText("kpi-sla-compliance", sla.compliance_rate ? `${sla.compliance_rate}%` : "—");
      setText("kpi-breached", sla.breached_sla ?? "—");

      const list = document.getElementById("area-health-list");
      if (list && health.items) {
        list.innerHTML = health.items
          .map(
            (a) => `
            <li class="area-row" data-status="${a.status}">
              <span class="area-name">${a.area_name}</span>
              <span class="area-online">${a.online_devices}/${a.total_devices}</span>
              <span class="area-score">${a.health_score}%</span>
            </li>`
          )
          .join("");
      }
    } catch (e) {
      console.warn("Dashboard refresh failed", e);
    }
  }

  function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value ?? "—";
  }

  function connectLiveEvents() {
    // SSE not available natively for our pub/sub; use the agent WS bridge
    const userId = localStorage.getItem("dh_user_id") || "admin";
    const wsUrl = (location.protocol === "https:" ? "wss://" : "ws://") + location.host + `/api/agent/ws/${userId}`;
    try {
      const ws = new WebSocket(wsUrl);
      ws.addEventListener("message", (e) => {
        try {
          const ev = JSON.parse(e.data);
          renderLiveEvent(ev);
        } catch (_) {}
      });
      ws.addEventListener("close", () => setTimeout(connectLiveEvents, 5000));
    } catch (e) {
      console.warn("WS connect error", e);
    }
  }

  function renderLiveEvent(ev) {
    const feed = document.getElementById("live-event-feed");
    if (!feed) return;
    const ts = new Date().toLocaleTimeString();
    const item = document.createElement("div");
    item.className = `live-event live-event--${ev.channel?.split(":")[0] ?? "info"}`;
    item.innerHTML = `<span class="ts">${ts}</span>
                      <span class="ch">${ev.channel ?? ""}</span>
                      <span class="msg">${JSON.stringify(ev.data ?? {}).slice(0, 180)}</span>`;
    feed.prepend(item);
    while (feed.children.length > 50) feed.removeChild(feed.lastChild);
  }

  document.addEventListener("DOMContentLoaded", () => {
    refreshDashboard();
    setInterval(refreshDashboard, 30000);
    connectLiveEvents();
  });
})();
