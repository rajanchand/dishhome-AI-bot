/**
 * DishHome AI Voice Bot - Main Application
 * Initializes voice client, dashboard, and UI interactions.
 */

// ── Global State ────────────────────────────
let voiceClient = null;
let dashboard = null;
let currentLanguage = 'en';
let isRecording = false;

// ── Initialize ──────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    // Init voice client
    voiceClient = new VoiceClient();
    voiceClient.onTranscript = handleTranscript;
    voiceClient.onResponse = handleResponse;
    voiceClient.onMetrics = handleMetrics;
    voiceClient.onHandoff = handleHandoff;
    voiceClient.onConnectionChange = handleConnectionChange;

    // Connect WebSocket
    voiceClient.connect();

    // Show session ID
    const sessionEl = document.getElementById('session-id');
    if (sessionEl) sessionEl.textContent = voiceClient.sessionId.substring(0, 20);

    // Init dashboard polling
    dashboard = new Dashboard();
    dashboard.startPolling(5000);

    // Check system health
    checkHealth();

    console.log('DishHome AI Voice Bot initialized');
});

// ── Message Handling ────────────────────────
function handleTranscript(text, language) {
    addMessage('user', text, language);
}

function handleResponse(text, language) {
    removeTypingIndicator();
    addMessage('bot', text, language);
}

function handleMetrics(metrics) {
    if (dashboard) dashboard.updatePerformance(metrics);
}

function handleHandoff(reason) {
    addSystemMessage(`🔄 Transfer requested: ${reason}`);
}

function handleConnectionChange(connected) {
    const dot = document.getElementById('system-status');
    if (dot) {
        dot.className = connected ? 'status-dot' : 'status-dot offline';
    }
}

// ── Chat UI Functions ───────────────────────
function addMessage(role, text, language) {
    const container = document.getElementById('chat-messages');
    const emptyState = document.getElementById('empty-state');
    if (emptyState) emptyState.remove();

    const langBadge = language === 'ne' ? '<span class="lang-badge ne">NE</span>' : '<span class="lang-badge en">EN</span>';
    const time = new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    const avatar = role === 'bot' ? '🤖' : '👤';

    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}`;
    msgDiv.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div>
            <div class="message-content">${escapeHtml(text)}</div>
            <div class="message-meta">${time} ${langBadge}</div>
        </div>
    `;

    container.appendChild(msgDiv);
    container.scrollTop = container.scrollHeight;
}

function addSystemMessage(text) {
    const container = document.getElementById('chat-messages');
    const div = document.createElement('div');
    div.style.cssText = 'text-align:center; padding:8px; font-size:0.78rem; color:var(--warning);';
    div.textContent = text;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function showTypingIndicator() {
    const container = document.getElementById('chat-messages');
    const existing = document.getElementById('typing-indicator');
    if (existing) return;

    const div = document.createElement('div');
    div.id = 'typing-indicator';
    div.className = 'message bot';
    div.innerHTML = `
        <div class="message-avatar">🤖</div>
        <div class="message-content">
            <div class="typing-indicator"><span></span><span></span><span></span></div>
        </div>
    `;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function removeTypingIndicator() {
    const el = document.getElementById('typing-indicator');
    if (el) el.remove();
}

// ── User Actions ────────────────────────────
function sendTextMessage() {
    const input = document.getElementById('chat-input');
    const text = input.value.trim();
    if (!text) return;

    addMessage('user', text, currentLanguage);
    input.value = '';
    showTypingIndicator();

    if (voiceClient) {
        voiceClient.sendText(text);
    }
}

function toggleRecording() {
    const btn = document.getElementById('btn-mic');
    const viz = document.getElementById('audio-viz');

    if (!isRecording) {
        isRecording = true;
        btn.classList.add('recording');
        btn.innerHTML = '⏹️';
        if (viz) viz.style.display = 'flex';
        if (voiceClient) voiceClient.startRecording();
    } else {
        isRecording = false;
        btn.classList.remove('recording');
        btn.innerHTML = '🎤';
        if (viz) viz.style.display = 'none';
        if (voiceClient) voiceClient.stopRecording();
        showTypingIndicator();
    }
}

function setLanguage(lang) {
    currentLanguage = lang;
    document.getElementById('btn-lang-en').classList.toggle('active', lang === 'en');
    document.getElementById('btn-lang-ne').classList.toggle('active', lang === 'ne');
}

// ── Health Check ────────────────────────────
async function checkHealth() {
    try {
        const res = await fetch('/api/health');
        const data = await res.json();
        const dot = document.getElementById('ollama-status');
        const text = document.getElementById('ollama-status-text');
        if (data.status === 'healthy') {
            if (dot) dot.className = 'status-dot';
            if (text) text.textContent = 'Ollama Connected';
        }
    } catch (e) {
        const dot = document.getElementById('ollama-status');
        const text = document.getElementById('ollama-status-text');
        if (dot) dot.className = 'status-dot offline';
        if (text) text.textContent = 'Ollama Offline';
    }
}

// ── Utility ─────────────────────────────────
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
