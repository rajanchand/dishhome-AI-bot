"""
DishHome AI Voice Bot - Voice WebSocket Routes
Real-time voice streaming and text chat endpoints.
"""

import json
import base64
import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import Response
from loguru import logger

from app.core.voice_pipeline import voice_pipeline
from app.core.conversation import conversation_manager
from app.models.schemas import TextChatRequest, TextChatResponse
from app.services.call_service import call_service

router = APIRouter(tags=["voice"])


class ConnectionManager:
    """Manages active WebSocket connections."""

    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"WebSocket connected: {session_id}")

    def disconnect(self, session_id: str):
        self.active_connections.pop(session_id, None)
        logger.info(f"WebSocket disconnected: {session_id}")

    async def send_json(self, session_id: str, data: dict):
        ws = self.active_connections.get(session_id)
        if ws:
            await ws.send_json(data)

    async def send_bytes(self, session_id: str, data: bytes):
        ws = self.active_connections.get(session_id)
        if ws:
            await ws.send_bytes(data)


ws_manager = ConnectionManager()


@router.websocket("/ws/voice/{session_id}")
async def voice_websocket(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time voice communication.

    Protocol:
    - Client sends: {"type": "audio", "data": "<base64 PCM audio>"}
    - Client sends: {"type": "text", "data": "<text message>"}
    - Client sends: {"type": "end"}
    - Server sends: {"type": "transcript", "text": "...", "language": "..."}
    - Server sends: {"type": "response", "text": "...", "language": "..."}
    - Server sends: {"type": "audio", "data": "<base64 audio>"}
    - Server sends: {"type": "metrics", "data": {...}}
    - Server sends: {"type": "handoff", "reason": "..."}
    """
    await ws_manager.connect(websocket, session_id)
    conversation_manager.create_session(session_id)

    try:
        await call_service.create_call(session_id)
    except Exception as e:
        logger.warning(f"Failed to create call record: {e}")

    # Send welcome message
    try:
        welcome = await voice_pipeline.process_text(
            text="greeting",
            session_id=session_id,
            language="ne",
        )
        await websocket.send_json({
            "type": "response",
            "text": welcome["response"],
            "language": welcome["language"],
        })
        if welcome["audio"]:
            await websocket.send_json({
                "type": "audio",
                "data": base64.b64encode(welcome["audio"]).decode("utf-8"),
            })
    except Exception as e:
        logger.warning(f"Failed to send welcome: {e}")

    try:
        while True:
            message = await websocket.receive_json()
            msg_type = message.get("type", "")

            if msg_type == "audio":
                # Decode base64 audio
                audio_data = base64.b64decode(message["data"])
                result = await voice_pipeline.process_audio(
                    audio_data=audio_data,
                    session_id=session_id,
                )

                if result["text"]:
                    await websocket.send_json({
                        "type": "transcript",
                        "text": result["text"],
                        "language": result["language"],
                    })
                    await websocket.send_json({
                        "type": "response",
                        "text": result["response"],
                        "language": result["language"],
                    })
                    if result["audio"]:
                        await websocket.send_json({
                            "type": "audio",
                            "data": base64.b64encode(result["audio"]).decode("utf-8"),
                        })
                    await websocket.send_json({
                        "type": "metrics",
                        "data": result.get("metrics", {}),
                    })

                    # Check for handoff
                    session = conversation_manager.get_session(session_id)
                    if session and session.needs_handoff:
                        await websocket.send_json({
                            "type": "handoff",
                            "reason": session.handoff_reason,
                        })

            elif msg_type == "text":
                result = await voice_pipeline.process_text(
                    text=message["data"],
                    session_id=session_id,
                )
                await websocket.send_json({
                    "type": "response",
                    "text": result["response"],
                    "language": result["language"],
                })
                if result["audio"]:
                    await websocket.send_json({
                        "type": "audio",
                        "data": base64.b64encode(result["audio"]).decode("utf-8"),
                    })

            elif msg_type == "end":
                break

    except WebSocketDisconnect:
        logger.info(f"Client disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error ({session_id}): {e}")
    finally:
        ws_manager.disconnect(session_id)
        session = conversation_manager.end_session(session_id)
        if session:
            try:
                await call_service.end_call(
                    session_id=session_id,
                    transcript=[t.__dict__ for t in session.turns] if hasattr(session, 'turns') else [],
                    turn_count=session.turn_count,
                    duration=session.duration_seconds,
                )
            except Exception as e:
                logger.warning(f"Failed to save call record: {e}")


@router.post("/api/chat", response_model=TextChatResponse)
async def text_chat(request: TextChatRequest):
    """Text-based chat endpoint (alternative to voice)."""
    session_id = request.session_id or str(uuid.uuid4())

    result = await voice_pipeline.process_text(
        text=request.message,
        session_id=session_id,
        language=request.language,
    )

    return TextChatResponse(
        session_id=session_id,
        user_message=request.message,
        response=result["response"],
        language=result["language"],
        has_audio=bool(result.get("audio")),
    )


@router.get("/api/chat/audio/{session_id}")
async def get_last_audio(session_id: str):
    """Get the last TTS audio for a session."""
    # This would be stored in cache/session in production
    return Response(content=b"", media_type="audio/mpeg")
