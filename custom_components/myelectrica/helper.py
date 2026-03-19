"""
Funcții utilitare pentru integrarea MyElectrica România.

Conține:
  - Formatare valută (RON) în format românesc
  - Formatare date în limba română
  - Conversie sigură la float
  - Extragere body.response din răspunsurile API
  - Construire adresă citibilă din datele LocConsum
  - Mapping județe România (cod → nume complet)
"""

from datetime import datetime

from .const import MONTHS_EN_RO, MONTHS_NUM_RO


# ── Mapping județe România ──────────────────────

JUDETE_RO: dict[str, str] = {
    "AB": "Alba",
    "AR": "Arad",
    "AG": "Argeș",
    "BC": "Bacău",
    "BH": "Bihor",
    "BN": "Bistrița-Năsăud",
    "BT": "Botoșani",
    "BV": "Brașov",
    "BR": "Brăila",
    "B":  "București",
    "BZ": "Buzău",
    "CS": "Caraș-Severin",
    "CL": "Călărași",
    "CJ": "Cluj",
    "CT": "Constanța",
    "CV": "Covasna",
    "DB": "Dâmbovița",
    "DJ": "Dolj",
    "GL": "Galați",
    "GR": "Giurgiu",
    "GJ": "Gorj",
    "HR": "Harghita",
    "HD": "Hunedoara",
    "IL": "Ialomița",
    "IS": "Iași",
    "IF": "Ilfov",
    "MM": "Maramureș",
    "MH": "Mehedinți",
    "MS": "Mureș",
    "NT": "Neamț",
    "OT": "Olt",
    "PH": "Prahova",
    "SM": "Satu Mare",
    "SJ": "Sălaj",
    "SB": "Sibiu",
    "SV": "Suceava",
    "TR": "Teleorman",
    "TM": "Timiș",
    "TL": "Tulcea",
    "VS": "Vaslui",
    "VL": "Vâlcea",
    "VN": "Vrancea",
}


# ── Formatare valută ────────────────────────────


def format_ron(value: float) -> str:
    """Formatează o valoare numerică în format românesc (1.234,56)."""
    formatted = f"{value:,.2f}"
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")


# ── Formatare date ──────────────────────────────


def format_date_ro(date_str: str) -> str:
    """Formatează o dată ISO ca '5 ianuarie 2025'."""
    try:
        parsed = datetime.strptime(date_str, "%Y-%m-%d")
        month = MONTHS_EN_RO.get(parsed.strftime("%B"), "necunoscut")
        return f"{parsed.day} {month} {parsed.year}"
    except (ValueError, TypeError):
        return "Necunoscut"


# ── Conversie sigură la float ───────────────────


def safe_float(value, default: float = 0.0) -> float:
    """Conversie sigură la float (API-ul returnează string-uri)."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


# ── Extragere body.response ─────────────────────


def get_body_response(raw: dict | list | None):
    """
    Extrage `body.response` din răspunsul API.

    Unele endpoint-uri returnează direct `body.response`,
    altele au formatul `{status, httpCode, body: {response: ...}}`.
    """
    if raw is None:
        return None
    if isinstance(raw, list):
        return raw
    body = raw.get("body")
    if isinstance(body, dict):
        return body.get("response")
    return None


# ── Mapping județ ───────────────────────────────


def get_judet(code: str) -> str:
    """Returnează numele complet al județului din codul scurt (ex: AB → Alba)."""
    return JUDETE_RO.get(code.upper().strip(), code) if code else "Necunoscut"


# ── Construire adresă ───────────────────────────

def normalize_title(value: str) -> str:
    """Normalizează text venit din API (de obicei ALL CAPS) în Title Case curat."""
    if not value:
        return ""

    value = value.strip().lower().title()

    # Corecții pentru abrevieri românești
    replacements = {
        " Nr.": " nr.",
        " Ap.": " ap.",
        " Bl.": " bl.",
        " Sc.": " sc.",
        " Et.": " et.",
    }

    for wrong, correct in replacements.items():
        value = value.replace(wrong, correct)

    return value

def build_address(loc: dict) -> str:
    """Construiește o adresă citibilă din datele LocConsum."""
    parts = []
    street = loc.get("Street", "")
    if street:
        parts.append(street)
    nr = loc.get("HouseNumber", "")
    if nr:
        parts.append(f"nr. {nr}")
    building = loc.get("Building", "")
    if building:
        parts.append(f"bl. {building}")
    entrance = loc.get("Entrance", "")
    if entrance:
        parts.append(f"sc. {entrance}")
    floor = loc.get("Floor", "")
    if floor:
        parts.append(f"et. {floor}")
    room = loc.get("RoomNumber", "")
    if room:
        parts.append(f"ap. {room}")
    city = loc.get("City", "")
    if city:
        parts.append(city)
    return ", ".join(parts) if parts else "Adresă necunoscută"


def build_address_consum(loc: dict) -> str:
    """
    Construiește adresa de consum pe o singură linie.

    Format:
    „Ștefan cel Mare 20, 515800 Sebeș, Alba"
    „Moților 90A, ap. 17, 510128 Alba Iulia, Alba"
    """
    parts: list[str] = []

    street = normalize_title(loc.get("Street", ""))
    nr = loc.get("HouseNumber", "").strip()

    if street and nr:
        parts.append(f"{street} {nr}")
    elif street:
        parts.append(street)

    building = loc.get("Building", "").strip()
    if building:
        parts.append(f"bl. {building}")

    entrance = loc.get("Entrance", "").strip()
    if entrance:
        parts.append(f"sc. {entrance}")

    floor = loc.get("Floor", "").strip()
    if floor:
        parts.append(f"et. {floor}")

    room = loc.get("RoomNumber", "").strip()
    if room:
        parts.append(f"ap. {room}")

    city = normalize_title(loc.get("City", ""))
    postcode = loc.get("PostCode", "").strip()

    if postcode and city:
        parts.append(f"{postcode} {city}")
    elif city:
        parts.append(city)
    elif postcode:
        parts.append(postcode)

    region = loc.get("Region", "")
    if region:
        parts.append(normalize_title(get_judet(region)))

    return ", ".join(parts) if parts else "Adresă necunoscută"


# ── Mapping tip client ─────────────────────────
CLIENT_TYPE_FRIENDLY: dict[str, str] = {
    "PF": "Persoană fizică",
    "PJ": "Persoană juridică",
    "II": "Întreprindere individuală",
    "PFA": "Persoană fizică autorizată",
    "SRL": "Societate cu răspundere limitată",
    "SA": "Societate pe acțiuni",
    "SNC": "Societate în nume colectiv",
    "SCS": "Societate în comandită simplă",
    "ONG": "Organizație non-guvernamentală",
}

def client_type_friendly(code: str) -> str:
    """
    Returnează denumirea prietenoasă pentru codul tip client.
    Dacă codul nu există în mapping, returnează codul sau 'Necunoscut'.
    """
    if not code:
        return "Necunoscut"
    return CLIENT_TYPE_FRIENDLY.get(code.upper().strip(), code)
