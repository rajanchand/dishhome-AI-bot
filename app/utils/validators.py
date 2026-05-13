"""Phone, NID, MAC, and email validators."""

import re
from typing import Optional

import phonenumbers
from phonenumbers import NumberParseException


def normalize_phone(phone: str, default_country: str = "NP") -> Optional[str]:
    """Normalize a Nepali phone number to +977XXXXXXXXXX format."""
    if not phone:
        return None
    cleaned = re.sub(r"[\s\-\(\)]", "", phone)
    try:
        parsed = phonenumbers.parse(cleaned, default_country)
        if not phonenumbers.is_valid_number(parsed):
            return None
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except NumberParseException:
        return None


def is_valid_nepali_mobile(phone: str) -> bool:
    """Quick check: Nepali mobile = 98XXXXXXXX (10 digits)."""
    if not phone:
        return False
    cleaned = re.sub(r"\D", "", phone)
    if cleaned.startswith("977"):
        cleaned = cleaned[3:]
    return bool(re.match(r"^9[78]\d{8}$", cleaned))


def validate_mac_address(mac: str) -> bool:
    if not mac:
        return False
    return bool(re.match(r"^([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$", mac))


def normalize_mac(mac: str) -> str:
    if not mac:
        return ""
    cleaned = re.sub(r"[^0-9A-Fa-f]", "", mac).upper()
    if len(cleaned) != 12:
        return mac
    return ":".join(cleaned[i:i+2] for i in range(0, 12, 2))


def validate_nepali_nid(nid: str) -> bool:
    """Loose check: Nepal citizenship number = 6-15 alphanumeric."""
    if not nid:
        return False
    cleaned = nid.strip()
    return bool(re.match(r"^[A-Za-z0-9\-/]{6,20}$", cleaned))
