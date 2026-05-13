/**
 * DishHome AI Voice Bot - Dashboard Logic
 * Handles metrics polling, session display, and performance tracking.
 */

class Dashboard {
    constructor() {
        this.pollInterval = null;
        this.metrics = {};
    }

    /**
     * Start polling for dashboard metrics.
     */
    startPolling(intervalMs = 5000) {
        this.fetchMetrics();
        this.fetchSessions();
        this.pollInterval = setInterval(() => {
            this.fetchMetrics();
            this.fetchSessions();
        }, intervalMs);
    }

    stopPolling() {
        if (this.pollInterval) clearInterval(this.pollInterval);
    }

    async fetchMetrics() {
        try {
            const res = await fetch('/api/analytics/dashboard');
            const data = await res.json();
            this.metrics = data;
            this.updateMetricsUI(data);
        } catch (e) {
            console.warn('Failed to fetch metrics:', e);
        }
    }

    async fetchSessions() {
        try {
            const res = await fetch('/api/analytics/sessions');
            const data = await res.json();
            this.updateSessionsUI(data);
        } catch (e) {
            console.warn('Failed to fetch sessions:', e);
        }
    }

    updateMetricsUI(data) {
        const el = (id) => document.getElementById(id);
        if (el('metric-total')) el('metric-total').textContent = data.total_calls || 0;
        if (el('metric-active')) el('metric-active').textContent = data.active_calls || 0;
        if (el('metric-duration')) el('metric-duration').textContent = (data.avg_duration || 0) + 's';
        if (el('metric-resolution')) el('metric-resolution').textContent = (data.resolution_rate || 0) + '%';
        if (el('lang-en-count')) el('lang-en-count').textContent = data.english_calls || 0;
        if (el('lang-ne-count')) el('lang-ne-count').textContent = data.nepali_calls || 0;

        // Language bars
        const total = (data.english_calls || 0) + (data.nepali_calls || 0) || 1;
        if (el('lang-en-bar')) el('lang-en-bar').style.width = ((data.english_calls || 0) / total * 100) + '%';
        if (el('lang-ne-bar')) el('lang-ne-bar').style.width = ((data.nepali_calls || 0) / total * 100) + '%';
    }

    updateSessionsUI(data) {
        const list = document.getElementById('call-list');
        const countEl = document.getElementById('active-count');
        if (!list) return;

        const sessions = data.sessions || [];
        const active = sessions.filter(s => s.active);

        if (countEl) countEl.textContent = `${active.length} active`;

        if (sessions.length === 0) {
            list.innerHTML = '<div class="empty-state"><div class="icon">📭</div><p>No active calls</p></div>';
            return;
        }

        list.innerHTML = sessions.slice(0, 10).map(s => `
            <div class="call-item" onclick="viewSession('${s.session_id}')">
                <div class="call-avatar">${s.active ? '🟢' : '⚪'}</div>
                <div class="call-info">
                    <div class="name">${s.session_id.substring(0, 16)}...</div>
                    <div class="detail">${s.turns} turns · ${s.duration}s · ${s.language === 'ne' ? 'नेपाली' : 'English'}</div>
                </div>
                <span class="call-status ${s.needs_handoff ? 'handoff' : (s.active ? 'active' : 'completed')}">
                    ${s.needs_handoff ? 'Handoff' : (s.active ? 'Active' : 'Done')}
                </span>
            </div>
        `).join('');
    }

    /**
     * Update performance metrics from pipeline response.
     */
    updatePerformance(metrics) {
        const el = (id) => document.getElementById(id);
        if (!metrics) return;

        const sttMs = Math.round((metrics.stt_time || 0) * 1000);
        const llmMs = Math.round((metrics.llm_time || 0) * 1000);
        const ttsMs = Math.round((metrics.tts_time || 0) * 1000);
        const totalMs = Math.round((metrics.total_time || 0) * 1000);

        if (el('perf-stt')) el('perf-stt').textContent = sttMs + 'ms';
        if (el('perf-llm')) el('perf-llm').textContent = llmMs + 'ms';
        if (el('perf-tts')) el('perf-tts').textContent = ttsMs + 'ms';
        if (el('perf-total')) el('perf-total').textContent = totalMs + 'ms';

        // Bars (scale: max 5000ms = 100%)
        const maxMs = 5000;
        if (el('perf-stt-bar')) el('perf-stt-bar').style.width = Math.min(sttMs / maxMs * 100, 100) + '%';
        if (el('perf-llm-bar')) el('perf-llm-bar').style.width = Math.min(llmMs / maxMs * 100, 100) + '%';
        if (el('perf-tts-bar')) el('perf-tts-bar').style.width = Math.min(ttsMs / maxMs * 100, 100) + '%';
        if (el('perf-total-bar')) el('perf-total-bar').style.width = Math.min(totalMs / maxMs * 100, 100) + '%';
    }
}

function viewSession(sessionId) {
    console.log('View session:', sessionId);
}

window.Dashboard = Dashboard;
