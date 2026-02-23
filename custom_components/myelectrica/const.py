"""Constante pentru integrarea MyElectrica România."""

# ──────────────────────────────────────────────
# Domeniu & configurare implicită
# ──────────────────────────────────────────────
DOMAIN = "myelectrica"
DEFAULT_UPDATE = 3600  # secunde (1 oră)
ATTRIBUTION = "Date furnizate de MyElectrica România"

# ──────────────────────────────────────────────
# Headere HTTP
# ──────────────────────────────────────────────
HEADERS_POST = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
}

# ──────────────────────────────────────────────
# URL-uri API MyElectrica
# ──────────────────────────────────────────────
URL_LOGIN = "https://api.myelectrica.ro/api/login-web"
URL_CONTULMEU = "https://api.myelectrica.ro/api/contract-nlc-details/{cod_nlc}"
URL_INDEXCONTOR = "https://api.myelectrica.ro/api/meter-list/{cod_nlc}"
URL_CONVENTIE = "https://api.myelectrica.ro/api/consumtion-convention/{cod_nlc}"
URL_FACTURI = (
    "https://api.myelectrica.ro/api/contract-account-invoices"
    "/{cod_incasare}/{start_date}/{end_date}/false"
)

# ──────────────────────────────────────────────
# Mapare luni → română
# ──────────────────────────────────────────────

# Mapping luni EN -> RO
MONTHS_EN_RO: dict[str, str] = {
    "January": "ianuarie",
    "February": "februarie",
    "March": "martie",
    "April": "aprilie",
    "May": "mai",
    "June": "iunie",
    "July": "iulie",
    "August": "august",
    "September": "septembrie",
    "October": "octombrie",
    "November": "noiembrie",
    "December": "decembrie",
}

# Mapping luni numeric (string zero-padded) -> RO
MONTHS_NUM_RO: dict[str, str] = {
    "01": "ianuarie",
    "02": "februarie",
    "03": "martie",
    "04": "aprilie",
    "05": "mai",
    "06": "iunie",
    "07": "iulie",
    "08": "august",
    "09": "septembrie",
    "10": "octombrie",
    "11": "noiembrie",
    "12": "decembrie",
}
