"""SMS (Sparrow) + Email (SMTP) notifications."""

from email.message import EmailMessage
from typing import Optional, List

import aiosmtplib
import httpx
from loguru import logger

from config.settings import settings


class NotificationService:
    async def send_sms(self, to_phone: str, message: str) -> bool:
        if not settings.sparrow_sms_token:
            logger.info(f"[SMS-STUB] {to_phone}: {message}")
            return True
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.post(
                    settings.sparrow_sms_url,
                    data={
                        "token": settings.sparrow_sms_token,
                        "from": settings.sparrow_sms_from,
                        "to": to_phone,
                        "text": message,
                    },
                )
                ok = r.status_code == 200
                if ok:
                    logger.info(f"SMS sent to {to_phone}")
                else:
                    logger.warning(f"SMS failed: {r.status_code} {r.text[:200]}")
                return ok
        except Exception as e:
            logger.warning(f"SMS error: {e}")
            return False

    async def send_email(
        self, to_email: str, subject: str, body: str,
        html: bool = False, cc: Optional[List[str]] = None,
    ) -> bool:
        if not settings.smtp_username:
            logger.info(f"[EMAIL-STUB] {to_email} | {subject}")
            return True
        try:
            msg = EmailMessage()
            msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
            msg["To"] = to_email
            if cc:
                msg["Cc"] = ", ".join(cc)
            msg["Subject"] = subject
            if html:
                msg.set_content("HTML-only message")
                msg.add_alternative(body, subtype="html")
            else:
                msg.set_content(body)
            await aiosmtplib.send(
                msg,
                hostname=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_username,
                password=settings.smtp_password,
                start_tls=settings.smtp_use_tls,
            )
            logger.info(f"Email sent to {to_email}")
            return True
        except Exception as e:
            logger.warning(f"Email error: {e}")
            return False

    async def send_payment_reminder(self, phone: str, customer_name: str,
                                      amount: float, due_date: str,
                                      invoice_number: str) -> bool:
        msg = (
            f"नमस्ते {customer_name} जी, तपाईंको DishHome बिल INV-{invoice_number} "
            f"NPR {amount:,.2f} due {due_date}. eSewa वा Khalti बाट तिर्न सक्नुहुन्छ।"
        )
        return await self.send_sms(phone, msg)

    async def send_sla_breach_alert(self, agent_email: str, ticket_number: str,
                                      priority: str, customer_name: str) -> bool:
        return await self.send_email(
            agent_email,
            subject=f"[SLA BREACH] Ticket {ticket_number} ({priority})",
            body=(
                f"Ticket {ticket_number} for {customer_name} ({priority} priority) "
                f"has breached its SLA deadline. Please action immediately."
            ),
        )

    async def send_outage_notification(self, phone: str, area: str,
                                        estimated_resolution: str) -> bool:
        msg = (
            f"DishHome: तपाईंको क्षेत्र {area} मा network outage छ। "
            f"अनुमानित समाधान: {estimated_resolution}. क्षमायाचना।"
        )
        return await self.send_sms(phone, msg)


notification_service = NotificationService()
