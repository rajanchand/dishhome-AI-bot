"""
DishHome AI Voice Bot - Language Detector
Automatic language detection for Nepali/English.
"""

from typing import Optional
from loguru import logger

try:
    from langdetect import detect, LangDetectException
except ImportError:
    detect = None


class LanguageDetector:
    """Detects whether input text is Nepali or English using multiple signals."""

    DEVANAGARI_RANGE = range(0x0900, 0x097F + 1)

    def detect(self, text: str, whisper_language: Optional[str] = None,
               whisper_confidence: float = 0.0) -> str:
        if not text or not text.strip():
            return "en"

        if whisper_language and whisper_confidence > 0.8:
            lang = whisper_language[:2].lower()
            if lang in ("ne", "en"):
                return lang

        devanagari_ratio = self._devanagari_ratio(text)
        if devanagari_ratio > 0.3:
            return "ne"

        if detect is not None:
            try:
                detected = detect(text)
                if detected in ("ne", "hi"):
                    return "ne"
                elif detected == "en":
                    return "en"
            except (LangDetectException, Exception):
                pass

        if whisper_language:
            lang = whisper_language[:2].lower()
            if lang in ("ne", "en"):
                return lang

        return "ne"

    def _devanagari_ratio(self, text: str) -> float:
        if not text:
            return 0.0
        total = sum(1 for c in text if not c.isspace())
        devnag = sum(1 for c in text if ord(c) in self.DEVANAGARI_RANGE)
        return devnag / total if total > 0 else 0.0

    def get_language_name(self, code: str) -> str:
        return {"ne": "Nepali", "en": "English"}.get(code, "Unknown")


language_detector = LanguageDetector()
