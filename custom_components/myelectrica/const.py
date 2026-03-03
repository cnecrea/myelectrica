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
BASE_URL = "https://api.myelectrica.ro/api"

# 1.1 Autentificare
URL_LOGIN = f"{BASE_URL}/login"

# 3.1 Ierarhie date cont (coduri client → contracte → NLC-uri)
URL_HIERARCHY = f"{BASE_URL}/account-data-hierarchy"

# 3.2 Date client detaliate
URL_CLIENT_DATA = f"{BASE_URL}/client-data/{{client_code}}"

# 3.3 Detalii contract NLC
URL_CONTRACT_NLC = f"{BASE_URL}/contract-nlc-details/{{nlc}}"

# 4.1 Facturi per cod client
URL_INVOICES = (
    f"{BASE_URL}/client-code-invoices"
    "/{client_code}/{start_date}/{end_date}/{unpaid}"
)

# 5.1 Istoric plăți per cod client
URL_PAYMENTS = (
    f"{BASE_URL}/client-code-payments"
    "/{client_code}/{start_date}/{end_date}"
)

# 6.1 Lista contoare (meter list) per NLC
URL_METER_LIST = f"{BASE_URL}/meter-list/{{nlc}}"

# 7.1 Istoric citiri per cod client + NLC
URL_READINGS = f"{BASE_URL}/readings/{{client_code}}/{{nlc}}"

# 8.1 Convenție consum per NLC
URL_CONVENTION = f"{BASE_URL}/consumtion-convention/{{nlc}}"

# 6.2 Trimitere index (autocitire)
URL_SET_INDEX = f"{BASE_URL}/set-index"

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
