# DishHome AI Voice Bot

A production-ready, bilingual (Nepali/English) AI voice bot for DishHome ISP call center, powered by **Ollama LLM**, **Whisper STT**, and **Edge-TTS**.

## 🏗️ Architecture

```
Customer Voice → [STT: Whisper] → [Language Detection] → [LLM: Ollama] → [TTS: Edge-TTS] → Voice Response
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- [Ollama](https://ollama.ai/) installed and running
- FFmpeg (for audio processing)

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux

# Install packages
pip install -r requirements.txt
```

### 2. Setup Ollama

```bash
# Install Ollama (if not already)
curl -fsSL https://ollama.ai/install.sh | sh

# Pull the LLM model
ollama pull llama3.1:8b

# Verify it's running
ollama list
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings
```

### 4. Run the Server

```bash
# Development mode
python -m app.main

# Or with uvicorn directly
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Access Dashboard

Open `http://localhost:8000` in your browser.

## 🐳 Docker Deployment

```bash
# Start both voicebot and Ollama
docker-compose up -d

# Pull the LLM model inside Ollama container
docker exec dishhome-ollama ollama pull llama3.1:8b
```

## 🌐 Features

- **Bilingual Support**: Nepali (नेपाली) and English
- **Voice Pipeline**: STT → LLM → TTS in real-time
- **Auto Language Detection**: Devanagari script + Whisper + langdetect
- **DishHome Knowledge Base**: Plans, FAQ, troubleshooting
- **Agent Dashboard**: Real-time monitoring with metrics
- **Agent Handoff**: Auto-detect when human agent is needed
- **Call Logging**: Full transcript and analytics
- **WebSocket**: Real-time bidirectional voice streaming

## 📁 Project Structure

```
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── core/
│   │   ├── stt_engine.py    # Whisper Speech-to-Text
│   │   ├── tts_engine.py    # Edge-TTS Text-to-Speech
│   │   ├── llm_engine.py    # Ollama LLM integration
│   │   ├── voice_pipeline.py # Full pipeline orchestration
│   │   ├── language_detector.py
│   │   └── conversation.py  # State management
│   ├── api/routes/           # REST & WebSocket endpoints
│   ├── models/               # Database models
│   ├── services/             # Business logic
│   └── knowledge/            # FAQ & troubleshooting data
├── frontend/                 # Agent dashboard
├── docker-compose.yml
└── requirements.txt
```

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| WS | `/ws/voice/{session_id}` | Real-time voice streaming |
| POST | `/api/chat` | Text chat (REST) |
| GET | `/api/calls` | List call records |
| GET | `/api/analytics/dashboard` | Dashboard metrics |
| GET | `/api/health` | System health check |

## ⚙️ Configuration

Key environment variables (see `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_MODEL` | `llama3.1:8b` | Ollama model name |
| `WHISPER_MODEL_SIZE` | `base` | Whisper model: tiny/base/small/medium/large-v3 |
| `TTS_VOICE_NEPALI` | `ne-NP-SagarNeural` | Nepali TTS voice |
| `TTS_VOICE_ENGLISH` | `en-US-AriaNeural` | English TTS voice |

## 📜 License

MIT License - DishHome Nepal
