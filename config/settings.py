"""
DishHome AI Voice Bot - Application Settings
Centralized configuration using Pydantic Settings.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ── Server ──────────────────────────────────────────────
    app_host: str = Field(default="0.0.0.0", description="Server host")
    app_port: int = Field(default=8000, description="Server port")
    app_env: str = Field(default="development", description="Environment")
    app_debug: bool = Field(default=True, description="Debug mode")
    app_secret_key: str = Field(
        default="dev-secret-key-change-in-production",
        description="Secret key for sessions",
    )

    # ── Ollama LLM ──────────────────────────────────────────
    ollama_base_url: str = Field(
        default="http://localhost:11434", description="Ollama server URL"
    )
    ollama_model: str = Field(
        default="llama3.1:8b", description="Ollama model to use"
    )
    ollama_timeout: int = Field(
        default=30, description="Ollama request timeout in seconds"
    )

    # ── Whisper STT ─────────────────────────────────────────
    whisper_model_size: str = Field(
        default="base",
        description="Whisper model size: tiny, base, small, medium, large-v3",
    )
    whisper_device: str = Field(
        default="cpu", description="Device: cpu or cuda"
    )
    whisper_compute_type: str = Field(
        default="int8", description="Compute type: int8, float16, float32"
    )

    # ── Edge-TTS ────────────────────────────────────────────
    tts_voice_nepali: str = Field(
        default="ne-NP-SagarNeural", description="Nepali TTS voice"
    )
    tts_voice_english: str = Field(
        default="en-US-AriaNeural", description="English TTS voice"
    )
    tts_rate: str = Field(default="+0%", description="TTS speech rate")
    tts_volume: str = Field(default="+0%", description="TTS volume")

    # ── Database ────────────────────────────────────────────
    database_url: str = Field(
        default="sqlite+aiosqlite:///./dishhome_voicebot.db",
        description="Database connection string",
    )

    # ── Logging ─────────────────────────────────────────────
    log_level: str = Field(default="INFO", description="Log level")
    log_file: str = Field(
        default="logs/voicebot.log", description="Log file path"
    )

    # ── Auth ────────────────────────────────────────────────
    agent_username: str = Field(default="admin", description="Agent username")
    agent_password: str = Field(
        default="dishhome@2024", description="Agent password"
    )

    # ── Derived Properties ──────────────────────────────────
    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def base_dir(self) -> str:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


# Singleton settings instance
settings = Settings()
