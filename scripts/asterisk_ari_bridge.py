import asyncio
import json
import base64
import websockets
import aiohttp
from loguru import logger

# --- CONFIGURATION ---
# Asterisk ARI Settings
ARI_URL = "http://asterisk-server:8088/ari"
ARI_USER = "nexa_bot"
ARI_PASS = "secure_password"
ARI_APP = "nexa-isp-bot"

# Nexa AI Bot Settings
AI_BOT_WS_URL = "ws://localhost:8000/ws/voice"

async def bridge_call_to_ai(channel_id):
    """
    Bridges a live Asterisk channel to the Nexa AI Voice Bot via WebSockets.
    """
    session_id = f"phone_{channel_id[:8]}"
    ai_ws_url = f"{AI_BOT_WS_URL}/{session_id}"
    
    logger.info(f"Connecting Call {channel_id} to AI Bot at {ai_ws_url}")
    
    try:
        async with websockets.connect(ai_ws_url) as ai_ws:
            logger.success(f"Connected to Nexa AI Bot for session {session_id}")
            
            # Note: In a real implementation, you would use Asterisk External Media 
            # or AudioSocket to get raw PCM audio from the channel.
            # This loop simulates the data relay.
            
            async def relay_asterisk_to_ai():
                """Relays audio from phone (Asterisk) -> AI Bot"""
                # This is where you would read from Asterisk AudioSocket
                # for chunk in asterisk_audio_stream:
                #     await ai_ws.send(json.dumps({"type": "audio", "data": base64_audio}))
                pass

            async def relay_ai_to_asterisk():
                """Relays audio from AI Bot -> Phone (Asterisk)"""
                async for message in ai_ws:
                    data = json.loads(message)
                    if data["type"] == "audio":
                        # Play audio back to Asterisk channel
                        # write_to_asterisk_channel(data["data"])
                        logger.debug("Received audio from AI, playing to phone...")
                    elif data["type"] == "response":
                        logger.info(f"AI Response: {data['text']}")

            await asyncio.gather(
                relay_asterisk_to_ai(),
                relay_ai_to_asterisk()
            )

    except Exception as e:
        logger.error(f"Error in ARI-AI Bridge: {e}")

async def monitor_asterisk_events():
    """
    Listens to Asterisk ARI events and triggers the AI bridge for new calls.
    """
    auth = aiohttp.BasicAuth(ARI_USER, ARI_PASS)
    ari_ws_url = f"ws://asterisk-server:8088/ari/events?api_key={ARI_USER}:{ARI_PASS}&app={ARI_APP}"

    logger.info(f"Monitoring Asterisk ARI events for app: {ARI_APP}...")
    
    async with websockets.connect(ari_ws_url) as ws:
        async for message in ws:
            event = json.loads(message)
            
            # Event: New Call Enters Stasis Application
            if event.get("type") == "StasisStart":
                channel_id = event["channel"]["id"]
                logger.info(f"New incoming call detected: {channel_id}")
                
                # Start the 2-way bridge in the background
                asyncio.create_task(bridge_call_to_ai(channel_id))

if __name__ == "__main__":
    logger.info("Starting NexaISP Asterisk Bridge...")
    try:
        asyncio.run(monitor_asterisk_events())
    except KeyboardInterrupt:
        logger.info("Bridge stopped by user.")
