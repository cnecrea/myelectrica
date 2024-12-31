"""Constante pentru integrarea MyElectrica România."""

from datetime import datetime

# Domeniul integrării
DOMAIN = "myelectrica"

# Detalii de configurare
DEFAULT_USER = "username"
DEFAULT_PASS = "password"
COD_INCASARE = "COD_INCASARE"
COD_CLIENT = "COD_CLIENT"
COD_NLC = "COD_NLC"

DEFAULT_UPDATE = 3600  # Interval de actualizare în secunde (1 oră)

# Antet pentru cereri POST
HEADERS_POST = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
}

# Payload-ul pentru autentificare
PAYLOAD_LOGIN = {
    "username": DEFAULT_USER,
    "password": DEFAULT_PASS,
}

MONTHS_RO = {
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

# URL-uri pentru interacțiunea cu API-ul MyElectrica
URL_LOGIN = "https://api.myelectrica.ro/api/login-web" # OK
URL_CONTULMEU = "https://api.myelectrica.ro/api/contract-nlc-details/{cod_nlc}" # OK
URL_INDEXCONTOR ="https://api.myelectrica.ro/api/meter-list/{cod_nlc}"
URL_CONVENTIE = "https://api.myelectrica.ro/api/consumtion-convention/{cod_nlc}"
URL_FACTURI = "https://api.myelectrica.ro/api/contract-account-invoices/{cod_incasare}/{start_date}/{end_date}/false"


# Date implicite pentru perioada de facturare
START_DATE = "2023-01-01"
END_DATE = datetime.now().strftime('%Y-%m-%d')