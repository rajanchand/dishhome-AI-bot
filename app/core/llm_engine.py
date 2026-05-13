"""
DishHome AI Voice Bot - LLM Engine
Integrates with Ollama for local LLM inference.
Handles bilingual (Nepali/English) conversation with ISP-specific knowledge.
"""

import json
from typing import Optional, AsyncGenerator
from loguru import logger

try:
    import ollama as ollama_client
    from ollama import AsyncClient
except ImportError:
    ollama_client = None
    AsyncClient = None
    logger.warning("ollama package not installed. LLM will use mock mode.")

from config.settings import settings


# ── System Prompt ─────────────────────────────────────────────
DISHHOME_SYSTEM_PROMPT = """
You are “Khushi”, a fully autonomous OFFLINE AI Voice Call Center System for DishHome ISP.

==================================================
PRIMARY ROLE & ISP WORKFLOW
==================================================

You must follow the standard ISP operational flow strictly:

1. IDENTITY VERIFICATION (MANDATORY START):
   - At the beginning of the call (after greeting), you MUST collect and verify:
     - Registered Mobile Number OR Customer ID.
   - Use `get_customer_profile` to verify. If not found, ask again politely.
   - Do NOT proceed to technical diagnostics without verification unless it's a "New Connection" (Sales) inquiry.

2. SALES FLOW (New Connection):
   - If customer wants a new connection:
     - Collect Full Name, Phone, and Address.
     - Use `register_new_connection_lead` to create a lead.
     - Inform them that a sales representative will call within 2 hours.

3. TECHNICAL FLOW (Troubleshooting):
   - Check `check_network_status` and `check_area_outage` immediately.
   - If a signal issue is detected (LOS/Low Power), guide them to reboot.
   - If issue persists, inform them you are creating a Technical Ticket.

4. TICKETING & VENDOR ASSIGNMENT:
   - When creating a ticket via `create_support_ticket`:
     - Set `field_visit_required` to `true` for hardware/physical issues.
     - The system will AUTOMATICALLY assign the best local Vendor based on the customer's Service Area (synced from Admin Dashboard).
     - Provide the Ticket Number (e.g., TK-2026-XXXXXX) to the customer.

==================================================
VOICE CONVERSATION RULES
==================================================

- Speak like a real human support agent. Use short voice-friendly sentences (5–15 words).
- Default Language: Nepali. Auto-switch to English if the customer speaks English.
- REQUIRED OPENING: “Namaste. Thank you for calling ISP Support. Ma tapailai kasari help garna sakchu?”

==================================================
AUTO ACTIONS & TOOLS
==================================================

You have access to:
- CRM (Profile, History, Interaction Logs)
- Network (ONU Status, Ping, PPPoE Reset, Outage Maps)
- Billing (Invoices, Payment Reminders, Package Upgrades)
- Tickets (Create, Escalate, Assign Vendor, Schedule Visit)
- Sales (New Connection Lead Registration)

Never hallucinate diagnostics or fake actions. If a tool fails, inform the customer and offer human handoff.
"""


class LLMEngine:
    """
    LLM Engine powered by Ollama for local inference.
    """

    def __init__(self):
        self._client: Optional[object] = None
        self._initialized = False
        self._model = settings.ollama_model

    async def initialize(self) -> None:
        """Initialize connection to Ollama server."""
        if self._initialized:
            return

        if AsyncClient is None:
            logger.warning("LLM Engine running in MOCK mode (ollama not installed)")
            self._initialized = True
            return

        try:
            self._client = AsyncClient(host=settings.ollama_base_url)
            self._initialized = True
            logger.success(f"LLM Engine initialized (model: {self._model})")
        except Exception as e:
            logger.error(f"Failed to initialize LLM Engine: {e}")
            self._initialized = True

    async def generate_response(
        self,
        user_message: str,
        conversation_history: list[dict],
        language: str = "en",
        customer_context: Optional[dict] = None,
    ) -> str:
        """Generate a response to the user's message."""
        if user_message == "greeting":
            return "Namaste. Thank you for calling ISP Support. Ma tapailai kasari help garna sakchu?"

        if not self._initialized:
            await self.initialize()

        if self._client is None:
            return await self._mock_response(user_message, language)

        try:
            from app.core.tool_schemas import TOOL_SCHEMAS
            from app.core.function_caller import function_caller

            messages = self._build_messages(
                user_message, conversation_history, language, customer_context
            )

            response = await self._client.chat(
                model=self._model,
                messages=messages,
                tools=TOOL_SCHEMAS,
                options={"temperature": 0.7, "num_predict": 128}
            )

            msg = response.get("message", {})
            tool_calls = msg.get("tool_calls") or []

            if not tool_calls:
                return msg.get("content", "").strip() or self._error_response(language)

            # Process tool calls
            for tc in tool_calls:
                fn = tc.get("function", {})
                name = fn.get("name")
                args = fn.get("arguments", {})
                if isinstance(args, str):
                    try: args = json.loads(args)
                    except: args = {}
                
                logger.info(f"Khushi calling tool: {name}")
                result = await function_caller.call(name, args)
                messages.append({"role": "assistant", "content": None, "tool_calls": [tc]})
                messages.append({"role": "tool", "name": name, "content": json.dumps(result)})

            # Final response after tool calls
            final_response = await self._client.chat(
                model=self._model,
                messages=messages
            )
            return final_response.get("message", {}).get("content", "").strip()

        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            # Fallback to mock response if Ollama is unavailable
            if "connect" in str(e).lower() or "connection" in str(e).lower():
                logger.warning("Ollama connection failed, falling back to mock mode")
                return await self._mock_response(user_message, language)
            return self._error_response(language)

    async def generate_response_stream(
        self,
        user_message: str,
        conversation_history: list[dict],
        language: str = "en",
        customer_context: Optional[dict] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream a response."""
        if not self._initialized:
            await self.initialize()

        if self._client is None:
            yield await self._mock_response(user_message, language)
            return

        try:
            messages = self._build_messages(user_message, conversation_history, language, customer_context)
            stream = await self._client.chat(model=self._model, messages=messages, stream=True)
            async for chunk in stream:
                token = chunk["message"]["content"]
                if token: yield token
        except Exception as e:
            logger.error(f"LLM streaming error: {e}")
            yield self._error_response(language)

    def _build_messages(self, user_message, conversation_history, language, customer_context):
        messages = [{"role": "system", "content": DISHHOME_SYSTEM_PROMPT}]
        if customer_context:
            messages[0]["content"] += f"\n[Customer: {customer_context.get('name', 'N/A')}, ID: {customer_context.get('customer_id', 'N/A')}]"
        
        lang_hint = "\nRespond in Nepali (नेपाली)." if language == "ne" else "\nRespond in English."
        messages[0]["content"] += lang_hint

        for msg in conversation_history[-6:]:
            messages.append(msg)
        messages.append({"role": "user", "content": user_message})
        return messages

    async def _mock_response(self, user_message: str, language: str) -> str:
        """Fallback mock responses when Ollama is unavailable."""
        msg = user_message.lower()
        if "id" in msg or any(c.isdigit() for c in msg):
            if language == "en":
                return "Thank you. Checking your DishHome router status now... It seems to be online with good signal."
            return "धन्यवाद। तपाईंको DishHome राउटर चेक गर्दैछु... यो अनलाइन छ र सिग्नल राम्रो छ।"
        
        if "bill" in msg or "pay" in msg:
            if language == "en":
                return "Your current balance is NPR 0. Your subscription is valid until next month."
            return "तपाईंको ब्यालेन्स रु ० छ। तपाईंको प्याकेज अर्को महिनासम्म बाँकी छ।"

        if language == "en":
            return "I am Khushi, your DishHome assistant. How can I help you with your internet today?"
        return "नमस्ते, म DishHome बाट खुशी हुँ। आज म तपाईंलाई इन्टरनेट सम्बन्धी के सहयोग गर्न सक्छु?"

    def _error_response(self, language: str) -> str:
        if language == "en":
            return "I'm sorry, I'm having trouble connecting to my brain. Please try again or ask for a human."
        return "माफ गर्नुहोस्, मेरो सिस्टममा केही समस्या आयो। कृपया केही समय पछि प्रयास गर्नुहोस्।"

    async def shutdown(self) -> None:
        self._client = None
        self._initialized = False


llm_engine = LLMEngine()
