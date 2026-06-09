import re

from django.contrib.postgres.search import TrigramSimilarity
from django.db.models import FloatField, Q
from django.db.models.functions import Greatest

from care.emr.models.product_knowledge import ProductKnowledge

# Maps keywords in eAushadhi drug names to SNOMED display substrings
# used in ProductKnowledge.definitional["dosage_form"]["display"].
# Values are lists so one eAushadhi form keyword can match multiple CARE representations
# (e.g. "suspension" is sometimes stored as "Oral drop" or "Syrup" in CARE).
DOSAGE_FORM_MAP = {
    "tablet": ["tablet"],
    "tablets": ["tablet"],
    "capsule": ["capsule"],
    "capsules": ["capsule"],
    "injection": ["injection"],
    "infusion": ["infusion"],
    "suspension": ["suspension", "drop", "syrup"],
    "syrup": ["syrup", "suspension", "drop"],
    "cream": ["cream"],
    "gel": ["gel"],
    "ointment": ["ointment"],
    "eye": ["eye"],
    "drops": ["drop", "suspension"],
    "powder": ["powder"],
    "solution": ["solution"],
}

_FORM_STOP = {
    "tablet", "tablets", "capsule", "capsules", "injection", "infusion",
    "suspension", "syrup", "cream", "gel", "ointment", "eye", "ear",
    "oral", "drops", "powder", "solution", "for", "with",
}


def extract_generic_name(drug_name: str) -> str:
    """Return the drug substance before dosage form / strength tokens."""
    words = drug_name.lower().split()
    generic = []
    for word in words:
        clean = re.sub(r"[^a-z]", "", word)
        if clean in _FORM_STOP:
            break
        if re.match(r"^\d", word):
            break
        if clean:
            generic.append(word)
    return " ".join(generic) if generic else words[0]


def normalize_drug_name(name: str) -> str:
    """Full normalised form used as the second similarity signal."""
    name = name.lower()
    name = re.sub(r"\b(ip|bp|usp|who|nih)\b", "", name)
    name = re.sub(r"\b\d+x\d+(?:x\d+)?\b", "", name)
    name = re.sub(r"(\d+)\s*(mg|ml|mcg|iu|g|%)", r"\1 \2", name)
    name = re.sub(r"\btablets?\b", "tablet", name)
    name = re.sub(r"\bcapsules?\b", "capsule", name)
    name = re.sub(r"\binjections?\b", "injection", name)
    name = re.sub(r"\bsuspensions?\b", "suspension", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


# Phrases that contain dosage-form words but are NOT a dosage form themselves.
# Stripped before keyword detection to avoid false-positive form pre-filtering.
_FORM_MODIFIERS = [
    r"powder\s+free",  # "Powder free" gloves, catheters, etc.
    r"latex\s+free",
    r"preservative\s+free",
    r"alcohol\s+free",
]


def extract_dosage_form_filter(drug_name: str) -> list[str] | None:
    """Return SNOMED display substrings to pre-filter by, or None to skip filtering."""
    name_lower = drug_name.lower()
    for modifier in _FORM_MODIFIERS:
        name_lower = re.sub(modifier, "", name_lower)
    for keyword, snomed_displays in DOSAGE_FORM_MAP.items():
        if re.search(rf"\b{keyword}\b", name_lower):
            return snomed_displays
    return None


def confidence_tier(score: float) -> str:
    if score >= 0.85:
        return "high"
    if score >= 0.50:
        return "medium"
    return "low"


def get_fuzzy_suggestions(drug_name: str, facility, limit: int = 10):
    """
    Return a list of ProductKnowledge objects annotated with .similarity,
    using three signals and an optional dosage-form pre-filter.
    Includes both facility-scoped and global (facility__isnull=True) records.

    The dosage-form filter is tried first for better precision. If it yields
    no results (e.g. CARE only has Paracetamol as a tablet but the eAushadhi
    name says "Suspension"), we fall back to the unfiltered search so the
    pharmacist still sees the closest match.
    """
    generic_name = extract_generic_name(drug_name)
    normalized = normalize_drug_name(drug_name)
    dosage_form = extract_dosage_form_filter(drug_name)

    base_qs = ProductKnowledge.objects.filter(
        Q(facility__isnull=True) | Q(facility=facility)
    )

    def _ranked(qs):
        return list(
            qs.annotate(
                generic_sim=TrigramSimilarity("name", generic_name),
                full_sim=TrigramSimilarity("name", normalized),
                alt_sim=TrigramSimilarity("names_cache", generic_name),
                similarity=Greatest("generic_sim", "full_sim", "alt_sim", output_field=FloatField()),
            )
            .filter(similarity__gt=0.3)
            .order_by("-similarity")
            .select_related("category", "facility")
            [:limit]
        )

    if dosage_form:
        form_q = Q()
        for display in dosage_form:
            form_q |= Q(definitional__dosage_form__display__icontains=display)
        results = _ranked(base_qs.filter(form_q))
        if results:
            return results
        # Form-filtered search found nothing — fall back to all forms so the
        # pharmacist can still see the closest drug-substance match.

    return _ranked(base_qs)
