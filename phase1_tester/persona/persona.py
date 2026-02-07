"""Persona definition and question/stop detection."""

import re

PERSONA: dict = {
    "motivation": "i am Sam - i need to buy for stability, family with kids",
    "target_buy_date": "Feb 2027 (flexible)",
    "comfort_with_process": "7/10",
    "main_stress": "getting approved",
    "annual_income_usd": 120000,
    "down_payment_available": 200000,
    "state_focus": "New Jersey",
    "area_focus": "Wayne (ok nearby: Pequannock/Riverdale if needed)",
    "purchase_budget_max": 200000,
    "property_type": "condo",
    "bedrooms_min": 3,
    "bathrooms_min": 2,
    "monthly_payment_target": 3000,
    "condition_preference": "light cosmetic updates ok",
    "proximity_requirements": "Wayne Hills High School and Pompton Lakes",
    "max_drive_time": "30 minutes",
    "quiet_environment_preference": "quiet",
    "safety_importance": "10/10",
    "outdoor_space_required": "optional; small patio nice-to-have",
    "deadline_type": "flexible",
}

QUESTION_STARTERS = (
    "how ",
    "what ",
    "which ",
    "when ",
    "where ",
    "why ",
    "do you ",
    "are you ",
    "on a scale ",
)


def persona_context() -> dict:
    """Return a copy of the persona dict for context."""
    return dict(PERSONA)


def is_question(text: str) -> bool:
    """Treat the assistant message as requiring a reply if it asks something."""
    if not text or not text.strip():
        return False
    t = text.strip().lower()
    if "?" in text:
        return True
    for start in QUESTION_STARTERS:
        if t.startswith(start):
            return True
    if re.search(r":\s*$", text.strip()):
        return True
    return False


def stop_condition(text: str) -> bool:
    """Stop when assistant outputs a final Summary/closing message."""
    if not text or not text.strip():
        return False
    lower = text.lower()
    if "i've gathered all the information i need" in lower:
        return True
    if "based on our conversation" in lower:
        return True
    if "would you like to continue with" in lower:
        return True
    words = len(text.split())
    paragraphs = len([p for p in text.split("\n\n") if p.strip()])
    if words >= 80 and paragraphs >= 2:
        return True
    return False
