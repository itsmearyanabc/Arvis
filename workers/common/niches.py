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

COUNTRY_ALIASES = {"uae": "United Arab Emirates", "united arab emirates": "United Arab Emirates", "uk": "United Kingdom",
                   "united kingdom": "United Kingdom", "england": "United Kingdom", "usa": "United States", "us": "United States",
                   "united states": "United States", "america": "United States", "canada": "Canada", "australia": "Australia",
                   "india": "India", "singapore": "Singapore", "ireland": "Ireland", "new zealand": "New Zealand"}

def normalize_country(c: str) -> str:
    c = (c or "").strip()
    return COUNTRY_ALIASES.get(c.lower(), c.title() if c else c)

def normalize_niche(n: str) -> str:
    """Map free text ("interior designers", "Dentists", "law firms") onto a known niche key when possible."""
    n = (n or "").strip().lower()
    if n in SYNONYMS: return n
    cands = {n, n[:-1] if n.endswith("s") else n + "s", n[:-2] if n.endswith("es") else n}
    for niche, syns in SYNONYMS.items():
        pool = {niche, niche + "s"} | set(syns) | {s + "s" for s in syns}
        if cands & pool: return niche
    for niche in SYNONYMS:            # substring match: "dental" -> dentist, "interior designers" -> interior design
        if niche in n or n in niche: return niche
    return n

def group_of(niche: str) -> str:
    return NICHE_TO_GROUP.get(normalize_niche(niche), "Other")

def synonyms_of(niche: str):
    return SYNONYMS.get((niche or "").lower(), [niche])
