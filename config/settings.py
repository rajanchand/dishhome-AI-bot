"""
DishHome AI Call Center - Application Settings
Centralized configuration using Pydantic Settings.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional, List
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ── Server ──────────────────────────────────────────────────────────────
    app_host: str = Field(default="0.0.0.0")
    app_port: int = Field(default=8000)
    app_env: str = Field(default="development")
    app_debug: bool = Field(default=True)
    app_secret_key: str = Field(default="dev-secret-key-CHANGE-in-production-min-32-chars")
    app_name: str = Field(default="DishHome AI Call Center")
    app_version: str = Field(default="2.0.0")

    # ── CORS ────────────────────────────────────────────────────────────────
    cors_allowed_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000", "http://localhost:8001"]
    )

    # ── PostgreSQL (Primary Database) ─────────────────────────────────────
    database_url: str = Field(
        default="postgresql+asyncpg://dishhome:dishhome_secret@localhost:5432/dishhome_db"
    )
    direct_url: Optional[str] = Field(default=None)
    database_pool_size: int = Field(default=20)
    database_max_overflow: int = Field(default=40)
    database_pool_recycle: int = Field(default=300)

    # ── Redis ─────────────────────────────────────────────────────────────
    redis_url: str = Field(default="redis://localhost:6379/0")
    redis_session_ttl: int = Field(default=3600)       # 1 hour
    redis_cache_ttl: int = Field(default=300)           # 5 minutes
    redis_network_ttl: int = Field(default=60)          # 1 minute

    # ── Celery ────────────────────────────────────────────────────────────
    celery_broker_url: str = Field(default="redis://localhost:6379/1")
    celery_result_backend: str = Field(default="redis://localhost:6379/2")

    # ── Elasticsearch ─────────────────────────────────────────────────────
    elasticsearch_url: str = Field(default="http://localhost:9200")
    elasticsearch_index_prefix: str = Field(default="dishhome")

    # ── S3 / MinIO ────────────────────────────────────────────────────────
    s3_endpoint_url: str = Field(default="http://localhost:9000")
    s3_access_key: str = Field(default="minioadmin")
    s3_secret_key: str = Field(default="minioadmin123")
    s3_region: str = Field(default="us-east-1")
    s3_bucket_recordings: str = Field(default="call-recordings")
    s3_bucket_attachments: str = Field(default="ticket-attachments")
    s3_presigned_expiry: int = Field(default=3600)      # 1 hour

    # ── JWT Authentication ─────────────────────────────────────────────────
    jwt_secret_key: str = Field(default="jwt-secret-CHANGE-in-production-min-32-chars")
    jwt_algorithm: str = Field(default="HS256")
    jwt_access_expire_minutes: int = Field(default=30)
    jwt_refresh_expire_days: int = Field(default=7)

    # ── Ollama LLM ─────────────────────────────────────────────────────────
    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_model: str = Field(default="llama3.1:8b")
    ollama_timeout: int = Field(default=60)

    # ── Whisper STT ────────────────────────────────────────────────────────
    whisper_model_size: str = Field(default="base")
    whisper_device: str = Field(default="cpu")
    whisper_compute_type: str = Field(default="int8")

    # ── Edge-TTS ───────────────────────────────────────────────────────────
    tts_voice_nepali: str = Field(default="ne-NP-SagarNeural")
    tts_voice_english: str = Field(default="en-US-AriaNeural")
    tts_rate: str = Field(default="+0%")
    tts_volume: str = Field(default="+0%")

    # ── Huawei iMaster NCE OLT API ─────────────────────────────────────────
    huawei_olt_base_url: str = Field(default="http://192.168.1.1:8080")
    huawei_olt_username: str = Field(default="admin")
    huawei_olt_password: str = Field(default="")
    huawei_olt_timeout: int = Field(default=30)

    # ── SMS Gateway (Sparrow SMS) ──────────────────────────────────────────
    sparrow_sms_token: str = Field(default="")
    sparrow_sms_from: str = Field(default="DishHome")
    sparrow_sms_url: str = Field(default="https://api.sparrowsms.com/v2/sms/")

    # ── Email (SMTP) ───────────────────────────────────────────────────────
    smtp_host: str = Field(default="smtp.gmail.com")
    smtp_port: int = Field(default=587)
    smtp_username: str = Field(default="")
    smtp_password: str = Field(default="")
    smtp_from_email: str = Field(default="noreply@dishhome.com.np")
    smtp_from_name: str = Field(default="DishHome Support")
    smtp_use_tls: bool = Field(default=True)

    # ── Payment Gateways ───────────────────────────────────────────────────
    esewa_merchant_code: str = Field(default="")
    esewa_secret_key: str = Field(default="")
    esewa_base_url: str = Field(default="https://uat.esewa.com.np")
    khalti_secret_key: str = Field(default="")
    khalti_base_url: str = Field(default="https://khalti.com/api/v2")

    # ── Observability ──────────────────────────────────────────────────────
    sentry_dsn: str = Field(default="")
    otel_exporter_otlp_endpoint: str = Field(default="http://localhost:4317")
    enable_prometheus: bool = Field(default=True)

    # ── Supabase ───────────────────────────────────────────────────────────
    supabase_url: str = Field(default="")
    supabase_key: str = Field(default="")
    supabase_service_role_key: str = Field(default="")
    supabase_jwt_secret: str = Field(default="")

    # ── Logging ────────────────────────────────────────────────────────────
    log_level: str = Field(default="INFO")
    log_file: str = Field(default="logs/voicebot.log")

    # ── Legacy Basic Auth (kept for backward-compat during migration) ──────
    agent_username: str = Field(default="admin")
    agent_password: str = Field(default="dishhome@2024")

    # ── Security ───────────────────────────────────────────────────────────
    max_failed_logins: int = Field(default=5)
    lockout_duration_minutes: int = Field(default=30)
    password_min_length: int = Field(default=12)
    upload_max_size_bytes: int = Field(default=10 * 1024 * 1024)  # 10 MB
    allowed_upload_types: List[str] = Field(
        default=["image/jpeg", "image/png", "application/pdf"]
    )

    # ── Derived Properties ─────────────────────────────────────────────────
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
        "extra": "ignore",
    }


settings = Settings()
