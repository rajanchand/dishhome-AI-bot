"""
DishHome AI Voice Bot - Speech-to-Text Engine
Uses faster-whisper for high-performance multilingual transcription.
Supports Nepali (ne) and English (en) with automatic language detection.
"""

import io
import numpy as np
from typing import Optional, Tuple
from loguru import logger

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None
    logger.warning("faster-whisper not installed. STT will use mock mode.")

from config.settings import settings


class STTEngine:
    """
    Speech-to-Text engine powered by faster-whisper.
    
    Supports:
    - Real-time transcription from audio chunks
    - Automatic language detection (Nepali/English)
    - Configurable model sizes for speed/accuracy tradeoff
    """

    SUPPORTED_LANGUAGES = {"ne": "Nepali", "en": "English"}

    def __init__(self):
        self._model: Optional[object] = None
        self._initialized = False

    async def initialize(self) -> None:
        """Load the Whisper model into memory."""
        if self._initialized:
            return

        if WhisperModel is None:
            logger.warning("STT Engine running in MOCK mode (faster-whisper not installed)")
            self._initialized = True
            return

        try:
            logger.info(
                f"Loading Whisper model: {settings.whisper_model_size} "
                f"on {settings.whisper_device} ({settings.whisper_compute_type})"
            )
            self._model = WhisperModel(
                settings.whisper_model_size,
                device=settings.whisper_device,
                compute_type=settings.whisper_compute_type,
            )
            self._initialized = True
            logger.success("STT Engine initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize STT Engine: {e}")
            raise

    async def transcribe(
        self,
        audio_data: bytes,
        sample_rate: int = 16000,
        language: Optional[str] = None,
    ) -> Tuple[str, str, float]:
        """
        Transcribe audio data to text.

        Args:
            audio_data: Raw audio bytes (PCM 16-bit)
            sample_rate: Audio sample rate (default 16000 Hz)
            language: Force language ('ne' or 'en'), None for auto-detect

        Returns:
            Tuple of (transcribed_text, detected_language, confidence)
        """
        if not self._initialized:
            await self.initialize()

        if self._model is None:
            # Mock mode for development
            return self._mock_transcribe(audio_data)

        try:
            # Convert bytes to numpy float32 array
            audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(
                np.float32
            )
            audio_array /= 32768.0  # Normalize to [-1, 1]

            # Transcribe with optional language hint
            segments, info = self._model.transcribe(
                audio_array,
                language=language,
                beam_size=5,
                word_timestamps=False,
                vad_filter=True,
                vad_parameters=dict(
                    min_silence_duration_ms=500,
                    speech_pad_ms=200,
                ),
            )

            # Collect all segment texts
            text_parts = []
            for segment in segments:
                text_parts.append(segment.text.strip())

            transcribed_text = " ".join(text_parts).strip()
            detected_language = info.language or "en"
            confidence = info.language_probability or 0.0

            # Map to supported languages
            if detected_language not in self.SUPPORTED_LANGUAGES:
                detected_language = "en"

            logger.info(
                f"STT Result: lang={detected_language} "
                f"conf={confidence:.2f} text='{transcribed_text[:80]}...'"
            )

            return transcribed_text, detected_language, confidence

        except Exception as e:
            logger.error(f"STT transcription error: {e}")
            return "", "en", 0.0

    async def transcribe_stream(
        self,
        audio_chunks: list[bytes],
        sample_rate: int = 16000,
        language: Optional[str] = None,
    ) -> Tuple[str, str, float]:
        """
        Transcribe a stream of audio chunks.
        Concatenates chunks and transcribes as a single audio segment.

        Args:
            audio_chunks: List of audio byte chunks
            sample_rate: Audio sample rate
            language: Force language or None for auto-detect

        Returns:
            Tuple of (transcribed_text, detected_language, confidence)
        """
        # Concatenate all chunks
        combined_audio = b"".join(audio_chunks)

        if len(combined_audio) < 1600:  # Less than 0.1s of audio at 16kHz
            return "", "en", 0.0

        return await self.transcribe(combined_audio, sample_rate, language)

    def _mock_transcribe(self, audio_data: bytes) -> Tuple[str, str, float]:
        """Mock transcription for development without Whisper."""
        logger.debug(f"Mock STT: received {len(audio_data)} bytes")
        return (
            "This is a mock transcription for development.",
            "en",
            0.95,
        )

    async def shutdown(self) -> None:
        """Release model resources."""
        if self._model is not None:
            del self._model
            self._model = None
        self._initialized = False
        logger.info("STT Engine shut down")


# Singleton instance
stt_engine = STTEngine()
