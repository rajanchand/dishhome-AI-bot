"""
DishHome AI Voice Bot - Text-to-Speech Engine
Uses Microsoft Edge-TTS for high-quality bilingual speech synthesis.
Supports Nepali (ne-NP) and English (en-US) voices.
"""

import io
import asyncio
from typing import Optional
from loguru import logger

try:
    import edge_tts
except ImportError:
    edge_tts = None
    logger.warning("edge-tts not installed. TTS will use mock mode.")

from config.settings import settings


class TTSEngine:
    """
    Text-to-Speech engine powered by Microsoft Edge-TTS.
    
    Supports:
    - Nepali voice: ne-NP-SagarNeural / ne-NP-HemkalaNeural
    - English voice: en-US-AriaNeural / en-US-GuyNeural
    - Adjustable rate and volume
    - Streaming audio output
    """

    VOICE_MAP = {
        "ne": {
            "male": "ne-NP-SagarNeural",
            "female": "ne-NP-HemkalaNeural",
        },
        "en": {
            "male": "en-US-GuyNeural",
            "female": "en-US-AriaNeural",
        },
    }

    def __init__(self):
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the TTS engine."""
        if self._initialized:
            return

        if edge_tts is None:
            logger.warning("TTS Engine running in MOCK mode (edge-tts not installed)")

        self._initialized = True
        logger.success("TTS Engine initialized successfully")

    def _get_voice(self, language: str, gender: str = "male") -> str:
        """
        Get the appropriate voice for the given language and gender.

        Args:
            language: Language code ('ne' or 'en')
            gender: Voice gender ('male' or 'female')

        Returns:
            Voice identifier string
        """
        lang = language[:2].lower()
        if lang not in self.VOICE_MAP:
            lang = "en"

        voices = self.VOICE_MAP[lang]
        return voices.get(gender, voices["male"])

    async def synthesize(
        self,
        text: str,
        language: str = "en",
        gender: str = "male",
        rate: Optional[str] = None,
        volume: Optional[str] = None,
    ) -> bytes:
        """
        Convert text to speech audio.

        Args:
            text: Text to convert to speech
            language: Language code ('ne' or 'en')
            gender: Voice gender ('male' or 'female')
            rate: Speech rate override (e.g., '+10%', '-5%')
            volume: Volume override (e.g., '+20%', '-10%')

        Returns:
            Audio data as bytes (MP3 format)
        """
        if not self._initialized:
            await self.initialize()

        if edge_tts is None:
            return self._mock_synthesize(text)

        voice = self._get_voice(language, gender)
        rate = rate or settings.tts_rate
        volume = volume or settings.tts_volume

        try:
            logger.info(
                f"TTS: voice={voice} rate={rate} "
                f"text='{text[:60]}...'"
            )

            communicate = edge_tts.Communicate(
                text=text,
                voice=voice,
                rate=rate,
                volume=volume,
            )

            # Collect audio chunks
            audio_chunks = []
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_chunks.append(chunk["data"])

            audio_data = b"".join(audio_chunks)
            logger.info(f"TTS: Generated {len(audio_data)} bytes of audio")

            return audio_data

        except Exception as e:
            logger.error(f"TTS synthesis error: {e}")
            return b""

    async def synthesize_stream(
        self,
        text: str,
        language: str = "en",
        gender: str = "male",
    ):
        """
        Stream TTS audio chunks as they are generated.
        Yields audio chunks for real-time playback.

        Args:
            text: Text to convert to speech
            language: Language code ('ne' or 'en')
            gender: Voice gender ('male' or 'female')

        Yields:
            Audio data chunks (bytes)
        """
        if not self._initialized:
            await self.initialize()

        if edge_tts is None:
            yield self._mock_synthesize(text)
            return

        voice = self._get_voice(language, gender)

        try:
            communicate = edge_tts.Communicate(
                text=text,
                voice=voice,
                rate=settings.tts_rate,
                volume=settings.tts_volume,
            )

            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    yield chunk["data"]

        except Exception as e:
            logger.error(f"TTS streaming error: {e}")

    def _mock_synthesize(self, text: str) -> bytes:
        """Mock synthesis for development without edge-tts."""
        logger.debug(f"Mock TTS: '{text[:50]}...'")
        # Return empty audio placeholder
        return b"\x00" * 1000

    async def list_voices(self, language: Optional[str] = None) -> list:
        """
        List available TTS voices, optionally filtered by language.

        Args:
            language: Filter by language code (e.g., 'ne', 'en')

        Returns:
            List of available voice dictionaries
        """
        if edge_tts is None:
            return []

        try:
            voices = await edge_tts.list_voices()
            if language:
                lang_prefix = {
                    "ne": "ne-NP",
                    "en": "en-US",
                }.get(language, language)
                voices = [
                    v for v in voices
                    if v.get("Locale", "").startswith(lang_prefix)
                ]
            return voices
        except Exception as e:
            logger.error(f"Failed to list voices: {e}")
            return []

    async def shutdown(self) -> None:
        """Clean up TTS resources."""
        self._initialized = False
        logger.info("TTS Engine shut down")


# Singleton instance
tts_engine = TTSEngine()
