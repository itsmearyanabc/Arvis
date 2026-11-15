"""Niche groups ARVIS prospects. One Google Sheet tab per group. Keep to real Maps business
categories, B2B only, high lifetime value (they can afford a proper website / brand project)."""

GROUPS = {
    "Healthcare": {
        "dentist": ["dentist", "dental clinic", "orthodontist"],
        "physiotherapy": ["physiotherapy clinic", "physiotherapist", "chiropractor"],
        "cosmetic clinic": ["cosmetic clinic", "medical spa", "dermatology clinic"],
    },
    "Legal & Finance": {
        "law firm": ["law firm", "lawyer", "solicitor"],
        "accounting firm": ["accounting firm", "chartered accountant", "tax advisor"],
    },
    "Property": {
        "real estate": ["real estate agency", "realtor", "estate agent"],
        "interior design": ["interior designer", "interior design studio", "architect"],
    },
    "Home Services": {
        "roofing": ["roofing contractor", "roofer"],
        "hvac": ["hvac contractor", "air conditioning repair", "heating company"],
        "renovation": ["renovation contractor", "kitchen remodeling", "general contractor"],
    },
    "Hospitality & Wellness": {
        "boutique hotel": ["boutique hotel", "bed and breakfast"],
        "gym": ["gym", "fitness studio", "yoga studio"],
    },
    "Education": {
        "private school": ["private school", "international school", "tutoring center"],
    },
}

NICHE_TO_GROUP = {niche: group for group, niches in GROUPS.items() for niche in niches}
SYNONYMS = {niche: syns for niches in GROUPS.values() for niche, syns in niches.items()}

def group_of(niche: str) -> str:
    return NICHE_TO_GROUP.get((niche or "").lower(), "Other")

def synonyms_of(niche: str):
    return SYNONYMS.get((niche or "").lower(), [niche])
