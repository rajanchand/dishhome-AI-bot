/**
 * DishHome AI Voice Bot - Voice Client
 * Handles WebSocket connection, audio recording, and playback.
 */

class VoiceClient {
    constructor() {
        this.ws = null;
        this.mediaRecorder = null;
        this.audioContext = null;
        this.isRecording = false;
        this.sessionId = this._generateId();
        this.audioChunks = [];
        this.onTranscript = null;
        this.onResponse = null;
        this.onAudio = null;
        this.onMetrics = null;
        this.onHandoff = null;
        this.onConnectionChange = null;
    }

    _generateId() {
        return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    /**
     * Connect to the voice WebSocket server.
     */
    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const url = `${protocol}//${window.location.host}/ws/voice/${this.sessionId}`;

        try {
            this.ws = new WebSocket(url);

            this.ws.onopen = () => {
                console.log('WebSocket connected:', this.sessionId);
                if (this.onConnectionChange) this.onConnectionChange(true);
            };

            this.ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this._handleMessage(data);
            };

            this.ws.onclose = () => {
                console.log('WebSocket disconnected');
                if (this.onConnectionChange) this.onConnectionChange(false);
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                if (this.onConnectionChange) this.onConnectionChange(false);
            };
        } catch (e) {
            console.error('Failed to connect WebSocket:', e);
        }
    }

    _handleMessage(data) {
        switch (data.type) {
            case 'transcript':
                if (this.onTranscript) this.onTranscript(data.text, data.language);
                break;
            case 'response':
                if (this.onResponse) this.onResponse(data.text, data.language);
                break;
            case 'audio':
                if (this.onAudio) this.onAudio(data.data);
                this._playAudio(data.data);
                break;
            case 'metrics':
                if (this.onMetrics) this.onMetrics(data.data);
                break;
            case 'handoff':
                if (this.onHandoff) this.onHandoff(data.reason);
                break;
        }
    }

    /**
     * Start recording audio from the microphone.
     */
    async startRecording() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    sampleRate: 16000,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true,
                }
            });

            this.audioContext = new AudioContext({ sampleRate: 16000 });
            this.audioChunks = [];
            this.isRecording = true;

            this.mediaRecorder = new MediaRecorder(stream, {
                mimeType: MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
                    ? 'audio/webm;codecs=opus' : 'audio/webm'
            });

            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.audioChunks.push(event.data);
                }
            };

            this.mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
                await this._sendAudio(audioBlob);
                stream.getTracks().forEach(track => track.stop());
            };

            this.mediaRecorder.start(250); // Collect chunks every 250ms
            console.log('Recording started');
        } catch (e) {
            console.error('Failed to start recording:', e);
            this.isRecording = false;
        }
    }

    /**
     * Stop recording and send audio to server.
     */
    stopRecording() {
        if (this.mediaRecorder && this.isRecording) {
            this.mediaRecorder.stop();
            this.isRecording = false;
            console.log('Recording stopped');
        }
    }

    async _sendAudio(audioBlob) {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
            console.warn('WebSocket not connected');
            return;
        }

        try {
            const arrayBuffer = await audioBlob.arrayBuffer();
            const base64 = btoa(String.fromCharCode(...new Uint8Array(arrayBuffer)));
            this.ws.send(JSON.stringify({
                type: 'audio',
                data: base64,
            }));
        } catch (e) {
            console.error('Failed to send audio:', e);
        }
    }

    /**
     * Send a text message via WebSocket.
     */
    sendText(text) {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
            // Fall back to REST API
            this._sendTextREST(text);
            return;
        }
        this.ws.send(JSON.stringify({ type: 'text', data: text }));
    }

    async _sendTextREST(text) {
        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: text,
                    session_id: this.sessionId,
                }),
            });
            const data = await response.json();
            if (this.onResponse) this.onResponse(data.response, data.language);
        } catch (e) {
            console.error('REST chat failed:', e);
        }
    }

    /**
     * Play base64-encoded audio.
     */
    async _playAudio(base64Data) {
        try {
            const binaryStr = atob(base64Data);
            const bytes = new Uint8Array(binaryStr.length);
            for (let i = 0; i < binaryStr.length; i++) {
                bytes[i] = binaryStr.charCodeAt(i);
            }
            const blob = new Blob([bytes], { type: 'audio/mpeg' });
            const url = URL.createObjectURL(blob);
            const audio = new Audio(url);
            audio.play().catch(e => console.warn('Audio autoplay blocked:', e));
            audio.onended = () => URL.revokeObjectURL(url);
        } catch (e) {
            console.warn('Audio playback failed:', e);
        }
    }

    /**
     * Disconnect WebSocket and clean up.
     */
    disconnect() {
        if (this.ws) {
            this.ws.send(JSON.stringify({ type: 'end' }));
            this.ws.close();
        }
        if (this.audioContext) {
            this.audioContext.close();
        }
    }
}

// Export singleton
window.VoiceClient = VoiceClient;
