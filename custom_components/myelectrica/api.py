"""
API Manager pentru integrarea MyElectrica România.
"""

import logging
import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    URL_LOGIN,
    HEADERS_POST,
    URL_CONTULMEU,
    URL_INDEXCONTOR,
    URL_CONVENTIE,
    URL_FACTURI,
    START_DATE,
    END_DATE,
)

_LOGGER = logging.getLogger(__name__)

class MyElectricaAPI:
    """
    Manager API pentru integrarea MyElectrica.
    Se ocupă de autentificare și de obținerea datelor de la server.
    """

    def __init__(self, hass: HomeAssistant, username: str, password: str, cod_incasare: str, cod_nlc: str):
        self._hass = hass
        self._username = username
        self._password = password
        self._cod_incasare = cod_incasare
        self._cod_nlc = cod_nlc

        self._session = async_get_clientsession(self._hass)
        self._token = None

    async def async_login(self) -> bool:
        """
        Face login și memorează token-ul. Returnează True dacă autentificarea a reușit.
        """
        try:
            payload = {
                "email": self._username,
                "parola": self._password,
            }
            async with self._session.post(URL_LOGIN, headers=HEADERS_POST, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("error") is False:
                        self._token = data.get("app_token")
                        _LOGGER.debug("Autentificare reușită, token primit: %s", self._token)
                        return True
                    else:
                        _LOGGER.error("Eroare API login: %s", data)
                else:
                    _LOGGER.error("Eroare HTTP la login: Status=%s", resp.status)
        except aiohttp.ClientError as err:
            _LOGGER.error("Excepție în timpul autentificării: %s", err)

        # Dacă nu a reușit
        self._token = None
        return False

    async def async_request(self, url: str) -> dict | None:
        """
        Efectuează un request GET cu token.
        Dacă nu avem token, încercăm să ne logăm mai întâi.
        """
        # Dacă nu avem token, încercăm să ne autentificăm
        if not self._token:
            auth_ok = await self.async_login()
            if not auth_ok:
                _LOGGER.error("Eroare: Nu s-a putut obține token-ul de autentificare.")
                return None

        headers = {
            "accept": "application/json",
            "authorization": f"Bearer {self._token}",
            "user-agent": HEADERS_POST["User-Agent"],
        }

        try:
            async with self._session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    _LOGGER.debug("Răspuns OK de la %s: %s", url, data)
                    return data
                else:
                    _LOGGER.error("Eroare la request: Status=%s, URL=%s, Răspuns=%s",
                                  resp.status, url, await resp.text())
        except aiohttp.ClientError as err:
            _LOGGER.error("Eroare conexiune la URL=%s: %s", url, err)

        return None

    async def async_get_contul_meu(self) -> dict | None:
        """Obține date contul meu."""
        url = URL_CONTULMEU.format(cod_nlc=self._cod_nlc)
        return await self.async_request(url)

    async def async_get_index_curent(self) -> dict | None:
        """Obține date pentru indexul curent al contorului."""
        url = URL_INDEXCONTOR.format(cod_nlc=self._cod_nlc)
        return await self.async_request(url)

    async def async_get_conventie(self) -> dict | None:
        """Obține date despre convenția de consum."""
        url = URL_CONVENTIE.format(cod_nlc=self._cod_nlc)
        return await self.async_request(url)

    async def async_get_facturi(self) -> dict | None:
        """Obține date despre facturi (atât achitate, cât și neachitate)."""
        url = URL_FACTURI.format(
            cod_incasare=self._cod_incasare,
            start_date=START_DATE,
            end_date=END_DATE,
        )
        return await self.async_request(url)
