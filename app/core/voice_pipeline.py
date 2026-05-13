"""
DishHome AI Voice Bot - Voice Pipeline
Orchestrates the full STT → LLM → TTS pipeline for real-time voice processing.
"""

import asyncio
import time
from typing import Optional
from loguru import logger

from app.core.stt_engine import stt_engine
from app.core.tts_engine import tts_engine
from app.core.llm_engine import llm_engine
from app.core.language_detector import language_detector
from app.core.conversation import conversation_manager, ConversationState


class VoicePipeline:
    """
    Orchestrates the complete voice processing pipeline:
    1. Receive audio → STT (transcribe)
    2. Detect language
    3. Generate LLM response
    4. TTS (synthesize response)
    5. Return audio
    """

    def __init__(self):
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize all pipeline components."""
        if self._initialized:
            return
        logger.info("Initializing Voice Pipeline...")
        await stt_engine.initialize()
        await tts_engine.initialize()
        await llm_engine.initialize()
        self._initialized = True
        logger.success("Voice Pipeline initialized")

    async def process_audio(
        self,
        audio_data: bytes,
        session_id: str,
        sample_rate: int = 16000,
    ) -> dict:
        """
        Process an audio input through the full pipeline.

        Args:
            audio_data: Raw PCM audio bytes
            session_id: Conversation session ID
            sample_rate: Audio sample rate

        Returns:
            dict with keys: text, response, audio, language, session_id
        """
        if not self._initialized:
            await self.initialize()

        start_time = time.time()
        session = conversation_manager.get_session(session_id)
        if not session:
            session = conversation_manager.create_session(session_id)

        # Step 1: Speech-to-Text
        stt_start = time.time()
        transcribed_text, whisper_lang, confidence = await stt_engine.transcribe(
            audio_data, sample_rate
        )
        stt_time = time.time() - stt_start

        if not transcribed_text.strip():
            return {
                "text": "",
                "response": "",
                "audio": b"",
                "language": session.language,
                "session_id": session_id,
                "metrics": {"stt_time": stt_time},
            }

        # Step 2: Language Detection
        detected_language = language_detector.detect(
            transcribed_text, whisper_lang, confidence
        )

        # Step 3: Add user turn to conversation
        session.add_turn("user", transcribed_text, detected_language, confidence)

        # Step 4: Generate LLM Response
        llm_start = time.time()
        response_text = await llm_engine.generate_response(
            user_message=transcribed_text,
            conversation_history=session.get_history(),
            language=detected_language,
            customer_context=session.customer_context,
        )
        llm_time = time.time() - llm_start

        # Step 5: Add assistant turn
        session.add_turn("assistant", response_text, detected_language)

        # Step 6: Check for handoff triggers
        handoff_triggers = [
            "connect you with", "transfer you", "human agent",
            "customer service representative",
            "ग्राहक सेवा प्रतिनिधि", "जोड्छु",
        ]
        if any(trigger in response_text.lower() for trigger in handoff_triggers):
            conversation_manager.request_handoff(
                session_id, "AI suggested human agent transfer"
            )

        # Step 7: Text-to-Speech
        tts_start = time.time()
        audio_response = await tts_engine.synthesize(
            text=response_text,
            language=detected_language,
        )
        tts_time = time.time() - tts_start

        total_time = time.time() - start_time
        logger.info(
            f"Pipeline complete: STT={stt_time:.2f}s LLM={llm_time:.2f}s "
            f"TTS={tts_time:.2f}s Total={total_time:.2f}s"
        )

        return {
            "text": transcribed_text,
            "response": response_text,
            "audio": audio_response,
            "language": detected_language,
            "session_id": session_id,
            "metrics": {
                "stt_time": round(stt_time, 3),
                "llm_time": round(llm_time, 3),
                "tts_time": round(tts_time, 3),
                "total_time": round(total_time, 3),
            },
        }

    async def process_text(
        self,
        text: str,
        session_id: str,
        language: Optional[str] = None,
    ) -> dict:
        """
        Process a text input (skip STT step). Useful for text chat mode.

        Args:
            text: User's text message
            session_id: Session ID
            language: Language override

        Returns:
            dict with response text and audio
        """
        if not self._initialized:
            await self.initialize()

        session = conversation_manager.get_session(session_id)
        if not session:
            session = conversation_manager.create_session(session_id)

        detected_language = language or language_detector.detect(text)
        session.add_turn("user", text, detected_language)

        response_text = await llm_engine.generate_response(
            user_message=text,
            conversation_history=session.get_history(),
            language=detected_language,
            customer_context=session.customer_context,
        )
        session.add_turn("assistant", response_text, detected_language)

        audio_response = await tts_engine.synthesize(
            text=response_text, language=detected_language,
        )

        return {
            "text": text,
            "response": response_text,
            "audio": audio_response,
            "language": detected_language,
            "session_id": session_id,
        }

    async def shutdown(self) -> None:
        """Shut down all pipeline components."""
        await stt_engine.shutdown()
        await tts_engine.shutdown()
        await llm_engine.shutdown()
        self._initialized = False
        logger.info("Voice Pipeline shut down")


voice_pipeline = VoicePipeline()
