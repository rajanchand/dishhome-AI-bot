"""
LLM function-calling schemas (Ollama / OpenAI compatible).
30 ISP-specific tools the AI agent can call to perform real actions.
"""

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_customer_profile",
            "description": "Retrieve customer profile by phone number or customer code. Always use this first when caller identifies themselves.",
            "parameters": {
                "type": "object",
                "properties": {
                    "identifier": {"type": "string", "description": "Phone number (e.g. 9841234567) or customer code (DH-YYYY-NNNNNN)"},
                    "identifier_type": {"type": "string", "enum": ["phone", "customer_code"]},
                },
                "required": ["identifier", "identifier_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "verify_customer_identity",
            "description": "Verify caller identity by cross-checking phone, DOB, or address.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string"},
                    "verification_type": {"type": "string", "enum": ["phone_match", "dob", "address"]},
                    "verification_value": {"type": "string"},
                },
                "required": ["customer_id", "verification_type", "verification_value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_otp_to_customer",
            "description": "Send an OTP to the customer's registered phone number for sensitive actions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string"},
                    "purpose": {"type": "string", "enum": ["identity_verify", "package_change", "payment", "reboot"]},
                },
                "required": ["customer_id", "purpose"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "verify_otp",
            "description": "Verify an OTP entered by the customer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string"},
                    "otp": {"type": "string"},
                    "purpose": {"type": "string"},
                },
                "required": ["customer_id", "otp", "purpose"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_customer_contact",
            "description": "Update customer's secondary phone or email after verification.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string"},
                    "field": {"type": "string", "enum": ["phone_secondary", "email"]},
                    "new_value": {"type": "string"},
                },
                "required": ["customer_id", "field", "new_value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "log_interaction",
            "description": "Log this customer interaction to CRM contact history.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string"},
                    "interaction_type": {"type": "string", "enum": ["call", "sms", "email", "chat"]},
                    "summary": {"type": "string"},
                    "outcome": {"type": "string", "enum": ["resolved", "escalated", "pending", "information_provided"]},
                },
                "required": ["customer_id", "interaction_type", "summary", "outcome"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_complaint_history",
            "description": "Get recent tickets/complaints for a customer to spot recurring issues.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string"},
                    "limit": {"type": "integer", "default": 5},
                },
                "required": ["customer_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_network_status",
            "description": "Check current ONU/router status (online/offline, PPPoE) for a customer.",
            "parameters": {
                "type": "object",
                "properties": {"customer_id": {"type": "string"}},
                "required": ["customer_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_area_outage",
            "description": "Check if there is an active network outage in the customer's service area.",
            "parameters": {
                "type": "object",
                "properties": {"customer_id": {"type": "string"}},
                "required": ["customer_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_pppoe_session",
            "description": "Inspect active PPPoE session details.",
            "parameters": {
                "type": "object",
                "properties": {"customer_id": {"type": "string"}},
                "required": ["customer_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_signal_diagnostics",
            "description": "Get optical signal Rx/Tx power and LOS classification for an ONU.",
            "parameters": {
                "type": "object",
                "properties": {"customer_id": {"type": "string"}},
                "required": ["customer_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_speed_test_data",
            "description": "Get last recorded speed test results for a customer.",
            "parameters": {
                "type": "object",
                "properties": {"customer_id": {"type": "string"}},
                "required": ["customer_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_bandwidth_usage",
            "description": "Get bandwidth usage stats for a period.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string"},
                    "period": {"type": "string", "enum": ["today", "this_week", "this_month", "last_month"]},
                },
                "required": ["customer_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_mac_registration",
            "description": "Check if a MAC address is registered, and to which customer.",
            "parameters": {
                "type": "object",
                "properties": {"mac_address": {"type": "string"}},
                "required": ["mac_address"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "reboot_customer_device",
            "description": "Remotely reboot a customer ONU. Requires OTP verification first via verify_otp(purpose=reboot).",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["customer_id", "reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_noc_alerts",
            "description": "Get current active NOC incidents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "severity_filter": {"type": "string", "enum": ["all", "critical", "high"], "default": "all"},
                    "limit": {"type": "integer", "default": 10},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_billing_status",
            "description": "Get billing status, outstanding invoices, and payment history for a customer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string"},
                    "include_history": {"type": "boolean", "default": False},
                },
                "required": ["customer_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_payment_reminder",
            "description": "Send an SMS payment reminder for an outstanding invoice.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string"},
                    "invoice_id": {"type": "string"},
                },
                "required": ["customer_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_package_info",
            "description": "Get details of a specific package, or list all available packages.",
            "parameters": {
                "type": "object",
                "properties": {
                    "package_id": {"type": "string"},
                    "list_all": {"type": "boolean", "default": False},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "upgrade_package",
            "description": "Upgrade subscription to a new package. Requires OTP confirmation first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string"},
                    "new_package_id": {"type": "string"},
                },
                "required": ["customer_id", "new_package_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_renewal_options",
            "description": "Get renewal package options for an expiring subscription.",
            "parameters": {
                "type": "object",
                "properties": {"customer_id": {"type": "string"}},
                "required": ["customer_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_service_availability",
            "description": "Check if DishHome fiber service is available at a given address.",
            "parameters": {
                "type": "object",
                "properties": {
                    "municipality": {"type": "string"},
                    "ward": {"type": "string"},
                },
                "required": ["municipality"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_support_ticket",
            "description": "Create a new support ticket for an unresolved issue.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string"},
                    "category": {"type": "string", "enum": ["connectivity", "billing", "hardware", "new_connection", "inquiry"]},
                    "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "field_visit_required": {"type": "boolean", "default": False},
                },
                "required": ["customer_id", "category", "priority", "title", "description"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_existing_tickets",
            "description": "Check for existing open tickets to avoid duplicates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string"},
                    "status_filter": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["customer_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "escalate_ticket_priority",
            "description": "Increase priority of an existing ticket.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticket_id": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["ticket_id", "reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "schedule_technician_visit",
            "description": "Schedule a field technician visit.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string"},
                    "ticket_id": {"type": "string"},
                    "preferred_date": {"type": "string", "description": "YYYY-MM-DD"},
                    "preferred_time_slot": {"type": "string", "enum": ["morning", "afternoon", "evening"]},
                    "issue_description": {"type": "string"},
                },
                "required": ["customer_id", "ticket_id", "preferred_date", "preferred_time_slot"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_technician_availability",
            "description": "Check available technicians for an area + date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "area_id": {"type": "string"},
                    "date": {"type": "string"},
                },
                "required": ["area_id", "date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "register_new_connection_lead",
            "description": "Register a lead for a new internet connection installation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "full_name": {"type": "string"},
                    "phone": {"type": "string"},
                    "address": {"type": "string"},
                    "preferred_package_id": {"type": "string"},
                    "notes": {"type": "string"},
                },
                "required": ["full_name", "phone", "address"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "request_human_agent",
            "description": "Escalate the call to a human support agent with full context.",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "reason": {"type": "string"},
                    "priority": {"type": "string", "enum": ["normal", "urgent"], "default": "normal"},
                    "summary": {"type": "string"},
                },
                "required": ["session_id", "reason", "summary"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "Search FAQs and troubleshooting guides.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "language": {"type": "string", "enum": ["ne", "en"], "default": "ne"},
                },
                "required": ["query"],
            },
        },
    },
]
